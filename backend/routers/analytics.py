from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException, status, Depends
from backend.models import (
    SummaryMetrics, CategoryAnalyticsItem, TrendPoint,
    BehaviourAnalytics, SavingsOpportunity, RecurringResponse,
    RecurringUpdate, InsightResponse, InsightUpdate
)
from backend.services.spending_analyzer import (
    get_summary_metrics, get_category_analytics,
    get_spending_trends, get_behaviour_patterns
)
from backend.services.savings_analyzer import analyze_savings_opportunities
from backend.services.recurring_detector import detect_recurring_patterns
from backend.services.insights_engine import generate_insights
from backend.database import get_db
from backend.routers.auth import get_current_user

router = APIRouter(tags=["Analytics & Intelligence"])

# Summary
@router.get("/api/analytics/summary", response_model=SummaryMetrics)
async def analytics_summary(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieve key financial metrics and period-over-period comparisons for authenticated user."""
    user_id = current_user["id"]
    return get_summary_metrics(start_date, end_date, user_id=user_id)

# Categories
@router.get("/api/analytics/categories", response_model=List[CategoryAnalyticsItem])
async def analytics_categories(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieve detailed category expenditure breakdown with previous period metrics for authenticated user."""
    user_id = current_user["id"]
    return get_category_analytics(start_date, end_date, user_id=user_id)

# Trends
@router.get("/api/analytics/trends", response_model=List[TrendPoint])
async def analytics_trends(
    interval: str = Query("monthly", pattern="^(daily|weekly|monthly)$"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieve time-series income and expense trends for authenticated user."""
    user_id = current_user["id"]
    return get_spending_trends(interval, start_date, end_date, user_id=user_id)

# Behaviour & Anomalies
@router.get("/api/analytics/behaviour", response_model=BehaviourAnalytics)
async def analytics_behaviour(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieve behavioral spending habits (weekday vs weekend, discretionary vs essential, merchant concentration, anomalies)."""
    user_id = current_user["id"]
    return get_behaviour_patterns(start_date, end_date, user_id=user_id)

# Savings Opportunities
@router.get("/api/analytics/savings", response_model=List[SavingsOpportunity])
async def analytics_savings(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieve data-backed savings scenarios and recurring payment audit recommendations."""
    user_id = current_user["id"]
    return analyze_savings_opportunities(start_date, end_date, user_id=user_id)

# Recurring Transactions Endpoints
@router.get("/api/recurring", response_model=List[RecurringResponse])
async def list_recurring(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieve detected and confirmed recurring payments and subscriptions for authenticated user."""
    user_id = current_user["id"]
    return detect_recurring_patterns(user_id=user_id)

@router.patch("/api/recurring/{recurring_id}", response_model=Dict[str, Any])
async def update_recurring(
    recurring_id: int,
    req: RecurringUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update status, subscription flag, or review notes on a recurring payment."""
    user_id = current_user["id"]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM recurring_transactions WHERE id = ? AND user_id = ?;", (recurring_id, user_id))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Recurring transaction record not found.")

        updates = []
        params = []
        if req.status is not None:
            updates.append("status = ?")
            params.append(req.status)
        if req.is_subscription is not None:
            updates.append("is_subscription = ?")
            params.append(1 if req.is_subscription else 0)
        if req.is_essential is not None:
            updates.append("is_essential = ?")
            params.append(1 if req.is_essential else 0)
        if req.review_notes is not None:
            updates.append("review_notes = ?")
            params.append(req.review_notes)

        if updates:
            params.extend([recurring_id, user_id])
            cursor.execute(f"UPDATE recurring_transactions SET {', '.join(updates)} WHERE id = ? AND user_id = ?;", params)

    return {"message": "Recurring pattern updated successfully."}

# Insights Endpoints
@router.get("/api/insights", response_model=List[InsightResponse])
async def list_insights(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieve prioritized financial intelligence insights for authenticated user."""
    user_id = current_user["id"]
    return generate_insights(start_date, end_date, user_id=user_id)

@router.patch("/api/insights/{insight_id}", response_model=Dict[str, Any])
async def update_insight_status(
    insight_id: int,
    req: InsightUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Mark an insight as reviewed or dismissed."""
    user_id = current_user["id"]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM insights WHERE id = ? AND user_id = ?;", (insight_id, user_id))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Insight not found.")
        cursor.execute("UPDATE insights SET status = ? WHERE id = ? AND user_id = ?;", (req.status, insight_id, user_id))

    return {"message": f"Insight status updated to '{req.status}'."}
