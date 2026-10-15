import sqlite3
from typing import Dict, Any, List, Tuple
from backend.database import get_db
from backend.services.categorizer import is_transfer_description, is_refund_description, extract_merchant, categorize_transaction

def check_is_duplicate(conn: sqlite3.Connection, date: str, amount: float, description: str, merchant: str, user_id: int = 1) -> bool:
    """Check if transaction already exists in SQLite for this user with same date, amount, and similar description/merchant."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM transactions 
        WHERE transaction_date = ? 
          AND ABS(amount - ?) < 0.01 
          AND (description = ? OR merchant = ?)
          AND user_id = ?;
    """, (date, amount, description, merchant, user_id))
    return cursor.fetchone()[0] > 0

def clean_and_normalize_record(row_data: Dict[str, Any], default_currency: str = "INR", user_id: int = 1) -> Dict[str, Any]:
    """Clean, categorize, and normalize transaction data for persistent storage for a specific user."""
    date = row_data["parsed_date"]
    desc = (row_data.get("raw_description") or "").strip()
    merchant = (row_data.get("merchant") or extract_merchant(desc)).strip()
    amount = float(row_data["parsed_amount"])
    txn_type = row_data.get("transaction_type") or ("income" if amount > 0 else "expense")
    
    # Check category
    category = row_data.get("category")
    subcategory = row_data.get("subcategory", "")
    if not category:
        category, subcategory, _ = categorize_transaction(desc, merchant, amount, user_id=user_id)
        
    is_transfer = 1 if is_transfer_description(desc) or is_transfer_description(merchant) else 0
    is_refund = 1 if is_refund_description(desc) or is_refund_description(merchant) or category == "Refunds" else 0
    
    return {
        "user_id": user_id,
        "transaction_date": date,
        "description": desc,
        "merchant": merchant,
        "amount": amount,
        "transaction_type": txn_type,
        "category": category,
        "subcategory": subcategory,
        "currency": default_currency,
        "payment_method": row_data.get("payment_method", ""),
        "is_recurring": 0,
        "is_transfer": is_transfer,
        "is_refund": is_refund,
        "notes": row_data.get("notes", "")
    }
