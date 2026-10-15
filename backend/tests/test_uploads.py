import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import init_db, get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_upload_invalid_format():
    response = client.post(
        "/api/uploads/preview",
        files={"file": ("test.pdf", b"%PDF-1.4 dummy content", "application/pdf")}
    )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]

def test_upload_empty_file():
    response = client.post(
        "/api/uploads/preview",
        files={"file": ("empty.csv", b"", "text/csv")}
    )
    assert response.status_code == 400

def test_upload_csv_preview_and_import():
    csv_content = b"""Date,Description,Merchant,Amount,Type,Category
2026-03-01,Salary Credit,ACME Corp,75000,Credit,Salary
2026-03-02,Grocery Store,BigBasket,-2500,Debit,Groceries
2026-03-05,Electricity Bill,BESCOM,-1200,Debit,Utilities
"""
    # 1. Preview
    res = client.post(
        "/api/uploads/preview",
        files={"file": ("statement.csv", csv_content, "text/csv")}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_rows"] == 3
    assert data["valid_rows_count"] == 3
    assert data["temp_file_token"] is not None

    token = data["temp_file_token"]
    col_mapping = data["column_mapping"]

    # 2. Confirm Import
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
    assert import_data["transaction_count"] == 3
    assert import_data["import_status"] == "completed"

    upload_id = import_data["id"]

    # 3. Check uploads list
    list_res = client.get("/api/uploads")
    assert list_res.status_code == 200
    uploads_list = list_res.json()
    assert any(u["id"] == upload_id for u in uploads_list)

    # 4. Check transactions exist
    txns_res = client.get("/api/transactions")
    assert txns_res.status_code == 200
    assert txns_res.json()["total_count"] >= 3

    # 5. Delete upload
    del_res = client.delete(f"/api/uploads/{upload_id}")
    assert del_res.status_code == 200
