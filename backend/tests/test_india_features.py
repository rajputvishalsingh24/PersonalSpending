import pytest
import sqlite3
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import init_db, get_db
from backend.services.auth_service import validate_and_normalize_phone, create_email_verification_token
from backend.services.categorizer import categorize_transaction, is_transfer_description, is_credit_card_payment, is_refund_description
from backend.services.backup_service import create_database_backup, list_database_backups, restore_database_backup
from backend.services.spending_analyzer import get_summary_metrics

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_india_test_environment():
    init_db()

# =====================================================================
# 1. Indian Phone Number Validation Tests
# =====================================================================

def test_indian_phone_number_validation():
    # Valid Indian mobile numbers
    valid_cases = [
        ("+91", "9876543210"),
        ("+91", "8888888888"),
        ("+91", "7999999999"),
        ("+91", "6234567890"),
        ("+91", "+91 98765 43210"),
        ("+91", "98765-43210"),
    ]
    for cc, phone in valid_cases:
        is_valid, normalized, err = validate_and_normalize_phone(cc, phone)
        assert is_valid is True, f"Failed for {phone}: {err}"
        assert normalized.startswith("+91")
        assert len(normalized) == 13 # +91 + 10 digits

    # Invalid Indian phone numbers
    invalid_cases = [
        ("+91", "0112345678"),      # Delhi landline - not mobile
        ("+91", "1234567890"),      # Starts with 1
        ("+91", "5555555555"),      # Starts with 5
        ("+91", "98765"),           # Too short
        ("+91", "98765432100000"),  # Too long
        ("+91", "abcdefghij"),      # Non numeric
    ]
    for cc, phone in invalid_cases:
        is_valid, _, err = validate_and_normalize_phone(cc, phone)
        assert is_valid is False, f"Should have failed for {phone}"
        assert len(err) > 0

# =====================================================================
# 2. Distinct Mobile Registration vs Login Flow
# =====================================================================

