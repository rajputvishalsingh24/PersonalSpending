import pytest
from fastapi.testclient import TestClient
from backend.main import app as _app
from backend.database import init_db
from backend.data_generator import generate_demo_dataset

client = TestClient(_app)

@pytest.fixture(autouse=True)
def setup_insights_test():
    init_db()
    generate_demo_dataset()

def test_fetch_and_update_insight():
    # 1. Fetch insights
    res = client.get("/api/insights")
    assert res.status_code == 200
    insights = res.json()
    assert len(insights) > 0

    first_id = insights[0]["id"]

    # 2. Update status to reviewed
    patch_res = client.patch(
        f"/api/insights/{first_id}",
        json={"status": "reviewed"}
    )
    assert patch_res.status_code == 200

    # 3. Dismiss insight
    dismiss_res = client.patch(
        f"/api/insights/{first_id}",
        json={"status": "dismissed"}
    )
    assert dismiss_res.status_code == 200

    # 4. Confirm dismissed insight is no longer returned in active list
    res_after = client.get("/api/insights")
    remaining_ids = [i["id"] for i in res_after.json()]
    assert first_id not in remaining_ids
