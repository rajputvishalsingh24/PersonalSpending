import datetime
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from backend.database import get_db
from backend.models import CategoryCreate, CategoryResponse, UserSettingsResponse
from backend.routers.auth import get_current_user

router = APIRouter(prefix="/api/settings", tags=["Settings"])

class UpdateSettingsRequest(BaseModel):
    display_name: str = None
    default_currency: str = None
    anomaly_sensitivity: str = None
    budget_drift_threshold: str = None
    theme_mode: str = None

@router.get("", response_model=UserSettingsResponse)
async def get_settings(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieve application settings and categories for authenticated user."""
    user_id = current_user["id"]
    display_name = current_user.get("display_name") or current_user.get("full_name") or "User"
    default_currency = current_user.get("default_currency") or "INR"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM user_settings WHERE user_id = ?;", (user_id,))
        settings_dict = {r["key"]: r["value"] for r in cursor.fetchall()}

        cursor.execute("SELECT * FROM categories WHERE user_id = ? OR is_default = 1 ORDER BY category_type ASC, category_name ASC;", (user_id,))
        cat_rows = cursor.fetchall()
        categories = [CategoryResponse(**dict(c)) for c in cat_rows]

    return UserSettingsResponse(
        display_name=display_name,
        default_currency=settings_dict.get("default_currency", default_currency),
        anomaly_sensitivity=settings_dict.get("anomaly_sensitivity", "medium"),
        budget_drift_threshold=settings_dict.get("budget_drift_threshold", "0.80"),
        theme_mode=settings_dict.get("theme_mode", "light"),
        categories=categories
    )

@router.patch("")
async def update_settings(
    req: UpdateSettingsRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update user settings such as default currency or display name for authenticated user."""
    user_id = current_user["id"]
    with get_db() as conn:
        cursor = conn.cursor()
        if req.display_name is not None:
            cursor.execute("UPDATE users SET display_name = ? WHERE id = ?;", (req.display_name, user_id))
        if req.default_currency is not None:
            cursor.execute("UPDATE users SET default_currency = ? WHERE id = ?;", (req.default_currency, user_id))
            cursor.execute("""
                INSERT INTO user_settings (user_id, key, value) VALUES (?, 'default_currency', ?)
                ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value;
            """, (user_id, req.default_currency))
        if req.anomaly_sensitivity is not None:
            cursor.execute("""
                INSERT INTO user_settings (user_id, key, value) VALUES (?, 'anomaly_sensitivity', ?)
                ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value;
            """, (user_id, req.anomaly_sensitivity))
        if req.theme_mode is not None:
            cursor.execute("""
                INSERT INTO user_settings (user_id, key, value) VALUES (?, 'theme_mode', ?)
                ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value;
            """, (user_id, req.theme_mode))

    return {"message": "Settings updated successfully."}

@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    req: CategoryCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Add a new custom spending or income category for authenticated user."""
    user_id = current_user["id"]
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM categories WHERE category_name = ? AND (user_id = ? OR is_default = 1);", (req.category_name, user_id))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Category already exists.")

        cursor.execute("""
            INSERT INTO categories (user_id, category_name, parent_category, category_type, is_default, created_at)
            VALUES (?, ?, ?, ?, 0, ?);
        """, (user_id, req.category_name, req.parent_category, req.category_type, now_iso))
        cat_id = cursor.lastrowid
        cursor.execute("SELECT * FROM categories WHERE id = ? AND user_id = ?;", (cat_id, user_id))
        row = cursor.fetchone()

    return CategoryResponse(**dict(row))
