import os
import sqlite3
import time
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse

from backend.config import DB_PATH
from backend.database import get_db, get_db_connection
from backend.routers.auth import get_current_user
from backend.models import SqlQueryRequest, SqlQueryResponse, TableRowInsertRequest, TableRowUpdateRequest

router = APIRouter(prefix="/api/admin", tags=["Admin & Database Management"])

def require_owner(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Ensure that the caller is authenticated as an owner/administrator."""
    role = current_user.get("role", "customer")
    if role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Owner/Administrator privileges required."
        )
    return current_user

@router.get("/stats")
async def get_admin_stats(current_user: Dict[str, Any] = Depends(require_owner)):
    """Return high-level database and platform management stats."""
    db_size_bytes = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    size_mb = round(db_size_bytes / (1024 * 1024), 2)
    size_str = f"{size_mb} MB" if size_mb >= 1 else f"{round(db_size_bytes / 1024, 1)} KB"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users;")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'customer';")
        total_customers = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM transactions;")
        total_transactions = cursor.fetchone()[0]

        cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE transaction_type = 'income';")
        total_income = cursor.fetchone()[0]

        cursor.execute("SELECT COALESCE(SUM(ABS(amount)), 0) FROM transactions WHERE transaction_type = 'expense';")
        total_expense = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM budgets;")
        total_budgets = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM recurring_transactions;")
        total_recurring = cursor.fetchone()[0]

        cursor.execute("PRAGMA integrity_check;")
        integrity = cursor.fetchone()[0]

        cursor.execute("SELECT sqlite_version();")
        sqlite_version = cursor.fetchone()[0]

    return {
        "database_file": str(DB_PATH.name),
        "database_size": size_str,
        "database_size_bytes": db_size_bytes,
        "sqlite_version": sqlite_version,
        "integrity_status": integrity,
        "total_users": total_users,
        "total_customers": total_customers,
        "total_transactions": total_transactions,
        "total_volume_inr": round(total_income + total_expense, 2),
        "total_budgets": total_budgets,
        "total_recurring": total_recurring,
        "status": "healthy"
    }

@router.get("/tables")
async def list_tables(current_user: Dict[str, Any] = Depends(require_owner)):
    """List all database tables with column info and record counts."""
    tables = []
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
        table_names = [row[0] for row in cursor.fetchall()]

        for tbl in table_names:
            cursor.execute(f"SELECT COUNT(*) FROM {tbl};")
            count = cursor.fetchone()[0]
            cursor.execute(f"PRAGMA table_info({tbl});")
            columns = [{"name": c["name"], "type": c["type"], "pk": bool(c["pk"])} for c in cursor.fetchall()]
            tables.append({
                "table_name": tbl,
                "row_count": count,
                "columns": columns
            })

    return {"tables": tables}

@router.get("/tables/{table_name}")
async def get_table_data(
    table_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    search: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(require_owner)
):
    """Fetch paginated records from a given table with optional column search."""
    # Whitelist table name to prevent SQL injection
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name = ?;", (table_name,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' does not exist.")

        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = [c["name"] for c in cursor.fetchall()]

        where_clause = ""
        params: List[Any] = []
        if search:
            # Search in string columns
            search_likes = [f"{col} LIKE ?" for col in columns]
            where_clause = "WHERE " + " OR ".join(search_likes)
            params = [f"%{search}%"] * len(columns)

        cursor.execute(f"SELECT COUNT(*) FROM {table_name} {where_clause};", params)
        total_rows = cursor.fetchone()[0]

        offset = (page - 1) * page_size
        cursor.execute(f"SELECT * FROM {table_name} {where_clause} ORDER BY rowid DESC LIMIT ? OFFSET ?;", params + [page_size, offset])
        rows = [dict(r) for r in cursor.fetchall()]

    return {
        "table_name": table_name,
        "columns": columns,
        "rows": rows,
        "total_rows": total_rows,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total_rows + page_size - 1) // page_size)
    }

@router.post("/query", response_model=SqlQueryResponse)
async def execute_sql_query(
    req: SqlQueryRequest,
    current_user: Dict[str, Any] = Depends(require_owner)
):
    """Execute raw SQL statements safely in the database and return columns, rows, and execution time."""
    raw_query = req.query.strip()
    if not raw_query:
        return SqlQueryResponse(columns=[], rows=[], row_count=0, execution_time_ms=0.0, error="Empty SQL query.")

    start_time = time.perf_counter()
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(raw_query)
            exec_time = round((time.perf_counter() - start_time) * 1000, 2)

            if cursor.description:
                columns = [col[0] for col in cursor.description]
                raw_rows = cursor.fetchall()
                rows = [list(r) for r in raw_rows]
                return SqlQueryResponse(
                    columns=columns,
                    rows=rows,
                    row_count=len(rows),
                    execution_time_ms=exec_time,
                    error=None
                )
            else:
                affected = cursor.rowcount
                return SqlQueryResponse(
                    columns=["result"],
                    rows=[[f"Query executed successfully. Rows affected: {affected}"]],
                    row_count=affected if affected >= 0 else 0,
                    execution_time_ms=exec_time,
                    error=None
                )
    except Exception as e:
        exec_time = round((time.perf_counter() - start_time) * 1000, 2)
        return SqlQueryResponse(
            columns=[],
            rows=[],
            row_count=0,
            execution_time_ms=exec_time,
            error=str(e)
        )

@router.delete("/tables/{table_name}/{row_id}")
async def delete_table_row(
    table_name: str,
    row_id: int,
    current_user: Dict[str, Any] = Depends(require_owner)
):
    """Delete a row by ID from any table."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name = ?;", (table_name,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Table not found.")

        cursor.execute(f"DELETE FROM {table_name} WHERE id = ?;", (row_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Row not found or already deleted.")

    return {"message": f"Row {row_id} deleted successfully from {table_name}."}

@router.get("/users")
async def list_all_customers(current_user: Dict[str, Any] = Depends(require_owner)):
    """List all platform users with aggregated financial stats."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                u.id, u.full_name, u.email, u.phone, u.role, u.account_status, u.created_at,
                COUNT(t.id) as transaction_count,
                COALESCE(SUM(CASE WHEN t.transaction_type = 'expense' THEN ABS(t.amount) ELSE 0 END), 0) as total_spent
            FROM users u
            LEFT JOIN transactions t ON u.id = t.user_id
            GROUP BY u.id
            ORDER BY u.created_at DESC;
        """)
        users = [dict(r) for r in cursor.fetchall()]

    return {"users": users}

@router.post("/users/{user_id}/toggle-status")
async def toggle_user_status(user_id: int, current_user: Dict[str, Any] = Depends(require_owner)):
    """Toggle a user's account status between active and suspended."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT account_status FROM users WHERE id = ?;", (user_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found.")

        new_status = "suspended" if row["account_status"] == "active" else "active"
        cursor.execute("UPDATE users SET account_status = ? WHERE id = ?;", (new_status, user_id))

    return {"user_id": user_id, "new_status": new_status}

@router.post("/vacuum")
async def vacuum_database(current_user: Dict[str, Any] = Depends(require_owner)):
    """Run SQLite VACUUM to defragment and optimize database file storage."""
    conn = get_db_connection()
    try:
        conn.execute("VACUUM;")
        return {"message": "Database optimized and defragmented successfully."}
    finally:
        conn.close()
