import sqlite3
import datetime
import calendar
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from backend.database import get_db
from backend.services.recurring_detector import get_active_recurring_expenses

ESSENTIAL_CATEGORIES = {
    "Housing and Rent", "Rent", "Groceries", "Utilities", "Electricity and Utilities",
    "Mobile and Internet", "Healthcare", "Healthcare and Medicines", "Fuel", "Transport and Fuel",
    "Transport", "Public Transport", "Insurance", "Loan Payments", "Loan and EMI Payments",
    "Education"
}

def resolve_date_range(start_date: Optional[str] = None, end_date: Optional[str] = None, user_id: int = 1) -> Tuple[str, str, str, str]:
    """
    Resolve current period (start_date, end_date) and comparable previous period (prev_start, prev_end).
    If no dates provided, defaults to the latest month with transaction data, or current calendar month.
    """
    if start_date and end_date:
        s_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        e_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        duration = (e_dt - s_dt).days + 1
        prev_e_dt = s_dt - datetime.timedelta(days=1)
        prev_s_dt = prev_e_dt - datetime.timedelta(days=duration - 1)
        return (
            start_date,
            end_date,
            prev_s_dt.strftime("%Y-%m-%d"),
            prev_e_dt.strftime("%Y-%m-%d")
        )

    # If not provided, find the latest transaction date for user in DB or default to today
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(transaction_date) FROM transactions WHERE is_transfer = 0 AND user_id = ?;", (user_id,))
        latest = cursor.fetchone()[0]

    if latest:
        ref_dt = datetime.datetime.strptime(latest, "%Y-%m-%d")
    else:
        ref_dt = datetime.datetime.now()

    # Full month of the reference date
    year = ref_dt.year
    month = ref_dt.month
    _, last_day = calendar.monthrange(year, month)
    
    current_start = f"{year:04d}-{month:02d}-01"
    current_end = f"{year:04d}-{month:02d}-{last_day:02d}"

    # Previous month
    if month == 1:
        prev_year = year - 1
        prev_month = 12
    else:
        prev_year = year
        prev_month = month - 1
    _, prev_last_day = calendar.monthrange(prev_year, prev_month)
    prev_start = f"{prev_year:04d}-{prev_month:02d}-01"
    prev_end = f"{prev_year:04d}-{prev_month:02d}-{prev_last_day:02d}"

    return current_start, current_end, prev_start, prev_end

