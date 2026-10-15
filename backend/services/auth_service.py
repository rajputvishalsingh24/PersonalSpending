import hashlib
import hmac
import secrets
import datetime
from typing import Optional, Dict, Any, Tuple
from backend.config import (
    SESSION_MAX_AGE_SECONDS, PASSWORD_RESET_TOKEN_TTL_MINUTES,
    EMAIL_VERIFICATION_TOKEN_TTL_MINUTES, OTP_TTL_MINUTES
)
from backend.database import get_db

ITERATIONS = 200000

def hash_password(password: str) -> str:
    """Hash password using cryptographically secure PBKDF2-HMAC-SHA256 with 32-byte salt."""
    salt = secrets.token_bytes(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${key.hex()}"

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against stored PBKDF2 hash using timing-safe comparison."""
    if not hashed or not hashed.startswith("pbkdf2_sha256$"):
        return False
    try:
        parts = hashed.split("$")
        if len(parts) != 4:
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_key = bytes.fromhex(parts[3])
        computed_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(computed_key, expected_key)
    except Exception:
        return False

try:
    import phonenumbers
    from phonenumbers import PhoneNumberType, number_type
    PHONENUMBERS_AVAILABLE = True
except ImportError:
    PHONENUMBERS_AVAILABLE = False

def validate_and_normalize_phone(country_code: str, phone: str) -> Tuple[bool, str, str]:
    """
    Validate and normalize phone number using official Google libphonenumber port.
    For Indian numbers (+91):
    - Strictly accepts 10-digit mobile numbers starting with 6, 7, 8, or 9.
    - Rejects landlines, premium rates, and invalid lengths with clear diagnostic messages.
    Returns: (is_valid: bool, e164_phone: str, error_message: str)
    """
    if not phone or not phone.strip():
        return False, "", "Please enter a valid mobile number."

    cc = (country_code or "+91").strip()
    if not cc.startswith("+"):
        cc = "+" + cc

    # Clean digits
    digits = "".join(filter(str.isdigit, phone))

    # India-specific pre-validation
    if cc == "+91":
        # Handle cases where user prefixed 91 or leading 0
        if digits.startswith("91") and len(digits) == 12:
            digits = digits[2:]
        elif digits.startswith("0") and len(digits) == 11:
            digits = digits[1:]

        if len(digits) != 10:
            return False, "", f"Indian mobile numbers must be exactly 10 digits (you entered {len(digits)} digits)."

        if digits[0] not in ("6", "7", "8", "9"):
            return False, "", "Indian mobile numbers must start with 6, 7, 8, or 9. Landlines and non-mobile numbers are not supported for SMS verification."

    full_candidate = f"{cc}{digits}"

    if PHONENUMBERS_AVAILABLE:
        try:
            parsed = phonenumbers.parse(full_candidate, None)
            if not phonenumbers.is_valid_number(parsed):
                return False, "", "Invalid phone number format."

            ntype = number_type(parsed)
            if cc == "+91" and ntype not in (PhoneNumberType.MOBILE, PhoneNumberType.FIXED_LINE_OR_MOBILE):
                return False, "", "Landlines and non-mobile numbers cannot receive SMS OTP."

            e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            return True, e164, ""
        except Exception as e:
            return False, "", f"Invalid phone number: {str(e)}"

    # Regex fallback if phonenumbers is not loaded
    if cc == "+91" and re.match(r"^[6-9]\d{9}$", digits):
        return True, f"+91{digits}", ""
    return False, "", "Invalid mobile number format."

def normalize_phone(country_code: str, phone: str) -> str:
    """Normalize phone number to standard E.164 format (+[country][number])."""
    is_valid, e164, _ = validate_and_normalize_phone(country_code, phone)
    if is_valid:
        return e164
    cc = country_code.replace("+", "").strip()
    p = "".join(filter(str.isdigit, phone))
    if p.startswith(cc) and len(p) > len(cc) + 6:
        return f"+{p}"
    return f"+{cc}{p}"

def normalize_email(email: str) -> str:
    """Normalize email address to lowercase stripped string."""
    return email.strip().lower()

# Sessions Management
def create_session(user_id: int) -> str:
    """Create a new server-side session in SQLite and return secure session token."""
    session_id = secrets.token_urlsafe(48)
    now = datetime.datetime.now(datetime.timezone.utc)
    expires = now + datetime.timedelta(seconds=SESSION_MAX_AGE_SECONDS)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sessions (session_id, user_id, created_at, expires_at, revoked)
            VALUES (?, ?, ?, ?, 0);
        """, (session_id, user_id, now.isoformat(), expires.isoformat()))
        
    return session_id

