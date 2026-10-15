import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import init_db, get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_transaction():
    init_db()
    with get_db() as conn:
        conn.execute("DELETE FROM transactions;")
        conn.execute("""
            INSERT INTO transactions (
                transaction_date, description, merchant, amount,
                transaction_type, category, subcategory, currency, payment_method,
                is_recurring, is_transfer, is_refund, notes, created_at
            ) VALUES ('2026-03-15', 'Dinner at Trattoria', 'Trattoria', -1500.0, 'expense', 'Restaurants and Food Delivery', '', 'INR', 'Card', 0, 0, 0, '', '2026-03-15T12:00:00Z');
        """)

def test_list_and_search_transactions():
    res = client.get("/api/transactions?search=Trattoria")
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] >= 1
    assert data["items"][0]["merchant"] == "Trattoria"

def test_filter_by_category():
    res = client.get("/api/transactions?category=Restaurants and Food Delivery")
    assert res.status_code == 200
    assert res.json()["total_count"] >= 1

def test_update_transaction():
    # Fetch existing
    res = client.get("/api/transactions")
    txn_id = res.json()["items"][0]["id"]

    # Patch category and notes
    patch_res = client.patch(
        f"/api/transactions/{txn_id}",
        json={"category": "Entertainment", "notes": "Business dinner celebration"}
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["category"] == "Entertainment"
    assert updated["notes"] == "Business dinner celebration"

    # Verify merchant preference was learned in database
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT category_name FROM category_mappings WHERE merchant_pattern LIKE '%trattoria%';")
        mapping = c.fetchone()
        assert mapping is not None
        assert mapping[0] == "Entertainment"

def test_delete_transaction():
    res = client.get("/api/transactions")
    txn_id = res.json()["items"][0]["id"]

    del_res = client.delete(f"/api/transactions/{txn_id}")
    assert del_res.status_code == 200

    # Verify 404 on get
    get_res = client.get(f"/api/transactions/{txn_id}")
    assert get_res.status_code == 404