def get_summary_metrics(start_date: Optional[str] = None, end_date: Optional[str] = None, user_id: int = 1) -> Dict[str, Any]:
    """Calculate key financial performance indicators for the specified period."""
    cur_start, cur_end, prev_start, prev_end = resolve_date_range(start_date, end_date, user_id=user_id)

    with get_db() as conn:
        cursor = conn.cursor()

        # Currency
        currency = "INR"
        try:
            cursor.execute("SELECT default_currency FROM users WHERE id = ?;", (user_id,))
            user_row = cursor.fetchone()
            if user_row and user_row["default_currency"]:
                currency = user_row["default_currency"]
            else:
                cursor.execute("SELECT value FROM user_settings WHERE key = 'default_currency' AND user_id = ?;", (user_id,))
                curr_row = cursor.fetchone()
                if curr_row:
                    currency = curr_row[0]
        except Exception:
            currency = "INR"

        # Current period totals - refunds offset expenses rather than inflating spending
        cursor.execute("""
            SELECT 
                COALESCE(SUM(CASE 
                    WHEN transaction_type = 'income' AND is_refund = 0 AND category != 'Refunds' THEN ABS(amount) 
                    ELSE 0 
                END), 0) as income,
                COALESCE(SUM(CASE 
                    WHEN is_refund = 1 OR category = 'Refunds' THEN -ABS(amount)
                    WHEN transaction_type = 'expense' THEN ABS(amount) 
                    ELSE 0 
                END), 0) as expense,
                COUNT(*) as count
            FROM transactions
            WHERE is_transfer = 0 AND user_id = ?
              AND transaction_date >= ? AND transaction_date <= ?;
        """, (user_id, cur_start, cur_end))
        cur_row = cursor.fetchone()
        income = round(float(cur_row["income"]), 2)
        expense = max(0.0, round(float(cur_row["expense"]), 2))
        count = int(cur_row["count"])

        # Previous period expense for MoM change
        cursor.execute("""
            SELECT COALESCE(SUM(CASE 
                WHEN is_refund = 1 OR category = 'Refunds' THEN -ABS(amount)
                WHEN transaction_type = 'expense' THEN ABS(amount) 
                ELSE 0 
            END), 0) as prev_expense
            FROM transactions
            WHERE is_transfer = 0 AND user_id = ?
              AND (transaction_type = 'expense' OR is_refund = 1 OR category = 'Refunds')
              AND transaction_date >= ? AND transaction_date <= ?;
        """, (user_id, prev_start, prev_end))
        prev_expense = max(0.0, round(float(cursor.fetchone()["prev_expense"]), 2))

    net_cash_flow = round(income - expense, 2)

    # Savings rate = (Income - Expense) / Income * 100
    if income > 0:
        savings_rate = round(((income - expense) / income) * 100.0, 1)
        savings_rate_label = f"{savings_rate}%"
    else:
        savings_rate = None
        savings_rate_label = "Not available"

    # MoM spending change
    if prev_expense > 0:
        mom_change = round(((expense - prev_expense) / prev_expense) * 100.0, 1)
        prefix = "+" if mom_change > 0 else ""
        mom_change_label = f"{prefix}{mom_change}% vs previous period"
    elif expense > 0:
        mom_change = None
        mom_change_label = "New spending period"
    else:
        mom_change = 0.0
        mom_change_label = "0% change"

    active_rec_spend, active_rec_count = get_active_recurring_expenses(user_id=user_id)

    period_label = f"{cur_start} to {cur_end}"

    return {
        "reporting_period": period_label,
        "total_income": income,
        "total_expenses": expense,
        "net_cash_flow": net_cash_flow,
        "savings_rate": savings_rate,
        "savings_rate_label": savings_rate_label,
        "mom_spending_change_pct": mom_change,
        "mom_spending_change_label": mom_change_label,
        "active_recurring_expenses": active_rec_spend,
        "active_recurring_count": active_rec_count,
        "currency": currency,
        "transaction_count": count
    }

