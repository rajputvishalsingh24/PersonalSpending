import json
import datetime
from typing import List, Dict, Any, Optional
from backend.database import get_db
from backend.services.spending_analyzer import get_summary_metrics, get_category_analytics, get_behaviour_patterns, resolve_date_range
from backend.services.budget_analyzer import analyze_budgets
from backend.services.recurring_detector import detect_recurring_patterns

def generate_insights(start_date: Optional[str] = None, end_date: Optional[str] = None, user_id: int = 1) -> List[Dict[str, Any]]:
    """
    Generate deterministic, data-backed financial insights.
    Stores and synchronizes them in the SQLite insights table.
    """
    cur_start, cur_end, prev_start, prev_end = resolve_date_range(start_date, end_date, user_id=user_id)
    period_key = f"{cur_start[:7]}"

    summary = get_summary_metrics(start_date, end_date, user_id=user_id)
    categories = get_category_analytics(start_date, end_date, user_id=user_id)
    behaviour = get_behaviour_patterns(start_date, end_date, user_id=user_id)
    budgets = analyze_budgets(period_key, user_id=user_id)
    recurring = detect_recurring_patterns(user_id=user_id)

    candidate_insights = []

    # 1. Insufficient data insight if < 5 transactions
    if summary["transaction_count"] < 5:
        candidate_insights.append({
            "insight_type": "insufficient_data",
            "title": "Build Your Financial Baseline",
            "summary": f"You have {summary['transaction_count']} recorded transactions for {period_key}. Uploading a full month of statements will unlock comprehensive trend analysis and recurring expense detection.",
            "supporting_evidence": {"transaction_count": summary["transaction_count"], "period": period_key},
            "severity": "info",
            "suggested_action": "Import statement files covering at least 30–60 days of activity.",
            "confidence_level": "High"
        })

    # 2. Material spending increases (>= 20% and >= ₹1,000)
    for cat in categories:
        if cat["percentage_change"] and cat["percentage_change"] >= 20.0 and cat["absolute_change"] >= 1000:
            candidate_insights.append({
                "insight_type": "spending_increase",
                "title": f"Surge in {cat['category']} Spending",
                "summary": f"Your {cat['category']} expenditure increased by {cat['percentage_change']:.0f}% (+₹{cat['absolute_change']:,.0f}) compared to the previous period. It currently represents {cat['percentage']}% of your total expenses.",
                "supporting_evidence": {
                    "category": cat["category"],
                    "current_spend": cat["total_spend"],
                    "previous_spend": cat["previous_period_spend"],
                    "pct_change": cat["percentage_change"],
                    "transaction_count": cat["transaction_count"]
                },
                "severity": "medium" if cat["percentage"] < 30 else "high",
                "suggested_action": f"Review recent transactions under {cat['category']} to assess whether this surge is temporary or requires a budget rebalance.",
                "confidence_level": "High"
            })

    # 3. Positive spending moderation (>= 15% decrease)
    for cat in categories:
        if cat["percentage_change"] and cat["percentage_change"] <= -15.0 and cat["previous_period_spend"] >= 2000:
            candidate_insights.append({
                "insight_type": "spending_decrease",
                "title": f"Disciplined Spending in {cat['category']}",
                "summary": f"Great progress! Your {cat['category']} expenses decreased by {abs(cat['percentage_change']):.0f}% (-₹{abs(cat['absolute_change']):,.0f}) compared to last period.",
                "supporting_evidence": {
                    "category": cat["category"],
                    "current_spend": cat["total_spend"],
                    "previous_spend": cat["previous_period_spend"],
                    "pct_change": cat["percentage_change"]
                },
                "severity": "positive",
                "suggested_action": f"Maintain your current spending habits in {cat['category']} to sustain this positive cash flow buffer.",
                "confidence_level": "High"
            })

    # 4. Budget overspending and drift warnings
    for b in budgets:
        if b["status"] == "Over Budget":
            candidate_insights.append({
                "insight_type": "budget_warning",
                "title": f"Budget Limit Exceeded: {b['category']}",
                "summary": f"Spending in {b['category']} has reached ₹{b['actual_spending']:,.0f}, exceeding your set budget of ₹{b['budget_amount']:,.0f} by {b['utilization_pct'] - 100:.1f}%.",
                "supporting_evidence": {
                    "category": b["category"],
                    "budget": b["budget_amount"],
                    "actual": b["actual_spending"],
                    "utilization": b["utilization_pct"]
                },
                "severity": "high",
                "suggested_action": "Pause further discretionary spending in this category or adjust your budget allocation.",
                "confidence_level": "High"
            })
        elif b["status"] == "Approaching Limit":
            candidate_insights.append({
                "insight_type": "budget_warning",
                "title": f"Budget Watch: {b['category']} at {b['utilization_pct']}%",
                "summary": f"You have utilized ₹{b['actual_spending']:,.0f} out of your ₹{b['budget_amount']:,.0f} budget with {b['days_remaining']} days remaining in the month.",
                "supporting_evidence": {
                    "category": b["category"],
                    "budget": b["budget_amount"],
                    "actual": b["actual_spending"],
                    "utilization": b["utilization_pct"]
                },
                "severity": "medium",
                "suggested_action": "Pace daily spending carefully over remaining days to prevent budget overflow.",
                "confidence_level": "High"
            })

    # 5. Recurring payment patterns detected
    if recurring:
        active_recs = [r for r in recurring if r["status"] != "dismissed"]
        if active_recs:
            total_monthly_est = sum(r["average_amount"] for r in active_recs if r["frequency"] == "monthly")
            candidate_insights.append({
                "insight_type": "recurring_pattern",
                "title": f"{len(active_recs)} Recurring Expenses Tracked",
                "summary": f"SpendSense detected {len(active_recs)} active repeating payment patterns (approx. ₹{total_monthly_est:,.0f}/month total).",
                "supporting_evidence": {"count": len(active_recs), "monthly_total": total_monthly_est},
                "severity": "info",
                "suggested_action": "Review the Recurring Payments tab to confirm active subscriptions and dismiss false positives.",
                "confidence_level": "High"
            })

    # 6. Unusual Transactions (Anomalies)
    if behaviour["anomalies"]:
        top_anomaly = behaviour["anomalies"][0]
        candidate_insights.append({
            "insight_type": "unusual_transaction",
            "title": f"Unusual Purchase Detected at {top_anomaly['merchant']}",
            "summary": f"A ₹{top_anomaly['amount']:,.0f} transaction in {top_anomaly['category']} on {top_anomaly['date']} is significantly higher than your typical median of ₹{top_anomaly['usual_median']:,.0f}.",
            "supporting_evidence": top_anomaly,
            "severity": "medium",
            "suggested_action": "Verify this transaction to ensure it was expected and correctly categorised.",
            "confidence_level": "Medium"
        })

    # 7. Savings rate insight
    if summary["savings_rate"] is not None:
        sr = summary["savings_rate"]
        if sr >= 25.0:
            candidate_insights.append({
                "insight_type": "positive_behavior",
                "title": f"Strong Savings Rate: {sr}%",
                "summary": f"You retained {sr}% of your qualifying income this period (net cash flow: +₹{summary['net_cash_flow']:,.0f}).",
                "supporting_evidence": {"savings_rate": sr, "net_cash_flow": summary["net_cash_flow"]},
                "severity": "positive",
                "suggested_action": "Consider sweeping surplus funds into high-yield savings or emergency reserves.",
                "confidence_level": "High"
            })
        elif sr < 10.0 and sr > 0:
            candidate_insights.append({
                "insight_type": "savings_opportunity",
                "title": f"Tight Savings Margin: {sr}%",
                "summary": f"Your expenses consumed {100 - sr:.1f}% of recorded income this period, leaving a narrow net surplus of ₹{summary['net_cash_flow']:,.0f}.",
                "supporting_evidence": {"savings_rate": sr, "net_cash_flow": summary["net_cash_flow"]},
                "severity": "medium",
                "suggested_action": "Explore the Savings Opportunities tab to identify top candidate discretionary cutbacks.",
                "confidence_level": "High"
            })

    # Synchronize candidate insights into SQLite
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        for ins in candidate_insights:
            cursor.execute("""
                SELECT id, status FROM insights 
                WHERE insight_type = ? AND title = ? AND period = ? AND user_id = ?;
            """, (ins["insight_type"], ins["title"], period_key, user_id))
            existing = cursor.fetchone()
            if not existing:
                cursor.execute("""
                    INSERT INTO insights (
                        user_id, insight_type, title, summary, supporting_evidence,
                        severity, suggested_action, confidence_level, period, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?);
                """, (
                    user_id,
                    ins["insight_type"],
                    ins["title"],
                    ins["summary"],
                    json.dumps(ins["supporting_evidence"]),
                    ins["severity"],
                    ins["suggested_action"],
                    ins["confidence_level"],
                    period_key,
                    now_str
                ))

        # Query all active or reviewed insights for display
        cursor.execute("""
            SELECT id, insight_type, title, summary, supporting_evidence, severity, suggested_action, confidence_level, period, status, created_at
            FROM insights
            WHERE status != 'dismissed' AND period = ? AND user_id = ?
            ORDER BY 
                CASE severity 
                    WHEN 'high' THEN 1 
                    WHEN 'medium' THEN 2 
                    WHEN 'positive' THEN 3 
                    ELSE 4 
                END ASC, id DESC;
        """, (period_key, user_id))
        rows = cursor.fetchall()

    results = []
    for r in rows:
        try:
            ev = json.loads(r["supporting_evidence"])
        except Exception:
            ev = {}
        results.append({
            "id": r["id"],
            "insight_type": r["insight_type"],
            "title": r["title"],
            "summary": r["summary"],
            "supporting_evidence": ev,
            "severity": r["severity"],
            "suggested_action": r["suggested_action"],
            "confidence_level": r["confidence_level"],
            "period": r["period"],
            "status": r["status"],
            "created_at": r["created_at"]
        })

    return results
