import pytest
from fastapi.testclient import TestClient
from backend.main import app as _app
from backend.database import init_db, get_db
from backend.services.auth_service import hash_password, create_phone_otp, create_password_reset_token

client = TestClient(_app)

@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()
    with get_db() as conn:
        conn.execute("DELETE FROM sessions;")
        conn.execute("DELETE FROM verification_tokens;")
        conn.execute("DELETE FROM transactions WHERE user_id > 1;")
        conn.execute("DELETE FROM budgets WHERE user_id > 1;")
        conn.execute("DELETE FROM uploads WHERE user_id > 1;")
        conn.execute("DELETE FROM users WHERE email != 'demo@spendsense.local';")

def test_email_registration_success():
    res = client.post("/api/auth/register", json={
        "full_name": "Alice Wonderland",
        "email": "alice@example.com",
        "password": "Password123!",
        "confirm_password": "Password123!",
        "terms_accepted": True
    })
    assert res.status_code == 201
    data = res.json()
    assert data["user"]["email"] == "alice@example.com"
    assert data["user"]["full_name"] == "Alice Wonderland"
    assert "session_token" in data
    assert "spendsense_session" in res.cookies

def test_email_registration_duplicate_rejected():
    client.post("/api/auth/register", json={
        "full_name": "Bob Builder",
        "email": "bob@example.com",
        "password": "Password123!",
        "confirm_password": "Password123!",
        "terms_accepted": True
    })
    # Attempt duplicate
    res = client.post("/api/auth/register", json={
        "full_name": "Bob Builder Duplicate",
        "email": "bob@example.com",
        "password": "Password123!",
        "confirm_password": "Password123!",
        "terms_accepted": True
    })
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"].lower()

def test_email_registration_validation():
    # Passwords do not match
    res1 = client.post("/api/auth/register", json={
        "full_name": "Test User",
        "email": "test@example.com",
        "password": "Password123",
        "confirm_password": "DifferentPassword456",
        "terms_accepted": True
    })
    assert res1.status_code == 400

    # Short password
    res2 = client.post("/api/auth/register", json={
        "full_name": "Test User",
        "email": "test@example.com",
        "password": "Pass1",
        "confirm_password": "Pass1",
        "terms_accepted": True
    })
    assert res2.status_code == 400

    # Terms not accepted
    res3 = client.post("/api/auth/register", json={
        "full_name": "Test User",
        "email": "test@example.com",
        "password": "Password123",
        "confirm_password": "Password123",
        "terms_accepted": False
    })
    assert res3.status_code == 400

def test_email_login_success_and_failure():
    # Register user
    client.post("/api/auth/register", json={
        "full_name": "Charlie Chaplin",
        "email": "charlie@example.com",
        "password": "Password123!",
        "confirm_password": "Password123!",
        "terms_accepted": True
    })

    # Successful login
    login_res = client.post("/api/auth/login", json={
        "email": "charlie@example.com",
        "password": "Password123!",
        "remember_me": True
    })
    assert login_res.status_code == 200
    assert "session_token" in login_res.json()
    assert "spendsense_session" in login_res.cookies

    # Failed login - bad password
    bad_res = client.post("/api/auth/login", json={
        "email": "charlie@example.com",
        "password": "WrongPassword999!"
    })
    assert bad_res.status_code == 401

    # Failed login - non-existent user
    non_res = client.post("/api/auth/login", json={
        "email": "nobody@example.com",
        "password": "Password123!"
    })
    assert non_res.status_code == 401

    # Demo user login
    demo_login = client.post("/api/auth/login", json={
        "email": "demo@spendsense.local",
        "password": "demo123",
        "remember_me": False
    })
    assert demo_login.status_code == 200
    assert demo_login.json()["user"]["id"] == 1
    assert demo_login.json()["user"]["email"] == "demo@spendsense.local"

def test_phone_otp_flow():
    phone = "9876543210"
    country_code = "+91"

    # Send OTP
    send_res = client.post("/api/auth/otp/send", json={
        "country_code": country_code,
        "phone": phone
    })
    assert send_res.status_code == 200
    assert send_res.json()["success"] is True

    # Retrieve plain OTP generated directly from database helper for testing
    otp = create_phone_otp("+919876543210")

    # Invalid OTP attempt
    bad_verify = client.post("/api/auth/otp/verify", json={
        "country_code": country_code,
        "phone": phone,
        "otp_code": "000000"
    })
    assert bad_verify.status_code == 400

    # Successful OTP verification
    good_verify = client.post("/api/auth/otp/verify", json={
        "country_code": country_code,
        "phone": phone,
        "otp_code": otp,
        "full_name": "Diana Prince"
    })
    assert good_verify.status_code == 200
    assert good_verify.json()["user"]["phone"] == "+919876543210"
    assert good_verify.json()["user"]["phone_verified"] == 1

