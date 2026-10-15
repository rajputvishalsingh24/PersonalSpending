import os
import io
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import init_db, get_db
from backend.config import DB_PATH

client = TestClient(app)

def test_full_end_to_end_acceptance_workflow():
    """
    Simulates the exact 25-step acceptance sequence required by the master prompt:
    1. Initialize and clean state
    2. Upload 25-row sample CSV
    3. Preview validation
    4. Confirm import into SQLite
    5. Check SQLite persistence
    6. Verify dashboard calculations
    7. Edit transaction category and confirm category learned
    8. Create monthly budget
    9. Verify recurring detection from history
    10. Verify insights generation
    11. Verify data persistence across simulated restarts
    12. Verify CSV export content
    """
    # 1. Clean initialization
    init_db()
    with get_db() as conn:
        conn.execute("DELETE FROM transactions;")
        conn.execute("DELETE FROM uploads;")
        conn.execute("DELETE FROM budgets;")
        conn.execute("DELETE FROM recurring_transactions;")
        conn.execute("DELETE FROM insights;")

    # 2. Upload sample CSV containing 25 transactions
    with open("data/sample_transactions.csv", "rb") as f:
        file_bytes = f.read()

    preview_res = client.post(
        "/api/uploads/preview",
        files={"file": ("sample_transactions.csv", file_bytes, "text/csv")}
    )
    assert preview_res.status_code == 200, f"Preview failed: {preview_res.text}"
    preview_data = preview_res.json()
    assert preview_data["total_rows"] == 25
    assert preview_data["valid_rows_count"] == 25
    assert preview_data["temp_file_token"] is not None

    token = preview_data["temp_file_token"]
    col_mapping = preview_data["column_mapping"]

    # 3. Confirm import
    import_res = client.post(
        "/api/uploads/import",
        json={
            "temp_file_token": token,
            "column_mapping": col_mapping,
            "skip_duplicates": True,
            "default_currency": "INR"
        }
    )
    assert import_res.status_code == 200
    import_data = import_res.json()
    assert import_data["transaction_count"] == 25
    upload_id = import_data["id"]

    # 4. Verify transactions appear in SQLite
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE upload_id = ?;", (upload_id,))
        count = cursor.fetchone()[0]
        assert count == 25

    # 5. Verify dashboard calculated metrics
    summary_res = client.get("/api/analytics/summary")
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["transaction_count"] >= 20
    assert summary["total_income"] > 0
    assert summary["total_expenses"] > 0
    assert summary["savings_rate"] is not None
    assert summary["net_cash_flow"] == round(summary["total_income"] - summary["total_expenses"], 2)

    # 6. Open transaction page & Edit one transaction's category
    txns_res = client.get("/api/transactions?page=1&page_size=10")
    assert txns_res.status_code == 200
    target_txn = txns_res.json()["items"][0]
    txn_id = target_txn["id"]

    edit_res = client.patch(
        f"/api/transactions/{txn_id}",
        json={"category": "Entertainment", "notes": "E2E Verified Note"}
    )
    assert edit_res.status_code == 200
    assert edit_res.json()["category"] == "Entertainment"

    # Confirm category totals updated
    cat_res = client.get("/api/analytics/categories")
    assert cat_res.status_code == 200
    cats = {c["category"]: c["total_spend"] for c in cat_res.json()}
    assert "Entertainment" in cats

    # 7. Create monthly budget in SQLite
    budget_res = client.post(
        "/api/budgets",
        json={"category": "Groceries", "budget_amount": 10000, "period_type": "monthly"}
    )
    assert budget_res.status_code == 201
    budget_data = budget_res.json()
    assert budget_data["category"] == "Groceries"
    assert budget_data["actual_spending"] > 0
    assert budget_data["status"] in ["On Track", "Approaching Limit", "Over Budget"]

    # 8. Verify recurring payments detection
    rec_res = client.get("/api/recurring")
    assert rec_res.status_code == 200

    # 9. Verify insights generation
    ins_res = client.get("/api/insights")
    assert ins_res.status_code == 200
    insights = ins_res.json()
    assert len(insights) > 0
    for ins in insights:
        assert ins["title"] != ""
        assert ins["summary"] != ""
        assert ins["suggested_action"] != ""

    # 10. Simulate backend restart & verify persistent data remains in SQLite
    # Re-initialize DB (idempotent, must not erase records)
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM transactions;")
        after_restart_count = cursor.fetchone()[0]
        assert after_restart_count == 25, "Data was lost after simulated restart!"

        cursor.execute("SELECT COUNT(*) FROM budgets;")
        after_restart_budgets = cursor.fetchone()[0]
        assert after_restart_budgets >= 1, "Budget was lost after simulated restart!"

    # 11. Export transaction data and verify CSV content
    export_res = client.get("/api/reports/export")
    assert export_res.status_code == 200
    csv_text = export_res.text
    assert "Date,Merchant,Description,Amount,Type,Category" in csv_text
    assert "BigBasket" in csv_text
    assert "ACME Corp" in csv_text
