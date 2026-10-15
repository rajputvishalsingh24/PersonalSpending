import pytest
from fastapi.testclient import TestClient
from backend.main import app as _app
from backend.database import init_db, get_db

client = TestClient(_app)

@pytest.fixture(autouse=True)
def setup_budget_test():
    init_db()
    with get_db() as conn:
        conn.execute("DELETE FROM budgets;")

def test_create_and_read_budget():
    res = client.post(
        "/api/budgets",
        json={"category": "Groceries", "budget_amount": 12000.0, "period_type": "monthly"}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["category"] == "Groceries"
    assert data["budget_amount"] == 12000.0
    assert data["status"] in ["On Track", "Approaching Limit", "Over Budget", "Insufficient Data"]

    budget_id = data["id"]

    # List budgets
    list_res = client.get("/api/budgets")
    assert list_res.status_code == 200
    assert any(b["id"] == budget_id for b in list_res.json())

    # Update budget
    update_res = client.patch(
        f"/api/budgets/{budget_id}",
        json={"budget_amount": 15000.0}
    )
    assert update_res.status_code == 200
    assert update_res.json()["budget_amount"] == 15000.0

    # Delete budget
    del_res = client.delete(f"/api/budgets/{budget_id}")
    assert del_res.status_code == 200

def test_duplicate_budget_rejected():
    client.post(
        "/api/budgets",
        json={"category": "Transport", "budget_amount": 5000.0, "period_type": "monthly"}
    )
    # Duplicate attempt
    dup_res = client.post(
        "/api/budgets",
        json={"category": "Transport", "budget_amount": 7000.0, "period_type": "monthly"}
    )
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json()["detail"]
