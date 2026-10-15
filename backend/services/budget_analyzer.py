import sqlite3
import datetime
import calendar
from typing import List, Dict, Any, Optional
from backend.database import get_db

def analyze_budgets(target_month: Optional[str] = None, user_id: int = 1) -> List[Dict[str, Any]]:
    """
    Calculate actual spending, budget utilization, remaining budget, days pacing, and drift alerts
    for all configured budgets for a user in SQLite.
    """
    if target_month:
        try:
            year, month = map(int, target_month.split("-"))
        except ValueError:
            dt = datetime.datetime.now()
            year, month = dt.year, dt.month
    else:
        # Default to latest month with transactions for this user or current month
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(transaction_date) FROM transactions WHERE is_transfer = 0 AND user_id = ?;", (user_id,))
            latest = cursor.fetchone()[0]
        if latest:
            ref_dt = datetime.datetime.strptime(latest, "%Y-%m-%d")
            year, month = ref_dt.year, ref_dt.month
        else:
            dt = datetime.datetime.now()
            year, month = dt.year, dt.month

    _, last_day = calendar.monthrange(year, month)
    start_date = f"{year:04d}-{month:02d}-01"
    end_date = f"{year:04d}-{month:02d}-{last_day:02d}"

    # Days elapsed in period
    today = datetime.date.today()
    period_start = datetime.date(year, month, 1)
    period_end = datetime.date(year, month, last_day)

    if today > period_end:
        days_elapsed = last_day
        days_remaining = 0
    elif today < period_start:
        days_elapsed = 1
        days_remaining = last_day
    else:
        days_elapsed = today.day
        days_remaining = max(0, last_day - today.day)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, category, budget_amount, period_type, created_at FROM budgets WHERE user_id = ? ORDER BY category ASC;", (user_id,))
        budget_rows = cursor.fetchall()

        if not budget_rows:
            return []

        results = []
        for b in budget_rows:
            cat = b["category"]
            budget_amt = float(b["budget_amount"])

            if cat == "__overall__":
                cursor.execute("""
                    SELECT COALESCE(SUM(CASE 
                        WHEN is_refund = 1 OR category = 'Refunds' THEN -ABS(amount)
                        WHEN transaction_type = 'expense' THEN ABS(amount)
                        ELSE 0 
                    END), 0) FROM transactions
                    WHERE is_transfer = 0 AND user_id = ?
                      AND (transaction_type = 'expense' OR is_refund = 1 OR category = 'Refunds')
                      AND transaction_date >= ? AND transaction_date <= ?;
                """, (user_id, start_date, end_date))
            else:
                cursor.execute("""
                    SELECT COALESCE(SUM(CASE 
                        WHEN is_refund = 1 OR category = 'Refunds' THEN -ABS(amount)
                        WHEN transaction_type = 'expense' THEN ABS(amount)
                        ELSE 0 
                    END), 0) FROM transactions
                    WHERE is_transfer = 0 AND user_id = ?
                      AND category = ?
                      AND (transaction_type = 'expense' OR is_refund = 1 OR category = 'Refunds')
                      AND transaction_date >= ? AND transaction_date <= ?;
                """, (user_id, cat, start_date, end_date))

            actual_spend = max(0.0, round(float(cursor.fetchone()[0]), 2))
            remaining = round(budget_amt - actual_spend, 2)
            utilization_pct = round((actual_spend / budget_amt) * 100.0, 1) if budget_amt > 0 else 0.0

            # Status determination
            if actual_spend == 0:
                status = "On Track"
            elif utilization_pct > 100.0:
                status = "Over Budget"
            elif utilization_pct >= 80.0:
                status = "Approaching Limit"
            else:
                status = "On Track"

            # Projection and drift analysis
            projected = None
            drift_alert = None
            if days_elapsed > 0:
                daily_pace = actual_spend / days_elapsed
                projected = round(daily_pace * last_day, 2)

                time_progress_pct = (days_elapsed / last_day) * 100.0
                if utilization_pct > time_progress_pct + 20 and days_remaining > 5:
                    drift_alert = f"Spending pacing faster than calendar time ({utilization_pct}% spent in {time_progress_pct:.0f}% of month)."
                elif projected > budget_amt and status != "Over Budget":
                    drift_alert = f"At current rate, projected to finish at ₹{projected:,.0f} (over budget by ₹{projected - budget_amt:,.0f})."

            results.append({
                "id": b["id"],
                "category": cat,
                "budget_amount": budget_amt,
                "actual_spending": actual_spend,
                "remaining_budget": remaining,
                "utilization_pct": utilization_pct,
                "status": status,
                "days_elapsed": days_elapsed,
                "days_remaining": days_remaining,
                "projected_spend": projected,
                "drift_alert": drift_alert,
                "period_type": b["period_type"],
                "created_at": b["created_at"]
            })

        return results
