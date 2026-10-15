import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, status, Depends
from backend.database import get_db
from backend.models import BudgetCreate, BudgetUpdate, BudgetResponse
from backend.services.budget_analyzer import analyze_budgets
from backend.routers.auth import get_current_user

router = APIRouter(prefix="/api/budgets", tags=["Budgets"])

@router.get("", response_model=List[BudgetResponse])
async def list_budgets(
    month: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieve all configured budgets with live spending utilization, days remaining, and drift alerts for authenticated user."""
    user_id = current_user["id"]
    return analyze_budgets(month, user_id=user_id)

@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    req: BudgetCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new monthly overall or category budget for authenticated user."""
    user_id = current_user["id"]
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if category already has a budget for this user
        cursor.execute("SELECT id FROM budgets WHERE category = ? AND period_type = ? AND user_id = ?;", (req.category, req.period_type, user_id))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A {req.period_type} budget for '{req.category}' already exists. Please edit the existing budget."
            )

        cursor.execute("""
            INSERT INTO budgets (user_id, category, budget_amount, period_type, start_date, end_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (user_id, req.category, req.budget_amount, req.period_type, req.start_date, req.end_date, now_iso))
        budget_id = cursor.lastrowid

    # Retrieve and return analyzed budget for this user
    analyzed = analyze_budgets(user_id=user_id)
    created = next((b for b in analyzed if b["id"] == budget_id), None)
    if not created:
        raise HTTPException(status_code=500, detail="Failed to initialize created budget.")
    return BudgetResponse(**created)

@router.patch("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: int,
    req: BudgetUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update a budget amount or dates for authenticated user."""
    user_id = current_user["id"]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM budgets WHERE id = ? AND user_id = ?;", (budget_id, user_id))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Budget not found.")

        updates = []
        params = []
        if req.budget_amount is not None:
            updates.append("budget_amount = ?")
            params.append(req.budget_amount)
        if req.start_date is not None:
            updates.append("start_date = ?")
            params.append(req.start_date)
        if req.end_date is not None:
            updates.append("end_date = ?")
            params.append(req.end_date)

        if updates:
            params.extend([budget_id, user_id])
            cursor.execute(f"UPDATE budgets SET {', '.join(updates)} WHERE id = ? AND user_id = ?;", params)

    analyzed = analyze_budgets(user_id=user_id)
    updated = next((b for b in analyzed if b["id"] == budget_id), None)
    return BudgetResponse(**updated)

@router.delete("/{budget_id}", status_code=status.HTTP_200_OK)
async def delete_budget(
    budget_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a budget for authenticated user."""
    user_id = current_user["id"]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM budgets WHERE id = ? AND user_id = ?;", (budget_id, user_id))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Budget not found.")
        cursor.execute("DELETE FROM budgets WHERE id = ? AND user_id = ?;", (budget_id, user_id))

    return {"message": f"Budget #{budget_id} deleted successfully."}
