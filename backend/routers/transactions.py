import math
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, status, Depends
from backend.database import get_db
from backend.models import TransactionListResponse, TransactionResponse, TransactionUpdate, TransactionCreate
from backend.services.categorizer import learn_merchant_mapping
from backend.services.recurring_detector import detect_recurring_patterns
from backend.services.insights_engine import generate_insights
from backend.routers.auth import get_current_user

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])

@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    min_amount: Optional[float] = Query(None),
    max_amount: Optional[float] = Query(None),
    is_recurring: Optional[int] = Query(None),
    is_transfer: Optional[int] = Query(None),
    is_refund: Optional[int] = Query(None),
    sort_by: str = Query("transaction_date"),
    sort_order: str = Query("desc"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """List transactions with rich filtering, search, sorting, and pagination for authenticated user."""
    user_id = current_user["id"]
    query_parts = ["user_id = ?"]
    params = [user_id]

    if search:
        query_parts.append("(description LIKE ? OR merchant LIKE ? OR category LIKE ?)")
        search_pattern = f"%{search}%"
        params.extend([search_pattern, search_pattern, search_pattern])

    if category:
        query_parts.append("category = ?")
        params.append(category)

    if transaction_type:
        query_parts.append("transaction_type = ?")
        params.append(transaction_type)

    if start_date:
        query_parts.append("transaction_date >= ?")
        params.append(start_date)

    if end_date:
        query_parts.append("transaction_date <= ?")
        params.append(end_date)

    if min_amount is not None:
        query_parts.append("ABS(amount) >= ?")
        params.append(min_amount)

    if max_amount is not None:
        query_parts.append("ABS(amount) <= ?")
        params.append(max_amount)

    if is_recurring is not None:
        query_parts.append("is_recurring = ?")
        params.append(is_recurring)

    if is_transfer is not None:
        query_parts.append("is_transfer = ?")
        params.append(is_transfer)

    if is_refund is not None:
        query_parts.append("is_refund = ?")
        params.append(is_refund)

    where_clause = " AND ".join(query_parts)

    allowed_sort_fields = {
        "transaction_date": "transaction_date",
        "amount": "ABS(amount)",
        "merchant": "merchant",
        "category": "category"
    }
    sort_col = allowed_sort_fields.get(sort_by, "transaction_date")
    direction = "ASC" if sort_order.lower() == "asc" else "DESC"

    with get_db() as conn:
        cursor = conn.cursor()

        # Count total
        cursor.execute(f"SELECT COUNT(*) FROM transactions WHERE {where_clause};", params)
        total_count = cursor.fetchone()[0]

        offset = (page - 1) * page_size
        cursor.execute(f"""
            SELECT * FROM transactions 
            WHERE {where_clause}
            ORDER BY {sort_col} {direction}, id DESC
            LIMIT ? OFFSET ?;
        """, params + [page_size, offset])
        rows = cursor.fetchall()

    items = [TransactionResponse(**dict(r)) for r in rows]
    total_pages = max(1, math.ceil(total_count / page_size))

    return TransactionListResponse(
        items=items,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieve details for a single transaction belonging to current user."""
    user_id = current_user["id"]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transactions WHERE id = ? AND user_id = ?;", (transaction_id, user_id))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Transaction not found.")
        return TransactionResponse(**dict(row))

@router.patch("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: int,
    req: TransactionUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update fields on a transaction and remember merchant categorization preferences."""
    user_id = current_user["id"]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transactions WHERE id = ? AND user_id = ?;", (transaction_id, user_id))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Transaction not found.")

        updates = []
        params = []

        if req.description is not None:
            updates.append("description = ?")
            params.append(req.description)
        if req.merchant is not None:
            updates.append("merchant = ?")
            params.append(req.merchant)
        if req.amount is not None:
            updates.append("amount = ?")
            params.append(req.amount)
        if req.transaction_type is not None:
            updates.append("transaction_type = ?")
            params.append(req.transaction_type)
        if req.category is not None:
            updates.append("category = ?")
            params.append(req.category)
            # Learn preference for future uploads
            merchant_to_learn = req.merchant or existing["merchant"] or existing["description"]
            learn_merchant_mapping(merchant_to_learn, req.category, user_id=user_id)
        if req.subcategory is not None:
            updates.append("subcategory = ?")
            params.append(req.subcategory)
        if req.is_transfer is not None:
            updates.append("is_transfer = ?")
            params.append(1 if req.is_transfer else 0)
        if req.is_refund is not None:
            updates.append("is_refund = ?")
            params.append(1 if req.is_refund else 0)
        if req.is_recurring is not None:
            updates.append("is_recurring = ?")
            params.append(1 if req.is_recurring else 0)
        if req.notes is not None:
            updates.append("notes = ?")
            params.append(req.notes)

        if updates:
            params.extend([transaction_id, user_id])
            cursor.execute(f"UPDATE transactions SET {', '.join(updates)} WHERE id = ? AND user_id = ?;", params)

        cursor.execute("SELECT * FROM transactions WHERE id = ? AND user_id = ?;", (transaction_id, user_id))
        updated = cursor.fetchone()

    # Recalculate recurring patterns & insights for this user
    try:
        detect_recurring_patterns(user_id=user_id)
        generate_insights(user_id=user_id)
    except Exception:
        pass

    return TransactionResponse(**dict(updated))

@router.delete("/{transaction_id}", status_code=status.HTTP_200_OK)
async def delete_transaction(
    transaction_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a single transaction."""
    user_id = current_user["id"]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM transactions WHERE id = ? AND user_id = ?;", (transaction_id, user_id))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Transaction not found.")
        cursor.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?;", (transaction_id, user_id))

    try:
        detect_recurring_patterns(user_id=user_id)
        generate_insights(user_id=user_id)
    except Exception:
        pass

    return {"message": f"Transaction #{transaction_id} deleted successfully."}
