import pytest
import sqlite3
from backend.database import init_db, get_db
from backend.data_generator import generate_demo_dataset
from backend.services.spending_analyzer import get_summary_metrics, get_category_analytics, get_spending_trends, get_behaviour_analytics
from backend.services.recurring_detector import detect_recurring_patterns
from backend.services.budget_analyzer import analyze_budgets
from backend.services.savings_analyzer import analyze_savings_opportunities
from backend.services.insights_engine import generate_insights

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    init_db()
    # Reset and seed demo data
    with get_db() as conn:
        conn.execute("DELETE FROM transactions;")
        conn.execute("DELETE FROM uploads;")
        conn.execute("DELETE FROM budgets;")
        conn.execute("DELETE FROM recurring_transactions;")
        conn.execute("DELETE FROM insights;")
    generate_demo_dataset()

def test_summary_metrics():
    summary = get_summary_metrics()
    assert summary["total_income"] > 0
    assert summary["total_expenses"] > 0
    assert summary["net_cash_flow"] == round(summary["total_income"] - summary["total_expenses"], 2)
    assert summary["savings_rate"] is not None
    assert summary["savings_rate"] > 0
    assert "INR" in summary["currency"]
    assert summary["transaction_count"] > 0

def test_transfer_exclusion():
    """Verify that transfers between own accounts are excluded from expenditure calculations and refunds offset expenses."""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT SUM(ABS(amount)) FROM transactions WHERE is_transfer = 1;")
        transfer_sum = c.fetchone()[0]
        assert transfer_sum > 0  # Transfers exist in DB

    summary = get_summary_metrics()
    # Total expenses must not include the transfer_sum and must deduct refunds
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT COALESCE(SUM(CASE 
                WHEN is_refund = 1 OR category = 'Refunds' THEN -ABS(amount)
                WHEN transaction_type = 'expense' THEN ABS(amount)
                ELSE 0
            END), 0)
            FROM transactions 
            WHERE is_transfer = 0 AND transaction_date >= '2026-10-01' AND transaction_date <= '2026-10-31';
        """)
        expected_expense = round(c.fetchone()[0], 2)
    assert summary["total_expenses"] == expected_expense

def test_category_analytics():
    cats = get_category_analytics()
    assert len(cats) > 0
    total_pct = sum(c["percentage"] for c in cats)
    assert 99.0 <= total_pct <= 101.0  # Sum of percentages should be ~100%
    for c in cats:
        assert c["total_spend"] > 0
        assert c["transaction_count"] > 0

def test_budget_analysis():
    budgets = analyze_budgets()
    assert len(budgets) > 0
    for b in budgets:
        assert b["budget_amount"] > 0
        assert b["utilization_pct"] >= 0
        assert b["status"] in ["On Track", "Approaching Limit", "Over Budget", "Insufficient Data"]
        assert b["remaining_budget"] == round(b["budget_amount"] - b["actual_spending"], 2)

def test_recurring_detection():
    patterns = detect_recurring_patterns()
    # Monthly bills like Netflix, Spotify, Airtel Broadband should be detected
    merchants = [p["merchant"] for p in patterns]
    assert len(patterns) >= 3, f"Expected at least 3 recurring patterns, found {len(patterns)}: {merchants}"
    for p in patterns:
        assert p["confidence_score"] >= 0.60
        assert p["frequency"] in ["weekly", "monthly", "quarterly", "annual", "irregular"]
        assert p["annual_estimate"] > 0

def test_savings_opportunities():
    opps = analyze_savings_opportunities()
    assert len(opps) > 0
    for o in opps:
        assert o["estimated_potential_monthly_savings"] > 0
        assert o["calculation_method"] != ""
        assert o["assumptions"] != ""

def test_insights_generation():
    insights = generate_insights()
    assert len(insights) > 0
    for i in insights:
        assert i["title"] != ""
        assert i["summary"] != ""
        assert i["severity"] in ["info", "low", "medium", "high", "positive"]
        assert i["suggested_action"] != ""
