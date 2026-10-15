import csv
import io
import json
import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Response, Query, HTTPException, status, Depends
from backend.database import get_db
from backend.models import RestoreBackupRequest
from backend.services.spending_analyzer import get_summary_metrics, get_category_analytics, get_spending_trends, resolve_date_range
from backend.services.budget_analyzer import analyze_budgets
from backend.services.recurring_detector import detect_recurring_patterns
from backend.services.insights_engine import generate_insights
from backend.services.backup_service import create_database_backup, list_database_backups, restore_database_backup
from backend.routers.auth import get_current_user

router = APIRouter(prefix="/api/reports", tags=["Reports & Management"])

@router.get("/monthly")
async def get_monthly_report(
    month: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Generate a comprehensive monthly report including KPIs, category distributions, and budget health for authenticated user."""
    user_id = current_user["id"]
    start_date = f"{month}-01" if month else None
    end_date = None
    if start_date:
        parts = month.split("-")
        import calendar
        _, last_day = calendar.monthrange(int(parts[0]), int(parts[1]))
        end_date = f"{month}-{last_day:02d}"

    summary = get_summary_metrics(start_date, end_date, user_id=user_id)
    categories = get_category_analytics(start_date, end_date, user_id=user_id)
    budgets = analyze_budgets(month, user_id=user_id)
    recurring = detect_recurring_patterns(user_id=user_id)

    return {
        "period": summary["reporting_period"],
        "summary": summary,
        "categories": categories,
        "budgets": budgets,
        "recurring_payments": [r for r in recurring if r["status"] != "dismissed"][:5]
    }

@router.get("/export")
@router.get("/export/csv")
async def export_transactions_csv(
    category: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Export transactions to a clean, standard CSV file for authenticated user."""
    user_id = current_user["id"]
    query = "SELECT transaction_date, merchant, description, amount, transaction_type, category, subcategory, currency, payment_method, is_recurring, is_transfer, is_refund, notes FROM transactions WHERE user_id = ?"
    params = [user_id]
    if category:
        query += " AND category = ?"
        params.append(category)
    if start_date:
        query += " AND transaction_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND transaction_date <= ?"
        params.append(end_date)
    query += " ORDER BY transaction_date DESC;"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Date", "Merchant", "Description", "Amount", "Type", "Category",
        "Subcategory", "Currency", "Payment Method", "Is Recurring", "Is Transfer", "Is Refund", "Notes"
    ])

    for r in rows:
        writer.writerow([
            r["transaction_date"],
            r["merchant"],
            r["description"],
            r["amount"],
            r["transaction_type"],
            r["category"],
            r["subcategory"],
            r["currency"],
            r["payment_method"],
            "Yes" if r["is_recurring"] else "No",
            "Yes" if r["is_transfer"] else "No",
            "Yes" if r["is_refund"] else "No",
            r["notes"]
        ])

    csv_data = output.getvalue()
    filename = f"spendsense_export_{datetime.date.today().strftime('%Y%m%d')}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/export/json")
async def export_data_json(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Export complete user financial data as a structured JSON file."""
    user_id = current_user["id"]
    with get_db() as conn:
        cursor = conn.cursor()

        # User Profile (safe fields)
        cursor.execute("SELECT id, full_name, display_name, email, phone, default_currency, created_at FROM users WHERE id = ?;", (user_id,))
        user_info = dict(cursor.fetchone() or {})

        # Categories
        cursor.execute("SELECT id, category_name, category_type, parent_category, is_default FROM categories WHERE user_id = ?;", (user_id,))
        categories = [dict(r) for r in cursor.fetchall()]

        # Transactions
        cursor.execute("SELECT id, transaction_date, description, merchant, amount, transaction_type, category, subcategory, currency, payment_method, is_recurring, is_transfer, is_refund, notes FROM transactions WHERE user_id = ? ORDER BY transaction_date DESC;", (user_id,))
        transactions = [dict(r) for r in cursor.fetchall()]

        # Budgets
        cursor.execute("SELECT id, category, budget_amount, period_type FROM budgets WHERE user_id = ?;", (user_id,))
        budgets = [dict(r) for r in cursor.fetchall()]

        # Recurring
        cursor.execute("SELECT id, merchant, category, average_amount, frequency, confidence_score, status, is_subscription FROM recurring_transactions WHERE user_id = ?;", (user_id,))
        recurring = [dict(r) for r in cursor.fetchall()]

        # Insights
        cursor.execute("SELECT id, insight_type, title, summary, severity, suggested_action FROM insights WHERE user_id = ?;", (user_id,))
        insights = [dict(r) for r in cursor.fetchall()]

    export_payload = {
        "export_metadata": {
            "app": "SpendSense",
            "version": "2.0.0",
            "exported_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "currency": user_info.get("default_currency", "INR")
        },
        "user": user_info,
        "categories": categories,
        "budgets": budgets,
        "recurring_payments": recurring,
        "insights": insights,
        "transactions_count": len(transactions),
        "transactions": transactions
    }

    json_str = json.dumps(export_payload, indent=2, ensure_ascii=False)
    filename = f"spendsense_full_data_{datetime.date.today().strftime('%Y%m%d')}.json"
    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# =====================================================================
# Database Backup & Restore Endpoints
# =====================================================================

@router.post("/backup")
async def trigger_backup(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Trigger an atomic SQLite backup verified with PRAGMA integrity_check."""
    try:
        backup_info = create_database_backup()
        return {
            "success": True,
            "message": f"Atomic database backup successfully created: {backup_info['filename']}",
            "backup": backup_info
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backup creation failed: {str(e)}"
        )

@router.get("/backups")
async def list_backups(current_user: Dict[str, Any] = Depends(get_current_user)):
    """List all available database backups."""
    backups = list_database_backups()
    return {
        "success": True,
        "count": len(backups),
        "backups": backups
    }

@router.post("/restore")
async def restore_backup(
    req: RestoreBackupRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Restore database from a specified backup file after verifying integrity."""
    try:
        result = restore_database_backup(req.backup_filename)
        return {
            "success": True,
            "message": f"Database successfully restored from {req.backup_filename}.",
            "details": result
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Restore failed: {str(e)}")

@router.post("/demo-data")
async def load_demo_data(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Populate database with a rich, multi-month realistic financial dataset for authenticated user."""
    user_id = current_user["id"]
    from backend.data_generator import generate_demo_dataset
    count = generate_demo_dataset(user_id=user_id)
    # Refresh analytics
    detect_recurring_patterns(user_id=user_id)
    generate_insights(user_id=user_id)
    return {"message": f"Successfully loaded {count} realistic demonstration transactions across 3 months."}

@router.post("/reset-data")
async def reset_all_data(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Clear all transactions, uploads, budgets, recurring items, and custom insights safely for authenticated user."""
    user_id = current_user["id"]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transactions WHERE user_id = ?;", (user_id,))
        cursor.execute("DELETE FROM uploads WHERE user_id = ?;", (user_id,))
        cursor.execute("DELETE FROM budgets WHERE user_id = ?;", (user_id,))
        cursor.execute("DELETE FROM recurring_transactions WHERE user_id = ?;", (user_id,))
        cursor.execute("DELETE FROM insights WHERE user_id = ?;", (user_id,))
        cursor.execute("DELETE FROM category_mappings WHERE user_id = ?;", (user_id,))

    return {"message": "All your transaction, budget, and analytical records have been reset successfully."}
