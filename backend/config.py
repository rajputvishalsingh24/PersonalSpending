import os
from pathlib import Path

# Load .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"
DATA_DIR = BACKEND_DIR / "data"
UPLOAD_DIR = BACKEND_DIR / "temp_uploads"
BACKUP_DIR = DATA_DIR / "backups"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Database - Predictable path in backend/data/spendsense.db
DB_PATH = DATA_DIR / "spendsense.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# App Settings
APP_NAME = "SpendSense — India-First Personal Finance Platform"
APP_VERSION = "2.0.0"
APP_ENV = os.getenv("APP_ENV", "development")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000")
DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "INR")
DEFAULT_COUNTRY_CODE = os.getenv("DEFAULT_COUNTRY_CODE", "+91")
DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "Asia/Kolkata")
MAX_UPLOAD_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB
MAX_BACKUP_RETENTION = int(os.getenv("MAX_BACKUP_RETENTION", "10"))

# Session & Security Settings
SESSION_SECRET = os.getenv("SESSION_SECRET", "spendsense_dev_secret_key_change_in_production_32bytes_min")
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "spendsense_session")
SESSION_MAX_AGE_SECONDS = int(os.getenv("SESSION_MAX_AGE_SECONDS", str(86400 * 7)))  # 7 days
SESSION_COOKIE_SECURE = os.getenv("APP_ENV") == "production"
SESSION_COOKIE_SAMESITE = "lax"

# Token Expiry Settings
PASSWORD_RESET_TOKEN_TTL_MINUTES = int(os.getenv("PASSWORD_RESET_TOKEN_TTL_MINUTES", "30"))
EMAIL_VERIFICATION_TOKEN_TTL_MINUTES = int(os.getenv("EMAIL_VERIFICATION_TOKEN_TTL_MINUTES", "60"))
OTP_TTL_MINUTES = int(os.getenv("OTP_TTL_MINUTES", "10"))

# SMS Provider Integration (Twilio Verify)
SMS_PROVIDER = os.getenv("SMS_PROVIDER", "twilio" if os.getenv("TWILIO_VERIFY_SERVICE_SID") else "console")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_VERIFY_SERVICE_SID = os.getenv("TWILIO_VERIFY_SERVICE_SID", "")

# Email Provider Integration (Resend)
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "resend" if os.getenv("RESEND_API_KEY") else "console")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "SpendSense <noreply@spendsense.local>")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

def validate_production_config():
    """Validate provider credentials when running in production mode."""
    if APP_ENV == "production":
        errors = []
        if SMS_PROVIDER == "twilio":
            if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_VERIFY_SERVICE_SID:
                errors.append("Twilio Verify requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_VERIFY_SERVICE_SID in production.")
        if EMAIL_PROVIDER == "resend":
            if not RESEND_API_KEY:
                errors.append("Resend email requires RESEND_API_KEY in production.")
        if SESSION_SECRET == "spendsense_dev_secret_key_change_in_production_32bytes_min":
            errors.append("SESSION_SECRET must be set to a secure random secret in production.")
        return errors
    return []
