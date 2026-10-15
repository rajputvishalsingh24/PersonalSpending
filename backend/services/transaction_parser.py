import os
import uuid
import re
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from backend.config import UPLOAD_DIR
from backend.services.categorizer import extract_merchant, categorize_transaction, is_transfer_description, is_refund_description

COLUMN_PATTERNS = {
    "date_col": [r"date", r"txn[\s_]?date", r"trans[\s_]?date", r"posting[\s_]?date", r"value[\s_]?date", r"time"],
    "desc_col": [r"desc", r"description", r"narration", r"particulars", r"details", r"remark", r"memo", r"transaction"],
    "merchant_col": [r"merchant", r"payee", r"vendor", r"party", r"receiver"],
    "amount_col": [r"^amount$", r"txn[\s_]?amount", r"total", r"^amt$"],
    "debit_col": [r"^debit$", r"withdrawal", r"^dr$", r"paid[\s_]?out", r"expense", r"debit[\s_]?amount"],
    "credit_col": [r"^credit$", r"deposit", r"^cr$", r"paid[\s_]?in", r"income", r"credit[\s_]?amount"],
    "category_col": [r"category", r"tag", r"classification"],
    "type_col": [r"^type$", r"txn[\s_]?type", r"transaction[\s_]?type", r"cr[\s_]?\/[\s_]?dr"]
}

def clean_amount_str(val: Any) -> Optional[float]:
    """Parse monetary amount string safely with currency symbols and parenthesis."""
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    
    val_str = str(val).strip()
    if not val_str:
        return None
        
    # Check for parenthesis notation for negative: (100.00)
    is_paren_negative = False
    if val_str.startswith("(") and val_str.endswith(")"):
        is_paren_negative = True
        val_str = val_str[1:-1]
        
    # Remove currency symbols, commas, spaces
    cleaned = re.sub(r"[₹\$\€\£\s\,]", "", val_str)
    try:
        num = float(cleaned)
        return -abs(num) if is_paren_negative else num
    except ValueError:
        return None

def parse_date_str(val: Any) -> Optional[str]:
    """Parse date string into ISO format YYYY-MM-DD."""
    if val is None or pd.isna(val):
        return None
    val_str = str(val).strip()
    if not val_str:
        return None
    try:
        if re.match(r"^\d{4}[-/]", val_str):
            dt = pd.to_datetime(val_str, yearfirst=True, dayfirst=False)
            return dt.strftime("%Y-%m-%d")
        dt = pd.to_datetime(val_str, dayfirst=True)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        try:
            dt = pd.to_datetime(val_str)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return None

def detect_columns(df_columns: List[str]) -> Dict[str, Optional[str]]:
    """Automatically detect column mappings based on regex patterns."""
    mapping: Dict[str, Optional[str]] = {
        "date_col": None,
        "desc_col": None,
        "merchant_col": None,
        "amount_col": None,
        "debit_col": None,
        "credit_col": None,
        "category_col": None,
        "type_col": None
    }
    
    for col in df_columns:
        norm = col.lower().strip()
        for field, patterns in COLUMN_PATTERNS.items():
            if mapping[field] is None:
                for pat in patterns:
                    if re.search(pat, norm):
                        mapping[field] = col
                        break
    return mapping

def read_file_to_dataframe(filepath: Path, filename: str) -> pd.DataFrame:
    """Read CSV or Excel into a pandas DataFrame."""
    lower_name = filename.lower()
    if lower_name.endswith((".xlsx", ".xls")):
        return pd.read_excel(filepath)
    else:
        # Try comma delimiter, then semicolon, then tab
        for sep in [",", ";", "\t"]:
            try:
                df = pd.read_csv(filepath, sep=sep)
                if len(df.columns) > 1:
                    return df
            except Exception:
                continue
        return pd.read_csv(filepath)

from backend.database import get_db
from backend.services.data_cleaner import check_is_duplicate