def validate_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Validate session token against SQLite sessions table and return authenticated user."""
    if not session_id:
        return None
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.session_id, s.expires_at, s.revoked,
                   u.id, u.full_name, u.display_name, u.email, u.phone,
                   u.email_verified, u.phone_verified, u.account_status,
                   u.default_currency, u.created_at
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.session_id = ? AND s.revoked = 0 AND s.expires_at > ?;
        """, (session_id, now_iso))
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)

def revoke_session(session_id: str) -> None:
    """Revoke a specific session on logout."""
    if not session_id:
        return
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE sessions SET revoked = 1 WHERE session_id = ?;", (session_id,))

def revoke_all_user_sessions(user_id: int) -> None:
    """Revoke all active sessions for a user upon security events or password changes."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE sessions SET revoked = 1 WHERE user_id = ?;", (user_id,))

# OTP and Verification Tokens
def hash_token(raw_token: str) -> str:
    """Generate SHA-256 hash for storing tokens and OTPs securely in SQLite."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

def create_phone_otp(phone: str, user_id: Optional[int] = None) -> str:
    """
    Generate a 6-digit numeric OTP, save its cryptographic hash in SQLite,
    and return the plain OTP for provider delivery.
    """
    otp_code = str(secrets.randbelow(900000) + 100000)
    token_hash = hash_token(otp_code)
    now = datetime.datetime.now(datetime.timezone.utc)
    expires = now + datetime.timedelta(minutes=OTP_TTL_MINUTES)
    
    with get_db() as conn:
        cursor = conn.cursor()
        # Invalidate previous unused OTPs for this phone number
        cursor.execute("""
            UPDATE verification_tokens SET used = 1 
            WHERE recipient = ? AND token_type = 'phone_otp' AND used = 0;
        """, (phone,))
        
        cursor.execute("""
            INSERT INTO verification_tokens (
                user_id, token_type, token_hash, recipient, expires_at, attempts, used, created_at
            ) VALUES (?, 'phone_otp', ?, ?, ?, 0, 0, ?);
        """, (user_id, token_hash, phone, expires.isoformat(), now.isoformat()))
        
    return otp_code

def verify_phone_otp(phone: str, otp_code: str) -> Tuple[bool, str, Optional[int]]:
    """
    Verify 6-digit OTP against SQLite with attempt limit and expiry checks.
    Returns: (is_valid: bool, error_message: str, user_id: Optional[int])
    """
    token_hash = hash_token(otp_code.strip())
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, token_hash, expires_at, attempts, used
            FROM verification_tokens
            WHERE recipient = ? AND token_type = 'phone_otp' AND used = 0
            ORDER BY id DESC LIMIT 1;
        """, (phone,))
        row = cursor.fetchone()
        
        if not row:
            return False, "No active OTP found. Please request a new verification code.", None
            
        token_id = row["id"]
        attempts = row["attempts"]
        expires_at = row["expires_at"]
        expected_hash = row["token_hash"]
        user_id = row["user_id"]
        
        if attempts >= 5:
            cursor.execute("UPDATE verification_tokens SET used = 1 WHERE id = ?;", (token_id,))
            return False, "Too many incorrect attempts. Please request a new OTP code.", None
            
        if now_iso > expires_at:
            cursor.execute("UPDATE verification_tokens SET used = 1 WHERE id = ?;", (token_id,))
            return False, "This verification code has expired. Please request a new code.", None
            
        if not hmac.compare_digest(token_hash, expected_hash):
            cursor.execute("UPDATE verification_tokens SET attempts = attempts + 1 WHERE id = ?;", (token_id,))
            remaining = 5 - (attempts + 1)
            return False, f"Incorrect code. {remaining} attempt(s) remaining.", None
            
        # Success: mark token as used
        cursor.execute("UPDATE verification_tokens SET used = 1 WHERE id = ?;", (token_id,))
        return True, "", user_id

def create_password_reset_token(user_id: int, email: str) -> str:
    """Generate secure password reset token and return plain token for email delivery."""
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_token(raw_token)
    now = datetime.datetime.now(datetime.timezone.utc)
    expires = now + datetime.timedelta(minutes=PASSWORD_RESET_TOKEN_TTL_MINUTES)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE verification_tokens SET used = 1
            WHERE recipient = ? AND token_type = 'password_reset' AND used = 0;
        """, (email,))
        
        cursor.execute("""
            INSERT INTO verification_tokens (
                user_id, token_type, token_hash, recipient, expires_at, attempts, used, created_at
            ) VALUES (?, 'password_reset', ?, ?, ?, 0, 0, ?);
        """, (user_id, token_hash, email, expires.isoformat(), now.isoformat()))
        
    return raw_token

