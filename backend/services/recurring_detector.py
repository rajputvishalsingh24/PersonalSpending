import sqlite3
import datetime
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from backend.database import get_db

SUBSCRIPTION_KEYWORDS = ["netflix", "spotify", "prime", "hotstar", "youtube", "apple", "icloud", "google", "broadband", "gym", "chatgpt"]

def detect_recurring_patterns(user_id: int = 1) -> List[Dict[str, Any]]:
    """
    Analyze all transactions for a user in SQLite to identify recurring payments and subscriptions.
    Updates the recurring_transactions table and flags transactions with is_recurring=1.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Fetch non-transfer expense transactions ordered by merchant and date
        cursor.execute("""
            SELECT id, merchant, description, category, amount, transaction_date 
            FROM transactions 
            WHERE is_transfer = 0 AND transaction_type = 'expense' AND user_id = ?
            ORDER BY merchant, transaction_date ASC;
        """, (user_id,))
        rows = cursor.fetchall()
        
        if not rows:
            return []
            
        # Group by merchant
        merchant_groups: Dict[str, List[Any]] = {}
        for r in rows:
            m = r["merchant"].strip()
            if not m:
                continue
            if m not in merchant_groups:
                merchant_groups[m] = []
            merchant_groups[m].append(r)
            
        detected_patterns = []
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        for merchant, txns in merchant_groups.items():
            if len(txns) < 2:
                continue
                
            dates = [datetime.datetime.strptime(t["transaction_date"], "%Y-%m-%d") for t in txns]
            amounts = [abs(t["amount"]) for t in txns]
            
            # Compute intervals between consecutive dates
            intervals = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
            if not intervals:
                continue
                
            avg_interval = float(np.mean(intervals))
            median_interval = float(np.median(intervals))
            avg_amount = float(np.mean(amounts))
            std_amount = float(np.std(amounts)) if len(amounts) > 1 else 0.0
            
            # Determine frequency and confidence
            frequency = None
            confidence = 0.0
            
            if 5 <= median_interval <= 9:
                frequency = "weekly"
                confidence = 0.85 if std_amount / (avg_amount + 1e-5) < 0.25 else 0.70
            elif 25 <= median_interval <= 35:
                frequency = "monthly"
                confidence = 0.90 if std_amount / (avg_amount + 1e-5) < 0.20 else 0.75
            elif 80 <= median_interval <= 100:
                frequency = "quarterly"
                confidence = 0.80 if std_amount / (avg_amount + 1e-5) < 0.25 else 0.65
            elif 340 <= median_interval <= 390:
                frequency = "annual"
                confidence = 0.85 if std_amount / (avg_amount + 1e-5) < 0.20 else 0.70
                
            if frequency:
                last_date = dates[-1]
                if frequency == "weekly":
                    next_expected = last_date + datetime.timedelta(days=7)
                elif frequency == "monthly":
                    next_expected = last_date + datetime.timedelta(days=30)
                elif frequency == "quarterly":
                    next_expected = last_date + datetime.timedelta(days=90)
                elif frequency == "annual":
                    next_expected = last_date + datetime.timedelta(days=365)
                else:
                    next_expected = last_date + datetime.timedelta(days=int(median_interval))
                    
                is_sub = 1 if any(kw in merchant.lower() or kw in txns[0]["category"].lower() for kw in SUBSCRIPTION_KEYWORDS) else 0
                category = txns[-1]["category"]
                
                # Insert or update in recurring_transactions
                cursor.execute("""
                    SELECT id, status, is_subscription, is_essential, review_notes 
                    FROM recurring_transactions 
                    WHERE merchant = ? AND user_id = ?;
                """, (merchant, user_id))
                existing = cursor.fetchone()
                
                if existing:
                    cursor.execute("""
                        UPDATE recurring_transactions SET
                            average_amount = ?,
                            frequency = ?,
                            last_detected_date = ?,
                            next_expected_date = ?,
                            confidence_score = ?,
                            category = ?
                        WHERE id = ? AND user_id = ?;
                    """, (
                        round(avg_amount, 2),
                        frequency,
                        last_date.strftime("%Y-%m-%d"),
                        next_expected.strftime("%Y-%m-%d"),
                        round(confidence, 2),
                        category,
                        existing["id"],
                        user_id
                    ))
                    rec_id = existing["id"]
                    rec_status = existing["status"]
                    is_sub = existing["is_subscription"]
                    is_ess = existing["is_essential"]
                    notes = existing["review_notes"]
                else:
                    cursor.execute("""
                        INSERT INTO recurring_transactions (
                            user_id, merchant, normalized_description, category, average_amount,
                            frequency, last_detected_date, next_expected_date, confidence_score,
                            status, is_subscription, is_essential, review_notes, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'detected', ?, 0, '', ?);
                    """, (
                        user_id,
                        merchant,
                        txns[-1]["description"],
                        category,
                        round(avg_amount, 2),
                        frequency,
                        last_date.strftime("%Y-%m-%d"),
                        next_expected.strftime("%Y-%m-%d"),
                        round(confidence, 2),
                        is_sub,
                        now_str
                    ))
                    rec_id = cursor.lastrowid
                    rec_status = "detected"
                    is_ess = 0
                    notes = ""
                    
                # Mark matching transactions with is_recurring = 1
                txn_ids = [t["id"] for t in txns]
                cursor.execute(f"UPDATE transactions SET is_recurring = 1 WHERE user_id = ? AND id IN ({','.join(['?']*len(txn_ids))});", [user_id] + txn_ids)
                
                multiplier = {"weekly": 52, "monthly": 12, "quarterly": 4, "annual": 1}.get(frequency, 12)
                annual_cost = round(avg_amount * multiplier, 2)
                
                detected_patterns.append({
                    "id": rec_id,
                    "merchant": merchant,
                    "normalized_description": txns[-1]["description"],
                    "category": category,
                    "average_amount": round(avg_amount, 2),
                    "frequency": frequency,
                    "last_detected_date": last_date.strftime("%Y-%m-%d"),
                    "next_expected_date": next_expected.strftime("%Y-%m-%d"),
                    "confidence_score": round(confidence, 2),
                    "status": rec_status,
                    "is_subscription": is_sub,
                    "is_essential": is_ess,
                    "review_notes": notes,
                    "annual_estimate": annual_cost,
                    "occurrences_count": len(txns),
                    "created_at": now_str
                })
                
        return detected_patterns

def get_active_recurring_expenses(user_id: int = 1) -> Tuple[float, int]:
    """Calculate total monthly estimated recurring expense and pattern count."""
    patterns = detect_recurring_patterns(user_id=user_id)
    total_monthly = 0.0
    count = 0
    for p in patterns:
        if p["status"] != "dismissed":
            count += 1
            freq = p["frequency"]
            avg = p["average_amount"]
            if freq == "weekly":
                total_monthly += avg * 4.33
            elif freq == "monthly":
                total_monthly += avg
            elif freq == "quarterly":
                total_monthly += avg / 3.0
            elif freq == "annual":
                total_monthly += avg / 12.0
            else:
                total_monthly += avg
    return round(total_monthly, 2), count
