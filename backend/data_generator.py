import datetime
import calendar
from typing import List, Dict, Any
from backend.database import get_db
from backend.services.categorizer import extract_merchant

SAMPLE_TRANSACTION_TEMPLATES = [
    # Salary
    {"day": 1, "desc": "ACME Corp Monthly Payroll Salary", "merchant": "ACME Corp", "amount": 95000.0, "type": "income", "cat": "Salary", "is_transfer": 0, "is_refund": 0},
    # Rent
    {"day": 5, "desc": "Apartment Maintenance and Rental Society", "merchant": "Prestige Heights", "amount": -25000.0, "type": "expense", "cat": "Housing and Rent", "is_transfer": 0, "is_refund": 0},
    # Loan EMI
    {"day": 8, "desc": "HDFC Auto Loan EMI Debited", "merchant": "HDFC Bank Loan", "amount": -11500.0, "type": "expense", "cat": "Loan Payments", "is_transfer": 0, "is_refund": 0},
    # Subscriptions
    {"day": 10, "desc": "Netflix Standard HD Subscription Plan", "merchant": "Netflix", "amount": -649.0, "type": "expense", "cat": "Subscriptions", "is_transfer": 0, "is_refund": 0},
    {"day": 12, "desc": "Spotify Premium Individual Monthly", "merchant": "Spotify", "amount": -119.0, "type": "expense", "cat": "Subscriptions", "is_transfer": 0, "is_refund": 0},
    {"day": 15, "desc": "Airtel Xstream Fiber Broadband Bill", "merchant": "Airtel Broadband", "amount": -999.0, "type": "expense", "cat": "Utilities", "is_transfer": 0, "is_refund": 0},
    # Utilities
    {"day": 16, "desc": "BESCOM Electricity Utility Bill Payment", "merchant": "BESCOM Electric", "amount": -1850.0, "type": "expense", "cat": "Utilities", "is_transfer": 0, "is_refund": 0},
    # Groceries (Weekly)
    {"day": 2, "desc": "BigBasket Fresh Fruits and Provisions", "merchant": "BigBasket", "amount": -2850.0, "type": "expense", "cat": "Groceries", "is_transfer": 0, "is_refund": 0},
    {"day": 9, "desc": "Zepto Quick 10m Groceries Delivery", "merchant": "Zepto Groceries", "amount": -1250.0, "type": "expense", "cat": "Groceries", "is_transfer": 0, "is_refund": 0},
    {"day": 17, "desc": "Nature's Basket Organic Vegetables", "merchant": "Nature's Basket", "amount": -2400.0, "type": "expense", "cat": "Groceries", "is_transfer": 0, "is_refund": 0},
    {"day": 24, "desc": "Blinkit Essentials and Dairy", "merchant": "Blinkit", "amount": -1650.0, "type": "expense", "cat": "Groceries", "is_transfer": 0, "is_refund": 0},
    # Food & Dining
    {"day": 4, "desc": "Swiggy Gourmet Dinner Delivery", "merchant": "Swiggy", "amount": -780.0, "type": "expense", "cat": "Restaurants and Food Delivery", "is_transfer": 0, "is_refund": 0},
    {"day": 11, "desc": "Zomato Weekend Biryani Order", "merchant": "Zomato", "amount": -1240.0, "type": "expense", "cat": "Restaurants and Food Delivery", "is_transfer": 0, "is_refund": 0},
    {"day": 19, "desc": "Starbucks Reserve Coffee and Snacks", "merchant": "Starbucks Cafe", "amount": -650.0, "type": "expense", "cat": "Restaurants and Food Delivery", "is_transfer": 0, "is_refund": 0},
    {"day": 26, "desc": "Barbeque Nation Family Dinner Outing", "merchant": "Barbeque Nation", "amount": -3200.0, "type": "expense", "cat": "Restaurants and Food Delivery", "is_transfer": 0, "is_refund": 0},
    # Fuel & Transport
    {"day": 7, "desc": "HPCL Petrol Station Fuel Dispense", "merchant": "HPCL Fuel", "amount": -2500.0, "type": "expense", "cat": "Fuel", "is_transfer": 0, "is_refund": 0},
    {"day": 21, "desc": "BPCL Auto Gas and Diesel Fill", "merchant": "BPCL Fuel", "amount": -2800.0, "type": "expense", "cat": "Fuel", "is_transfer": 0, "is_refund": 0},
    {"day": 14, "desc": "Uber Airport Drop Ride Cab", "merchant": "Uber Rides", "amount": -850.0, "type": "expense", "cat": "Transport", "is_transfer": 0, "is_refund": 0},
    # Healthcare
    {"day": 18, "desc": "Apollo Pharmacy Prescription Medicines", "merchant": "Apollo Pharmacy", "amount": -1450.0, "type": "expense", "cat": "Healthcare", "is_transfer": 0, "is_refund": 0},
    # Shopping
    {"day": 20, "desc": "Amazon Retail Electronics and Cable", "merchant": "Amazon", "amount": -3499.0, "type": "expense", "cat": "Shopping", "is_transfer": 0, "is_refund": 0},
    # Transfer between own accounts (Excluded from expenses)
    {"day": 3, "desc": "Self Transfer to Savings Reserve Account", "merchant": "Self Account Transfer", "amount": -20000.0, "type": "expense", "cat": "Other", "is_transfer": 1, "is_refund": 0},
    # Refund
    {"day": 22, "desc": "Amazon Item Return Refund Credit", "merchant": "Amazon Refund", "amount": 1200.0, "type": "income", "cat": "Refunds", "is_transfer": 0, "is_refund": 1},
    # Freelance Income
    {"day": 25, "desc": "Upwork Global Freelance Client Disbursement", "merchant": "Upwork Escrow", "amount": 18500.0, "type": "income", "cat": "Freelance Income", "is_transfer": 0, "is_refund": 0}
]