def get_category_analytics(start_date: Optional[str] = None, end_date: Optional[str] = None, user_id: int = 1) -> List[Dict[str, Any]]:
    """Calculate detailed category breakdowns, comparisons, and statistics with refund offsets."""
    cur_start, cur_end, prev_start, prev_end = resolve_date_range(start_date, end_date, user_id=user_id)

    with get_db() as conn:
        cursor = conn.cursor()

        # Total qualifying expense (refunds reduce total expense)
        cursor.execute("""
            SELECT COALESCE(SUM(CASE 
                WHEN is_refund = 1 OR category = 'Refunds' THEN -ABS(amount)
                WHEN transaction_type = 'expense' THEN ABS(amount)
                ELSE 0 
            END), 0) FROM transactions
            WHERE is_transfer = 0 AND user_id = ?
              AND (transaction_type = 'expense' OR is_refund = 1 OR category = 'Refunds')
              AND transaction_date >= ? AND transaction_date <= ?;
        """, (user_id, cur_start, cur_end))
        total_exp = max(1.0, float(cursor.fetchone()[0]))

        # Current period by category
        cursor.execute("""
            SELECT category, amount, transaction_type, is_refund, transaction_date 
            FROM transactions
            WHERE is_transfer = 0 AND user_id = ?
              AND (transaction_type = 'expense' OR is_refund = 1 OR category = 'Refunds')
              AND transaction_date >= ? AND transaction_date <= ?;
        """, (user_id, cur_start, cur_end))
        rows = cursor.fetchall()

        # Previous period totals by category
        cursor.execute("""
            SELECT category, COALESCE(SUM(CASE 
                WHEN is_refund = 1 OR category = 'Refunds' THEN -ABS(amount)
                WHEN transaction_type = 'expense' THEN ABS(amount)
                ELSE 0 
            END), 0) as prev_total
            FROM transactions
            WHERE is_transfer = 0 AND user_id = ?
              AND (transaction_type = 'expense' OR is_refund = 1 OR category = 'Refunds')
              AND transaction_date >= ? AND transaction_date <= ?
            GROUP BY category;
        """, (user_id, prev_start, prev_end))
        prev_totals = {r["category"]: max(0.0, float(r["prev_total"])) for r in cursor.fetchall()}

    cat_groups: Dict[str, List[float]] = {}
    for r in rows:
        cat = r["category"]
        if cat == "Refunds":
            continue
        if cat not in cat_groups:
            cat_groups[cat] = []
        is_ref = (r["is_refund"] == 1)
        val = -abs(float(r["amount"])) if is_ref else abs(float(r["amount"]))
        cat_groups[cat].append(val)

    days_in_period = max(1, (datetime.datetime.strptime(cur_end, "%Y-%m-%d") - datetime.datetime.strptime(cur_start, "%Y-%m-%d")).days + 1)

    total_cat_spend = sum(max(0.0, sum(amounts)) for cat, amounts in cat_groups.items() if cat != "Refunds")
    safe_denom = total_cat_spend if total_cat_spend > 0 else total_exp

    result = []
    for cat, amounts in cat_groups.items():
        cat_total = max(0.0, sum(amounts))
        prev_total = prev_totals.get(cat, 0.0)
        abs_change = round(cat_total - prev_total, 2)
        pct_change = round(((cat_total - prev_total) / prev_total) * 100.0, 1) if prev_total > 0 else None
        positive_amts = [abs(a) for a in amounts if a > 0] or [cat_total]

        result.append({
            "category": cat,
            "total_spend": round(cat_total, 2),
            "transaction_count": len(amounts),
            "percentage": round((cat_total / safe_denom) * 100.0, 1),
            "previous_period_spend": round(prev_total, 2),
            "absolute_change": abs_change,
            "percentage_change": pct_change,
            "average_amount": round(float(np.mean(positive_amts)), 2),
            "median_amount": round(float(np.median(positive_amts)), 2),
            "largest_transaction": round(float(max(positive_amts)), 2),
            "daily_average": round(cat_total / days_in_period, 2)
        })

    result.sort(key=lambda x: x["total_spend"], reverse=True)
    return result