def parse_and_preview_file(file_bytes: bytes, original_filename: str, user_id: int = 1) -> Dict[str, Any]:
    """Save upload temporarily, detect columns, validate records, and return preview."""
    token = str(uuid.uuid4())
    ext = Path(original_filename).suffix
    temp_path = UPLOAD_DIR / f"{token}{ext}"
    
    with open(temp_path, "wb") as f:
        f.write(file_bytes)
        
    df = read_file_to_dataframe(temp_path, original_filename)
    columns = [str(c) for c in df.columns]
    mapping = detect_columns(columns)
    
    preview_rows = []
    valid_count = 0
    duplicate_count = 0
    error_count = 0
    
    with get_db() as conn:
        for idx, row in df.iterrows():
            raw_date = str(row[mapping["date_col"]]) if mapping["date_col"] and pd.notna(row[mapping["date_col"]]) else ""
            raw_desc = str(row[mapping["desc_col"]]) if mapping["desc_col"] and pd.notna(row[mapping["desc_col"]]) else ""
            raw_merchant = str(row[mapping["merchant_col"]]) if mapping["merchant_col"] and pd.notna(row[mapping["merchant_col"]]) else ""
            
            parsed_date = parse_date_str(raw_date) if raw_date else None
            
            # Calculate amount & type based on available columns
            parsed_amount = None
            txn_type = "expense"
            validation_error = None
            
            # Scenario 1: Separate Debit and Credit columns
            if mapping["debit_col"] and mapping["credit_col"]:
                debit_val = clean_amount_str(row[mapping["debit_col"]])
                credit_val = clean_amount_str(row[mapping["credit_col"]])
                
                if credit_val and credit_val > 0:
                    parsed_amount = abs(credit_val)
                    txn_type = "income"
                elif debit_val and debit_val > 0:
                    parsed_amount = -abs(debit_val)
                    txn_type = "expense"
                elif debit_val and debit_val < 0:
                    parsed_amount = debit_val
                    txn_type = "expense"
            # Scenario 2: Single Amount column with optional Type column
            elif mapping["amount_col"]:
                raw_amt = clean_amount_str(row[mapping["amount_col"]])
                if raw_amt is not None:
                    if mapping["type_col"] and pd.notna(row[mapping["type_col"]]):
                        type_str = str(row[mapping["type_col"]]).lower().strip()
                        if "cr" in type_str or "in" in type_str or "deposit" in type_str:
                            parsed_amount = abs(raw_amt)
                            txn_type = "income"
                        else:
                            parsed_amount = -abs(raw_amt)
                            txn_type = "expense"
                    else:
                        if raw_amt >= 0:
                            parsed_amount = raw_amt
                            txn_type = "income"
                        else:
                            parsed_amount = raw_amt
                            txn_type = "expense"
                            
            if not parsed_date:
                validation_error = "Invalid or missing transaction date"
            elif parsed_amount is None or parsed_amount == 0:
                validation_error = "Invalid or zero transaction amount"
            elif not raw_desc and not raw_merchant:
                validation_error = "Missing description or merchant name"
                
            merchant = raw_merchant if raw_merchant else extract_merchant(raw_desc)
            category, _, conf = categorize_transaction(raw_desc, merchant, parsed_amount or 0.0, user_id=user_id)
            
            is_dup = False
            if parsed_date and parsed_amount is not None:
                is_dup = check_is_duplicate(conn, parsed_date, parsed_amount, raw_desc or merchant, merchant, user_id=user_id)

            if validation_error:
                error_count += 1
            elif is_dup:
                duplicate_count += 1
                valid_count += 1
            else:
                valid_count += 1
                
            preview_rows.append({
                "row_index": int(idx),
                "raw_date": raw_date,
                "parsed_date": parsed_date,
                "raw_description": raw_desc or merchant,
                "merchant": merchant,
                "raw_amount": str(row.get(mapping["amount_col"] or mapping["debit_col"] or "", "")),
                "parsed_amount": parsed_amount,
                "transaction_type": txn_type,
                "category": category,
                "confidence": conf,
                "is_duplicate": is_dup,
                "validation_error": validation_error
            })
        
    return {
        "filename": original_filename,
        "file_type": ext.replace(".", "").upper(),
        "total_rows": len(df),
        "valid_rows_count": valid_count,
        "duplicate_rows_count": duplicate_count,
        "error_rows_count": error_count,
        "columns_found": columns,
        "column_mapping": mapping,
        "preview_rows": preview_rows,
        "temp_file_token": token
    }