def generate_demo_dataset(user_id: int = 1) -> int:
    """Generate 3 months of consistent, realistic transactions into SQLite for the user."""
    now = datetime.date.today()
    months_to_gen = []
    
    # Generate for (Current month, Current - 1, Current - 2)
    for offset in [2, 1, 0]:
        y = now.year
        m = now.month - offset
        while m <= 0:
            m += 12
            y -= 1
        months_to_gen.append((y, m))

    total_inserted = 0
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    with get_db() as conn:
        cursor = conn.cursor()

        # Create demo upload record
        cursor.execute("""
            INSERT INTO uploads (user_id, original_filename, file_type, uploaded_at, import_status)
            VALUES (?, 'demo_statement_q1.csv', 'CSV', ?, 'completed');
        """, (user_id, now_iso))
        upload_id = cursor.lastrowid

        for idx, (yr, mo) in enumerate(months_to_gen):
            _, max_day = calendar.monthrange(yr, mo)
            # Add spending trend multiplier: 0.9 in month 1, 1.0 in month 2, 1.15 in month 3 (showing spending increase in Restaurants)
            dining_multiplier = 0.85 if idx == 0 else (1.0 if idx == 1 else 1.35)

            for tpl in SAMPLE_TRANSACTION_TEMPLATES:
                d = min(tpl["day"], max_day)
                txn_date = f"{yr:04d}-{mo:02d}-{d:02d}"
                amt = tpl["amount"]
                if tpl["cat"] == "Restaurants and Food Delivery":
                    amt = round(amt * dining_multiplier, 2)

                cursor.execute("""
                    INSERT INTO transactions (
                        user_id, upload_id, transaction_date, description, merchant, amount,
                        transaction_type, category, subcategory, currency, payment_method,
                        is_recurring, is_transfer, is_refund, notes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '', 'INR', 'Online Banking', 0, ?, ?, '', ?);
                """, (
                    user_id,
                    upload_id,
                    txn_date,
                    tpl["desc"],
                    tpl["merchant"],
                    amt,
                    tpl["type"],
                    tpl["cat"],
                    tpl["is_transfer"],
                    tpl["is_refund"],
                    now_iso
                ))
                total_inserted += 1

        cursor.execute("UPDATE uploads SET transaction_count = ? WHERE id = ? AND user_id = ?;", (total_inserted, upload_id, user_id))

        # Seed sample budgets for demonstration
        cursor.execute("INSERT OR IGNORE INTO budgets (user_id, category, budget_amount, period_type, created_at) VALUES (?, '__overall__', 65000, 'monthly', ?);", (user_id, now_iso))
        cursor.execute("INSERT OR IGNORE INTO budgets (user_id, category, budget_amount, period_type, created_at) VALUES (?, 'Groceries', 10000, 'monthly', ?);", (user_id, now_iso))
        cursor.execute("INSERT OR IGNORE INTO budgets (user_id, category, budget_amount, period_type, created_at) VALUES (?, 'Restaurants and Food Delivery', 6000, 'monthly', ?);", (user_id, now_iso))
        cursor.execute("INSERT OR IGNORE INTO budgets (user_id, category, budget_amount, period_type, created_at) VALUES (?, 'Fuel', 6000, 'monthly', ?);", (user_id, now_iso))

    return total_inserted
