import os
import datetime
from pathlib import Path
from typing import Dict, Any, List
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from backend.config import MAX_UPLOAD_SIZE_BYTES, UPLOAD_DIR
from backend.database import get_db
from backend.models import UploadPreviewResponse, UploadConfirmRequest, UploadResponse
from backend.services.transaction_parser import parse_and_preview_file, read_file_to_dataframe, clean_amount_str, parse_date_str
from backend.services.data_cleaner import clean_and_normalize_record, check_is_duplicate
from backend.services.recurring_detector import detect_recurring_patterns
from backend.services.insights_engine import generate_insights
from backend.routers.auth import get_current_user

router = APIRouter(prefix="/api/uploads", tags=["Uploads"])

@router.post("/preview", response_model=UploadPreviewResponse)
async def preview_upload(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Validate uploaded CSV or Excel statement and return column mapping and preview for authenticated user."""
    user_id = current_user["id"]
    filename = file.filename or "statement.csv"
    ext = Path(filename).suffix.lower()
    
    if ext not in [".csv", ".xlsx", ".xls"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Please upload a CSV or Excel (.xlsx, .xls) statement."
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size limit of {MAX_UPLOAD_SIZE_BYTES // (1024*1024)}MB."
        )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty."
        )

    try:
        preview_data = parse_and_preview_file(content, filename, user_id=user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unable to parse statement: {str(e)}"
        )

    # Cross-reference preview rows against SQLite database to flag duplicates for this user
    with get_db() as conn:
        for row in preview_data["preview_rows"]:
            if row["parsed_date"] and row["parsed_amount"]:
                is_dup = check_is_duplicate(
                    conn,
                    row["parsed_date"],
                    row["parsed_amount"],
                    row["raw_description"],
                    row["merchant"],
                    user_id=user_id
                )
                if is_dup and not row["is_duplicate"]:
                    row["is_duplicate"] = True
                    preview_data["duplicate_rows_count"] += 1

    return preview_data

@router.post("/import", response_model=UploadResponse)
async def confirm_import(
    req: UploadConfirmRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Commit validated transactions from temporary parsed statement into SQLite for authenticated user."""
    user_id = current_user["id"]
    temp_files = list(UPLOAD_DIR.glob(f"{req.temp_file_token}.*"))
    if not temp_files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload session expired or temporary file not found. Please re-upload the file."
        )

    temp_path = temp_files[0]
    filename = temp_path.name

    try:
        df = read_file_to_dataframe(temp_path, filename)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read temporary file: {str(e)}"
        )

    mapping = req.column_mapping
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    imported_count = 0
    duplicate_count = 0
    error_count = 0

    with get_db() as conn:
        cursor = conn.cursor()

        # Create record in uploads table
        cursor.execute("""
            INSERT INTO uploads (user_id, original_filename, file_type, uploaded_at, import_status)
            VALUES (?, ?, ?, ?, 'processing');
        """, (user_id, filename, temp_path.suffix.replace(".", "").upper(), now_iso))
        upload_id = cursor.lastrowid

        for _, row in df.iterrows():
            raw_date = str(row[mapping.date_col]) if mapping.date_col and row.get(mapping.date_col) is not None else ""
            raw_desc = str(row[mapping.desc_col]) if mapping.desc_col and row.get(mapping.desc_col) is not None else ""
            raw_merchant = str(row[mapping.merchant_col]) if mapping.merchant_col and row.get(mapping.merchant_col) is not None else ""

            parsed_date = parse_date_str(raw_date)
            parsed_amount = None
            txn_type = "expense"

            if mapping.debit_col and mapping.credit_col:
                debit_val = clean_amount_str(row.get(mapping.debit_col))
                credit_val = clean_amount_str(row.get(mapping.credit_col))
                if credit_val and credit_val > 0:
                    parsed_amount = abs(credit_val)
                    txn_type = "income"
                elif debit_val and debit_val > 0:
                    parsed_amount = -abs(debit_val)
                    txn_type = "expense"
            elif mapping.amount_col:
                amt = clean_amount_str(row.get(mapping.amount_col))
                if amt is not None:
                    if mapping.type_col and row.get(mapping.type_col):
                        t_str = str(row[mapping.type_col]).lower()
                        if "cr" in t_str or "in" in t_str or "deposit" in t_str:
                            parsed_amount = abs(amt)
                            txn_type = "income"
                        else:
                            parsed_amount = -abs(amt)
                            txn_type = "expense"
                    else:
                        parsed_amount = amt
                        txn_type = "income" if amt >= 0 else "expense"

            if not parsed_date or parsed_amount is None:
                error_count += 1
                continue

            cleaned = clean_and_normalize_record({
                "parsed_date": parsed_date,
                "raw_description": raw_desc or raw_merchant,
                "merchant": raw_merchant,
                "parsed_amount": parsed_amount,
                "transaction_type": txn_type,
                "category": str(row.get(mapping.category_col, "")) if mapping.category_col else ""
            }, default_currency=req.default_currency, user_id=user_id)

            # Check duplicate
            is_dup = check_is_duplicate(conn, cleaned["transaction_date"], cleaned["amount"], cleaned["description"], cleaned["merchant"], user_id=user_id)
            if is_dup:
                duplicate_count += 1
                if req.skip_duplicates:
                    continue

            cursor.execute("""
                INSERT INTO transactions (
                    user_id, upload_id, transaction_date, description, merchant, amount,
                    transaction_type, category, subcategory, currency, payment_method,
                    is_recurring, is_transfer, is_refund, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                user_id,
                upload_id,
                cleaned["transaction_date"],
                cleaned["description"],
                cleaned["merchant"],
                cleaned["amount"],
                cleaned["transaction_type"],
                cleaned["category"],
                cleaned["subcategory"],
                cleaned["currency"],
                cleaned["payment_method"],
                cleaned["is_recurring"],
                cleaned["is_transfer"],
                cleaned["is_refund"],
                cleaned["notes"],
                now_iso
            ))
            imported_count += 1

        # Update uploads metadata
        cursor.execute("""
            UPDATE uploads SET
                transaction_count = ?,
                duplicate_count = ?,
                error_count = ?,
                import_status = 'completed'
            WHERE id = ? AND user_id = ?;
        """, (imported_count, duplicate_count, error_count, upload_id, user_id))

    # Safely remove temp file
    try:
        temp_path.unlink(missing_ok=True)
    except Exception:
        pass

    # Refresh recurring detector and insights asynchronously for this user
    try:
        detect_recurring_patterns(user_id=user_id)
        generate_insights(user_id=user_id)
    except Exception:
        pass

    return {
        "id": upload_id,
        "original_filename": filename,
        "file_type": temp_path.suffix.replace(".", "").upper(),
        "uploaded_at": now_iso,
        "transaction_count": imported_count,
        "duplicate_count": duplicate_count,
        "error_count": error_count,
        "import_status": "completed"
    }

@router.get("", response_model=List[UploadResponse])
async def list_uploads(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieve history of statement imports for the authenticated user."""
    user_id = current_user["id"]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM uploads WHERE user_id = ? ORDER BY id DESC;", (user_id,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

@router.delete("/{upload_id}", status_code=status.HTTP_200_OK)
async def delete_upload(
    upload_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete an upload and all its imported transactions cleanly for the authenticated user."""
    user_id = current_user["id"]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM uploads WHERE id = ? AND user_id = ?;", (upload_id, user_id))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Upload record not found.")

        cursor.execute("DELETE FROM transactions WHERE upload_id = ? AND user_id = ?;", (upload_id, user_id))
        cursor.execute("DELETE FROM uploads WHERE id = ? AND user_id = ?;", (upload_id, user_id))

    # Refresh recurring and insights
    try:
        detect_recurring_patterns(user_id=user_id)
        generate_insights(user_id=user_id)
    except Exception:
        pass

    return {"message": f"Upload batch #{upload_id} and associated transactions removed successfully."}