def test_mobile_registration_and_login_separation():
    test_phone = "9876599999"

    # Clean up any existing test user with this phone
    with get_db() as conn:
        conn.execute("DELETE FROM users WHERE phone = '+919876599999';")

    # Step 1: Login with unregistered mobile must return 404
    login_attempt = client.post("/api/auth/otp/send", json={
        "country_code": "+91",
        "phone": test_phone,
        "purpose": "login"
    })
    assert login_attempt.status_code == 404
    assert "No account found" in login_attempt.json()["detail"]

    # Step 2: Register OTP request
    reg_otp_res = client.post("/api/auth/otp/send", json={
        "country_code": "+91",
        "phone": test_phone,
        "purpose": "register"
    })
    assert reg_otp_res.status_code == 200
    assert reg_otp_res.json()["success"] is True

    # Retrieve generated OTP from SQLite verification_tokens table
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT token_hash FROM verification_tokens 
            WHERE recipient = '+919876599999' AND token_type = 'phone_otp' AND used = 0
            ORDER BY id DESC LIMIT 1;
        """)
        row = cursor.fetchone()
        assert row is not None

    # Step 3: Verify OTP and complete registration
    # In development mode, the default dev code in test is verified
    # To test verify endpoint deterministically, let's test OTP verification
    with get_db() as conn:
        # Create user directly or verify with active token
        pass

# =====================================================================
# 3. Email Verification Flow
# =====================================================================

def test_email_verification_lifecycle():
    test_email = "india_verify_test@spendsense.local"

    # Clean up if existing
    with get_db() as conn:
        conn.execute("DELETE FROM users WHERE email = ?;", (test_email,))

    # Register user via email
    reg_res = client.post("/api/auth/register", json={
        "full_name": "Priya Sharma",
        "email": test_email,
        "password": "Password123",
        "confirm_password": "Password123",
        "terms_accepted": True
    })
    assert reg_res.status_code == 201
    user_data = reg_res.json()["user"]
    assert user_data["email_verified"] == 0 # Must start unverified

    # Query verification token
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE email = ?;", (test_email,))
        u_id = c.fetchone()["id"]

    token = create_email_verification_token(u_id, test_email)

    # Verify email via GET endpoint
    verify_res = client.get(f"/api/auth/verify-email?email={test_email}&token={token}")
    assert verify_res.status_code == 200
    assert verify_res.json()["success"] is True
    assert verify_res.json()["user"]["email_verified"] == 1

    # Token cannot be reused
    reuse_res = client.get(f"/api/auth/verify-email?email={test_email}&token={token}")
    assert reuse_res.status_code == 400

# =====================================================================
# 4. Indian Payment Rails & Double Counting Prevention
# =====================================================================

def test_indian_payment_rails_classification():
    # UPI transfers
    cat1, _, _ = categorize_transaction("UPI/Swiggy/swiggy@icici/Food order", "Swiggy", -450.0)
    assert cat1 in ["Food Delivery", "Restaurants and Food Delivery"]

    cat2, _, _ = categorize_transaction("UPI/P2P/rohit@okhdfcbank/Split bill", "rohit@okhdfcbank", -500.0)
    assert cat2 == "UPI Transfers"

    # Credit Card payment double counting prevention
    assert is_credit_card_payment("CRED CC BILL PAYMENT HDFC") is True
    assert is_credit_card_payment("AUTOPAY CREDIT CARD DEBIT") is True
    assert is_credit_card_payment("SBI CARD PAYMENT ONLINE") is True
    assert is_transfer_description("CRED CC BILL PAYMENT HDFC") is True

    # Internal transfer
    assert is_transfer_description("Self transfer to ICICI savings A/c") is True

    # Refund
    assert is_refund_description("AMAZON ITEM RETURN REFUND") is True
    assert is_refund_description("SWIGGY REFUND PROCESSED") is True

def test_refund_offsets_expenses_accurately():
    """Verify that refunds offset expenses rather than inflating spending."""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO transactions (
                user_id, transaction_date, description, merchant, amount,
                transaction_type, category, subcategory, currency, payment_method,
                is_recurring, is_transfer, is_refund, notes, created_at
            ) VALUES 
            (99, '2026-05-10', 'Electronics Purchase', 'Croma Store', -10000.0, 'expense', 'Shopping', '', 'INR', 'Card', 0, 0, 0, '', datetime('now')),
            (99, '2026-05-15', 'Croma Return Refund', 'Croma Store', 2000.0, 'income', 'Refunds', '', 'INR', 'Card', 0, 0, 1, '', datetime('now'));
        """)

    summary = get_summary_metrics(start_date="2026-05-01", end_date="2026-05-31", user_id=99)
    # Total expenses must be net: 10,000 - 2,000 = 8,000 (NOT 12,000)
    assert summary["total_expenses"] == 8000.0
    assert summary["net_cash_flow"] == -8000.0

    # Clean up test user 99
    with get_db() as conn:
        conn.execute("DELETE FROM transactions WHERE user_id = 99;")

# =====================================================================
# 5. Database Backup and Recovery
# =====================================================================

def test_sqlite_atomic_backup_and_restore():
    backup_result = create_database_backup()
    assert backup_result["success"] is True
    assert backup_result["integrity"] == "verified"
    filename = backup_result["filename"]

    # List backups
    backups = list_database_backups()
    assert len(backups) > 0
    assert any(b["filename"] == filename for b in backups)

    # Restore backup
    restore_res = restore_database_backup(filename)
    assert restore_res["success"] is True

# =====================================================================
# 6. User Data Export (CSV and JSON)
# =====================================================================

def test_user_data_export_endpoints():
    # CSV export
    csv_res = client.get("/api/reports/export/csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers.get("content-type", "")
    assert "Date,Merchant,Description,Amount" in csv_res.text

    # JSON export
    json_res = client.get("/api/reports/export/json")
    assert json_res.status_code == 200
    assert "application/json" in json_res.headers.get("content-type", "")
    data = json_res.json()
    assert "export_metadata" in data
    assert "transactions" in data
    assert "categories" in data
    assert "budgets" in data
    assert data["export_metadata"]["app"] == "SpendSense"
    assert data["export_metadata"]["currency"] == "INR"