def get_spending_trends(interval: str = "monthly", start_date: Optional[str] = None, end_date: Optional[str] = None, user_id: int = 1) -> List[Dict[str, Any]]:
    """Generate time-series income and expense data."""
    cur_start, cur_end, _, _ = resolve_date_range(start_date, end_date, user_id=user_id)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT transaction_date, transaction_type, category, is_refund, ABS(amount) as amt
            FROM transactions
            WHERE is_transfer = 0 AND user_id = ?
            ORDER BY transaction_date ASC;
        """, (user_id,))
        rows = cursor.fetchall()

    if not rows:
        return []

    buckets: Dict[str, Dict[str, float]] = {}
    for r in rows:
        dt_str = r["transaction_date"]
        if interval == "daily":
            key = dt_str
        elif interval == "weekly":
            dt = datetime.datetime.strptime(dt_str, "%Y-%m-%d")
            key = f"{dt.year}-W{dt.isocalendar()[1]:02d}"
        else: # monthly
            key = dt_str[:7]  # YYYY-MM

        if key not in buckets:
            buckets[key] = {"income": 0.0, "expense": 0.0}

        if r["is_refund"] == 1 or r["category"] == "Refunds":
            buckets[key]["expense"] -= float(r["amt"])
        elif r["transaction_type"] == "income":
            buckets[key]["income"] += float(r["amt"])
        else:
            buckets[key]["expense"] += float(r["amt"])

    sorted_keys = sorted(buckets.keys())
    # Keep up to the last 12 periods if monthly, or 30 if daily/weekly
    limit = 12 if interval == "monthly" else 30
    recent_keys = sorted_keys[-limit:]

    trend = []
    for k in recent_keys:
        inc = round(buckets[k]["income"], 2)
        exp = max(0.0, round(buckets[k]["expense"], 2))
        trend.append({
            "period": k,
            "income": inc,
            "expense": exp,
            "net": round(inc - exp, 2)
        })
    return trend

def get_behaviour_analytics(start_date: Optional[str] = None, end_date: Optional[str] = None, user_id: int = 1) -> Dict[str, Any]:
    """Calculate behavioral breakdowns, weekday vs weekend, essential vs discretionary, and anomalies."""
    cur_start, cur_end, _, _ = resolve_date_range(start_date, end_date, user_id=user_id)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, transaction_date, description, merchant, category, ABS(amount) as amt
            FROM transactions
            WHERE is_transfer = 0 AND is_refund = 0 AND category != 'Refunds' AND transaction_type = 'expense' AND user_id = ?
              AND transaction_date >= ? AND transaction_date <= ?;
        """, (user_id, cur_start, cur_end))
        rows = cursor.fetchall()

    weekday_spend = 0.0
    weekend_spend = 0.0
    essential_spend = 0.0
    discretionary_spend = 0.0
    merchant_spend: Dict[str, float] = {}
    category_txns: Dict[str, List[Dict[str, Any]]] = {}

    for r in rows:
        amt = float(r["amt"])
        dt = datetime.datetime.strptime(r["transaction_date"], "%Y-%m-%d")
        
        # Day of week: 0-4 weekday, 5-6 weekend
        if dt.weekday() < 5:
            weekday_spend += amt
        else:
            weekend_spend += amt

        # Essential vs Discretionary
        cat = r["category"]
        if cat in ESSENTIAL_CATEGORIES:
            essential_spend += amt
        else:
            discretionary_spend += amt

        # Merchant concentration
        m = r["merchant"]
        merchant_spend[m] = merchant_spend.get(m, 0.0) + amt

        if cat not in category_txns:
            category_txns[cat] = []
        category_txns[cat].append({
            "id": r["id"],
            "date": r["transaction_date"],
            "merchant": r["merchant"],
            "amount": amt
        })

    total = weekday_spend + weekend_spend
    safe_total = total if total > 0 else 1.0

    # Top 5 merchants
    sorted_merchants = sorted(merchant_spend.items(), key=lambda x: x[1], reverse=True)[:5]
    top_merchants = [
        {"merchant": m, "total_spend": round(amt, 2), "percentage": round((amt / safe_total) * 100.0, 1)}
        for m, amt in sorted_merchants
    ]

    # Anomaly Detection using Median & Median Absolute Deviation (MAD)
    anomalies = []
    for cat, txns in category_txns.items():
        if len(txns) >= 4:
            amts = np.array([t["amount"] for t in txns])
            med = float(np.median(amts))
            mad = float(np.median(np.abs(amts - med)))
            threshold = med + (3.0 * 1.4826 * mad) if mad > 0 else med * 2.5
            
            for t in txns:
                if t["amount"] > threshold and t["amount"] > 1000:
                    anomalies.append({
                        "transaction_id": t["id"],
                        "date": t["date"],
                        "merchant": t["merchant"],
                        "category": cat,
                        "amount": round(t["amount"], 2),
                        "usual_median": round(med, 2),
                        "reason": f"Amount is significantly higher than your typical {cat} purchase (median: ₹{med:,.0f})."
                    })

    return {
        "weekday_spend": round(weekday_spend, 2),
        "weekend_spend": round(weekend_spend, 2),
        "weekday_pct": round((weekday_spend / safe_total) * 100.0, 1),
        "weekend_pct": round((weekend_spend / safe_total) * 100.0, 1),
        "essential_spend": round(essential_spend, 2),
        "discretionary_spend": round(discretionary_spend, 2),
        "essential_pct": round((essential_spend / safe_total) * 100.0, 1),
        "discretionary_pct": round((discretionary_spend / safe_total) * 100.0, 1),
        "top_merchants": top_merchants,
        "anomalies": anomalies
    }

get_behaviour_patterns = get_behaviour_analytics
