import sqlite3
from typing import List, Dict, Any, Optional
from backend.services.spending_analyzer import get_category_analytics, get_behaviour_patterns, resolve_date_range
from backend.services.recurring_detector import detect_recurring_patterns

DISCRETIONARY_CATEGORIES = {
    "Restaurants and Food Delivery", "Food Delivery", "Restaurants and Cafés",
    "Shopping", "Entertainment", "Subscriptions", "Personal Care", "Travel", "Other"
}

def analyze_savings_opportunities(start_date: Optional[str] = None, end_date: Optional[str] = None, user_id: int = 1) -> List[Dict[str, Any]]:
    """
    Generate realistic, data-driven savings opportunity scenarios from transaction history.
    Never invents records or promises guaranteed outcomes.
    """
    categories_data = get_category_analytics(start_date, end_date, user_id=user_id)
    recurring_patterns = detect_recurring_patterns(user_id=user_id)
    cur_start, cur_end, prev_start, prev_end = resolve_date_range(start_date, end_date, user_id=user_id)

    opportunities: List[Dict[str, Any]] = []

    # 1. Opportunity: Material Spending Increases in Discretionary Categories
    for cat in categories_data:
        cat_name = cat["category"]
        abs_change = cat["absolute_change"]
        pct_change = cat["percentage_change"]
        total = cat["total_spend"]

        if pct_change and pct_change >= 20.0 and abs_change >= 1000 and cat_name in DISCRETIONARY_CATEGORIES:
            potential_monthly = round(abs_change * 0.5, 2)
            opportunities.append({
                "id": f"opp_increase_{cat_name.lower().replace(' ', '_')}",
                "opportunity_type": "spending_increase",
                "title": f"Elevated {cat_name} Spending",
                "category": cat_name,
                "merchant": None,
                "estimated_potential_monthly_savings": potential_monthly,
                "baseline_spending": cat["previous_period_spend"],
                "calculation_method": f"Compared {cur_start}..{cur_end} against baseline {prev_start}..{prev_end}.",
                "assumptions": f"Assuming a 50% moderation of recent ₹{abs_change:,.0f} surge back towards typical baseline.",
                "confidence": "High" if cat["transaction_count"] >= 3 else "Medium",
                "suggested_action": f"Review recent purchases in {cat_name} to curb non-essential discretionary surge.",
                "supporting_transactions_count": cat["transaction_count"]
            })

    # 2. Opportunity: Discretionary 10% Moderation Scenario
    for cat in categories_data:
        cat_name = cat["category"]
        total = cat["total_spend"]
        if cat_name in DISCRETIONARY_CATEGORIES and total >= 3000:
            potential_monthly = round(total * 0.10, 2)
            opportunities.append({
                "id": f"opp_scenario_10pct_{cat_name.lower().replace(' ', '_')}",
                "opportunity_type": "discretionary_reduction",
                "title": f"10% Optimization Scenario in {cat_name}",
                "category": cat_name,
                "merchant": None,
                "estimated_potential_monthly_savings": potential_monthly,
                "baseline_spending": total,
                "calculation_method": f"10% reduction applied to current period expenditure of ₹{total:,.0f}.",
                "assumptions": "Illustrative behavioral scenario based on cutting 1 out of 10 discretionary orders.",
                "confidence": "High",
                "suggested_action": f"Skipping or cooking 2 meals instead of food delivery would retain ~₹{potential_monthly:,.0f}/month.",
                "supporting_transactions_count": cat["transaction_count"]
            })

    # 3. Opportunity: Subscriptions and Recurring Service Review
    active_subs = [p for p in recurring_patterns if p["is_subscription"] and p["status"] != "dismissed"]
    if active_subs:
        total_sub_monthly = sum(p["average_amount"] for p in active_subs if p["frequency"] == "monthly")
        for sub in active_subs[:3]:
            annual_cost = sub["annual_estimate"]
            opportunities.append({
                "id": f"opp_sub_{sub['merchant'].lower().replace(' ', '_')}",
                "opportunity_type": "subscription_review",
                "title": f"Subscription Audit: {sub['merchant']}",
                "category": sub["category"],
                "merchant": sub["merchant"],
                "estimated_potential_monthly_savings": sub["average_amount"],
                "baseline_spending": annual_cost,
                "calculation_method": f"Observed recurring charge of ₹{sub['average_amount']:,.0f} ({sub['frequency']}).",
                "assumptions": f"Total annual expenditure is ₹{annual_cost:,.0f}. Potential savings if subscription is underutilized or paused.",
                "confidence": "High" if sub["confidence_score"] >= 0.8 else "Medium",
                "suggested_action": f"Verify whether your {sub['merchant']} plan is actively utilized or can be downgraded.",
                "supporting_transactions_count": sub["occurrences_count"]
            })

    # 4. Opportunity: Bank & Payment Fees and Charges
    for cat in categories_data:
        if cat["category"] == "Fees and Charges" and cat["total_spend"] > 0:
            opportunities.append({
                "id": "opp_fees_charges",
                "opportunity_type": "avoidable_fees",
                "title": "Banking and Service Charges",
                "category": "Fees and Charges",
                "merchant": None,
                "estimated_potential_monthly_savings": cat["total_spend"],
                "baseline_spending": cat["total_spend"],
                "calculation_method": f"Sum of explicit fees & charges in current period (₹{cat['total_spend']:,.0f}).",
                "assumptions": "Assumes avoidance of late payment penalties, ATM withdrawal surcharges, or fee waivers.",
                "confidence": "High",
                "suggested_action": "Review account balance maintenance and auto-pay settings to avoid penalty charges.",
                "supporting_transactions_count": cat["transaction_count"]
            })

    return opportunities