def test_password_reset_flow():
    # Register user
    client.post("/api/auth/register", json={
        "full_name": "Evan Wright",
        "email": "evan@example.com",
        "password": "OldPassword123!",
        "confirm_password": "OldPassword123!",
        "terms_accepted": True
    })

    # Forgot password request
    forgot_res = client.post("/api/auth/forgot-password", json={"email": "evan@example.com"})
    assert forgot_res.status_code == 200

    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE email = 'evan@example.com';")
        user_id = c.fetchone()["id"]

    token = create_password_reset_token(user_id, "evan@example.com")

    # Reset with token
    reset_res = client.post("/api/auth/reset-password", json={
        "email": "evan@example.com",
        "token": token,
        "new_password": "NewPassword456!",
        "confirm_password": "NewPassword456!"
    })
    assert reset_res.status_code == 200

    # Old password no longer works
    fail_login = client.post("/api/auth/login", json={
        "email": "evan@example.com",
        "password": "OldPassword123!"
    })
    assert fail_login.status_code == 401

    # New password works
    succ_login = client.post("/api/auth/login", json={
        "email": "evan@example.com",
        "password": "NewPassword456!"
    })
    assert succ_login.status_code == 200

def test_logout_revokes_session():
    reg_res = client.post("/api/auth/register", json={
        "full_name": "Fiona Gallagher",
        "email": "fiona@example.com",
        "password": "Password123!",
        "confirm_password": "Password123!",
        "terms_accepted": True
    })
    session_token = reg_res.json()["session_token"]

    # Profile lookup with token
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {session_token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "fiona@example.com"

    # Logout
    logout_res = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {session_token}"})
    assert logout_res.status_code == 200

    # Verify session revoked
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT revoked FROM sessions WHERE session_id = ?;", (session_token,))
        row = c.fetchone()
        assert row["revoked"] == 1

def test_strict_multi_user_data_isolation():
    """
    Test that User A's transactions, budgets, and analytics are strictly inaccessible to User B.
    """
    # 1. Register User A
    res_a = client.post("/api/auth/register", json={
        "full_name": "User Alpha",
        "email": "alpha@example.com",
        "password": "Password123!",
        "confirm_password": "Password123!",
        "terms_accepted": True
    })
    token_a = res_a.json()["session_token"]
    user_a_id = res_a.json()["user"]["id"]

    # 2. Register User B
    res_b = client.post("/api/auth/register", json={
        "full_name": "User Beta",
        "email": "beta@example.com",
        "password": "Password123!",
        "confirm_password": "Password123!",
        "terms_accepted": True
    })
    token_b = res_b.json()["session_token"]
    user_b_id = res_b.json()["user"]["id"]

    # 3. Insert transaction and budget for User A
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transactions (
                user_id, transaction_date, description, merchant, amount,
                transaction_type, category, subcategory, currency, payment_method,
                is_recurring, is_transfer, is_refund, notes, created_at
            ) VALUES (?, '2026-03-20', 'Alpha Secret Dinner', 'TopSecret Cafe', -5000.0, 'expense', 'Restaurants and Food Delivery', '', 'INR', 'Card', 0, 0, 0, 'Alpha confidential note', '2026-03-20T12:00:00Z');
        """, (user_a_id,))
        txn_a_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO budgets (user_id, category, budget_amount, period_type, created_at)
            VALUES (?, 'Groceries', 8000.0, 'monthly', '2026-03-01T00:00:00Z');
        """, (user_a_id,))
        budget_a_id = cursor.lastrowid

    # 4. User A queries: verifies they can see their transaction
    headers_a = {"Authorization": f"Bearer {token_a}"}
    txns_a = client.get("/api/transactions", headers=headers_a)
    assert txns_a.status_code == 200
    assert txns_a.json()["total_count"] == 1
    assert txns_a.json()["items"][0]["id"] == txn_a_id

    # 5. User B queries transactions: MUST BE EMPTY!
    headers_b = {"Authorization": f"Bearer {token_b}"}
    txns_b = client.get("/api/transactions", headers=headers_b)
    assert txns_b.status_code == 200
    assert txns_b.json()["total_count"] == 0
    assert len(txns_b.json()["items"]) == 0

    # 6. User B attempts direct ID access on User A's transaction -> 404 NOT FOUND
    direct_get = client.get(f"/api/transactions/{txn_a_id}", headers=headers_b)
    assert direct_get.status_code == 404

    # 7. User B attempts to patch User A's transaction -> 404 NOT FOUND
    direct_patch = client.patch(f"/api/transactions/{txn_a_id}", json={"notes": "Hacked"}, headers=headers_b)
    assert direct_patch.status_code == 404

    # 8. User B attempts to delete User A's transaction -> 404 NOT FOUND
    direct_del = client.delete(f"/api/transactions/{txn_a_id}", headers=headers_b)
    assert direct_del.status_code == 404

    # 9. User B queries budgets: does NOT see User A's budget
    budgets_b = client.get("/api/budgets", headers=headers_b)
    assert budgets_b.status_code == 200
    assert len([b for b in budgets_b.json() if b["id"] == budget_a_id]) == 0

    # 10. User B attempts to delete User A's budget -> 404 NOT FOUND
    del_budget_b = client.delete(f"/api/budgets/{budget_a_id}", headers=headers_b)
    assert del_budget_b.status_code == 404

    # 11. User B queries summary: expense is 0.0 (User A's -5000 is isolated)
    summary_b = client.get("/api/analytics/summary", headers=headers_b)
    assert summary_b.status_code == 200
    assert summary_b.json()["total_expenses"] == 0.0