def verify_password_reset_token(email: str, raw_token: str) -> Tuple[bool, str, Optional[int]]:
    """Validate password reset token and return user_id."""
    token_hash = hash_token(raw_token.strip())
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, expires_at, used
            FROM verification_tokens
            WHERE recipient = ? AND token_type = 'password_reset' AND token_hash = ? AND used = 0;
        """, (email, token_hash))
        row = cursor.fetchone()
        
        if not row:
            return False, "Invalid or expired password reset link.", None
            
        if now_iso > row["expires_at"]:
            cursor.execute("UPDATE verification_tokens SET used = 1 WHERE id = ?;", (row["id"],))
            return False, "This password reset link has expired. Please request a new one.", None
            
        return True, "", row["user_id"]

def consume_password_reset_token(email: str, raw_token: str) -> None:
    """Mark password reset token as used."""
    token_hash = hash_token(raw_token.strip())
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE verification_tokens SET used = 1
            WHERE recipient = ? AND token_type = 'password_reset' AND token_hash = ?;
        """, (email, token_hash))

def create_email_verification_token(user_id: int, email: str) -> str:
    """Generate secure email verification token and return plain token for email dispatch."""
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_token(raw_token)
    now = datetime.datetime.now(datetime.timezone.utc)
    expires = now + datetime.timedelta(minutes=EMAIL_VERIFICATION_TOKEN_TTL_MINUTES)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE verification_tokens SET used = 1
            WHERE recipient = ? AND token_type = 'email_verification' AND used = 0;
        """, (email,))
        
        cursor.execute("""
            INSERT INTO verification_tokens (
                user_id, token_type, token_hash, recipient, expires_at, attempts, used, created_at
            ) VALUES (?, 'email_verification', ?, ?, ?, 0, 0, ?);
        """, (user_id, token_hash, email, expires.isoformat(), now.isoformat()))
        
    return raw_token

def verify_email_verification_token(email: str, raw_token: str) -> Tuple[bool, str, Optional[int]]:
    """Validate email verification token and return matching user_id."""
    token_hash = hash_token(raw_token.strip())
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, expires_at, used
            FROM verification_tokens
            WHERE recipient = ? AND token_type = 'email_verification' AND token_hash = ? AND used = 0;
        """, (email, token_hash))
        row = cursor.fetchone()
        
        if not row:
            return False, "Invalid or expired verification link.", None
            
        if now_iso > row["expires_at"]:
            cursor.execute("UPDATE verification_tokens SET used = 1 WHERE id = ?;", (row["id"],))
            return False, "This verification link has expired. Please request a new one.", None
            
        return True, "", row["user_id"]

def consume_email_verification_token(email: str, raw_token: str) -> None:
    """Mark email verification token as consumed."""
    token_hash = hash_token(raw_token.strip())
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE verification_tokens SET used = 1
            WHERE recipient = ? AND token_type = 'email_verification' AND token_hash = ?;
        """, (email, token_hash))

