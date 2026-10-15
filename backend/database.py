import sqlite3
import datetime
from contextlib import contextmanager
from typing import Generator
from backend.config import DB_PATH

def get_db_connection() -> sqlite3.Connection:
    """Create and return a configured SQLite connection with foreign keys and WAL enabled."""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database operations with automatic commit and rollback."""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def ensure_column(cursor: sqlite3.Cursor, table: str, col: str, col_def: str) -> None:
    """Safely and idempotently ensure a column exists on a table without losing data."""
    cursor.execute(f"PRAGMA table_info({table});")
    existing_cols = [row["name"] for row in cursor.fetchall()]
    if col not in existing_cols:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def};")

def init_db() -> None:
    """Initialize database tables, indexes, migrations, and seed data idempotently."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with get_db() as conn:
        cursor = conn.cursor()
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # 1. Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL DEFAULT 'SpendSense User',
                display_name TEXT DEFAULT 'User',
                email TEXT UNIQUE,
                phone TEXT UNIQUE,
                password_hash TEXT,
                email_verified INTEGER DEFAULT 0,
                phone_verified INTEGER DEFAULT 0,
                account_status TEXT DEFAULT 'active',
                default_currency TEXT DEFAULT 'INR',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)

        # Run safe migrations for users table if it existed from an older version
        ensure_column(cursor, "users", "full_name", "TEXT NOT NULL DEFAULT 'SpendSense User'")
        ensure_column(cursor, "users", "email", "TEXT")
        ensure_column(cursor, "users", "phone", "TEXT")
        ensure_column(cursor, "users", "password_hash", "TEXT")
        ensure_column(cursor, "users", "email_verified", "INTEGER DEFAULT 0")
        ensure_column(cursor, "users", "phone_verified", "INTEGER DEFAULT 0")
        ensure_column(cursor, "users", "account_status", "TEXT DEFAULT 'active'")
        ensure_column(cursor, "users", "default_currency", "TEXT DEFAULT 'INR'")
        ensure_column(cursor, "users", "role", "TEXT DEFAULT 'customer'")
        ensure_column(cursor, "users", "updated_at", "TEXT DEFAULT ''")

        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email) WHERE email IS NOT NULL;")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_phone ON users(phone) WHERE phone IS NOT NULL;")

        # Audit logs table for Owner / Database administration
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER,
                details TEXT,
                created_at TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);")

        # 2. Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked INTEGER DEFAULT 0
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);")

        # 3. Verification Tokens & OTPs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS verification_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                token_type TEXT NOT NULL, -- 'email_verify', 'password_reset', 'phone_otp'
                token_hash TEXT NOT NULL,
                recipient TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                attempts INTEGER DEFAULT 0,
                used INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tokens_recipient_type ON verification_tokens(recipient, token_type);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tokens_hash ON verification_tokens(token_hash);")
        
        # 4. Uploads table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1 REFERENCES users(id) ON DELETE CASCADE,
                original_filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                transaction_count INTEGER DEFAULT 0,
                import_status TEXT DEFAULT 'completed',
                duplicate_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0
            );
        """)
        ensure_column(cursor, "uploads", "user_id", "INTEGER DEFAULT 1")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_uploads_user ON uploads(user_id);")

        # 5. Categories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1 REFERENCES users(id) ON DELETE CASCADE,
                category_name TEXT NOT NULL,
                parent_category TEXT DEFAULT NULL,
                category_type TEXT NOT NULL, -- 'expense' or 'income'
                is_default INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            );
        """)
        ensure_column(cursor, "categories", "user_id", "INTEGER DEFAULT 1")

        # 6. Learned Merchant Category Mappings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS category_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1 REFERENCES users(id) ON DELETE CASCADE,
                merchant_pattern TEXT NOT NULL,
                category_name TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                created_at TEXT NOT NULL
            );
        """)
        ensure_column(cursor, "category_mappings", "user_id", "INTEGER DEFAULT 1")

        # 7. Transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1 REFERENCES users(id) ON DELETE CASCADE,
                upload_id INTEGER REFERENCES uploads(id) ON DELETE SET NULL,
                transaction_date TEXT NOT NULL,
                description TEXT NOT NULL,
                merchant TEXT NOT NULL,
                amount REAL NOT NULL,
                transaction_type TEXT NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                currency TEXT DEFAULT 'INR',
                payment_method TEXT DEFAULT '',
                is_recurring INTEGER DEFAULT 0,
                is_transfer INTEGER DEFAULT 0,
                is_refund INTEGER DEFAULT 0,
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );
        """)
        ensure_column(cursor, "transactions", "user_id", "INTEGER DEFAULT 1")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_txn_user ON transactions(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_txn_date ON transactions(transaction_date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_txn_category ON transactions(category);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_txn_type ON transactions(transaction_type);")

        # 8. Budgets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1 REFERENCES users(id) ON DELETE CASCADE,
                category TEXT NOT NULL,
                budget_amount REAL NOT NULL,
                period_type TEXT DEFAULT 'monthly',
                start_date TEXT,
                end_date TEXT,
                created_at TEXT NOT NULL
            );
        """)
        ensure_column(cursor, "budgets", "user_id", "INTEGER DEFAULT 1")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_budgets_user ON budgets(user_id);")
        cursor.execute("DROP INDEX IF EXISTS idx_budget_cat_period;")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_budget_user_cat_period ON budgets(user_id, category, period_type);")

        # 9. Recurring transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recurring_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1 REFERENCES users(id) ON DELETE CASCADE,
                merchant TEXT NOT NULL,
                normalized_description TEXT NOT NULL,
                category TEXT NOT NULL,
                average_amount REAL NOT NULL,
                frequency TEXT NOT NULL,
                last_detected_date TEXT NOT NULL,
                next_expected_date TEXT,
                confidence_score REAL NOT NULL,
                status TEXT DEFAULT 'detected',
                is_subscription INTEGER DEFAULT 0,
                is_essential INTEGER DEFAULT 0,
                review_notes TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );
        """)
        ensure_column(cursor, "recurring_transactions", "user_id", "INTEGER DEFAULT 1")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_recurring_user ON recurring_transactions(user_id);")

        # 10. Financial Insights table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1 REFERENCES users(id) ON DELETE CASCADE,
                insight_type TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                supporting_evidence TEXT NOT NULL,
                severity TEXT DEFAULT 'info',
                suggested_action TEXT NOT NULL,
                confidence_level TEXT DEFAULT 'high',
                period TEXT DEFAULT '',
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL
            );
        """)
        ensure_column(cursor, "insights", "user_id", "INTEGER DEFAULT 1")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_insights_user ON insights(user_id);")

        # 11. User Settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER DEFAULT 1 REFERENCES users(id) ON DELETE CASCADE,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                PRIMARY KEY (user_id, key)
            );
        """)
        ensure_column(cursor, "user_settings", "user_id", "INTEGER DEFAULT 1")

        # Ensure default demo user exists (id = 1)
        cursor.execute("SELECT id, email, password_hash, phone FROM users WHERE id = 1;")
        row = cursor.fetchone()
        demo_hash = "pbkdf2_sha256$200000$66c82bfaf522a96217e62fa7989c885f37fcd2846849850251c37851b46f04f9$2f652abdf81754c96387ffaf1746049f6cfb479b943ce932ef91f3fa868377f0"
        
        cursor.execute("SELECT id FROM users WHERE phone = '+919876543210' AND id != 1;")
        demo_phone_taken = cursor.fetchone() is not None
        safe_demo_phone = None if demo_phone_taken else '+919876543210'

        if not row:
            cursor.execute("""
                INSERT INTO users (
                    id, full_name, display_name, email, phone, phone_verified, password_hash, default_currency, email_verified, role, created_at, updated_at
                ) VALUES (1, 'Aarav Sharma', 'Aarav', 'demo@spendsense.local', ?, 1, ?, 'INR', 1, 'customer', ?, ?);
            """, (safe_demo_phone, demo_hash, now_iso, now_iso))
        else:
            try:
                cursor.execute("""
                    UPDATE users SET email = COALESCE(email, 'demo@spendsense.local'),
                                     phone_verified = 1,
                                     password_hash = COALESCE(password_hash, ?),
                                     full_name = COALESCE(full_name, 'Aarav Sharma'),
                                     display_name = COALESCE(display_name, 'Aarav'),
                                     role = COALESCE(role, 'customer'),
                                     email_verified = 1
                    WHERE id = 1;
                """, (demo_hash,))
                if safe_demo_phone and not row["phone"]:
                    cursor.execute("UPDATE users SET phone = ? WHERE id = 1;", (safe_demo_phone,))
            except Exception:
                pass

        # Backfill user_id = 1 on any existing records where user_id is NULL
        for tbl in ["uploads", "categories", "category_mappings", "transactions", "budgets", "recurring_transactions", "insights"]:
            try:
                cursor.execute(f"UPDATE {tbl} SET user_id = 1 WHERE user_id IS NULL;")
            except Exception:
                pass

        # Seed default categories if none exist
        cursor.execute("SELECT COUNT(*) FROM categories;")
        if cursor.fetchone()[0] == 0:
            expense_categories = [
                "Housing and Rent", "Groceries", "Restaurants and Food Delivery", "Transport",
                "Fuel", "Shopping", "Entertainment", "Subscriptions", "Utilities", "Healthcare",
                "Education", "Travel", "Personal Care", "Insurance", "Loan Payments",
                "Fees and Charges", "Gifts and Donations", "Other"
            ]
            income_categories = [
                "Salary", "Freelance Income", "Business Income", "Interest",
                "Investment Income", "Refunds", "Other Income"
            ]
            for cat in expense_categories:
                cursor.execute(
                    "INSERT INTO categories (user_id, category_name, category_type, is_default, created_at) VALUES (1, ?, 'expense', 1, ?);",
                    (cat, now_iso)
                )
            for cat in income_categories:
                cursor.execute(
                    "INSERT INTO categories (user_id, category_name, category_type, is_default, created_at) VALUES (1, ?, 'income', 1, ?);",
                    (cat, now_iso)
                )

        # Seed default Owner / Admin account if none exists
        cursor.execute("SELECT id FROM users WHERE role = 'owner';")
        if not cursor.fetchone():
            cursor.execute("SELECT id FROM users WHERE phone = '+919999999999' OR email = 'owner@spendsense.ai';")
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO users (
                        id, full_name, display_name, email, phone, email_verified, phone_verified,
                        account_status, default_currency, role, created_at, updated_at
                    ) VALUES (
                        99, 'SpendSense Platform Owner', 'Owner', 'owner@spendsense.ai', '+919999999999',
                        1, 1, 'active', 'INR', 'owner', ?, ?
                    );
                """, (now_iso, now_iso))


