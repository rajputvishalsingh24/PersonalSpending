# SpendSense — Personal Spending Behavior Analyzer

> **"Your money has a story. SpendSense helps you see it."**  
> SpendSense is a personal finance intelligence application that transforms raw statement data into meaningful financial insights, recurring expense tracking, budget drift analysis, and realistic, data-grounded saving opportunities.

---

## 🛠 Tech Stack

- **Backend:** Python 3.12, FastAPI, Uvicorn, Pydantic v2
- **Data Engine:** Pandas, NumPy, Python statistical & date utilities
- **Database:** SQLite with WAL mode, foreign keys enabled (`backend/data/spendsense.db`)
- **Frontend:** Vanilla JavaScript, HTML5, Tailwind CSS, Chart.js, Custom 3D perspective transforms & SVG moving doodles
- **API Testing & Verification:** Pytest (18 deterministic test suites) & Postman (`spendsense-api.postman_collection.json`)

---

## 🚀 Quickstart & Installation

### 1. Prerequisites
- Python 3.12+
- Any modern web browser (Chrome, Firefox, Safari, Edge)

### 2. Setup Environment
```powershell
cd spendsense-analyzer
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Launch Application
Start the full-stack server with one command:
```powershell
uvicorn backend.main:app --reload --port 8000
```

- **Web Application:** [`http://localhost:8000`](http://localhost:8000)
- **Interactive OpenAPI Documentation:** [`http://localhost:8000/docs`](http://localhost:8000/docs)
- **Direct Page URLs:**
  - Overview Dashboard: [`http://localhost:8000/dashboard.html`](http://localhost:8000/dashboard.html)
  - Statement Upload Wizard: [`http://localhost:8000/upload.html`](http://localhost:8000/upload.html)
  - Transactions Manager: [`http://localhost:8000/transactions.html`](http://localhost:8000/transactions.html)
  - Budgets & Drift: [`http://localhost:8000/budgets.html`](http://localhost:8000/budgets.html)
  - Recurring Bills: [`http://localhost:8000/recurring.html`](http://localhost:8000/recurring.html)
  - Insights & Savings: [`http://localhost:8000/insights.html`](http://localhost:8000/insights.html)
  - Settings: [`http://localhost:8000/settings.html`](http://localhost:8000/settings.html)

*(Note: Frontend files can also be served independently on any static server like `python -m http.server 3000 --directory frontend` with full CORS support).*

---

## 💾 SQLite Database as Source of Truth

- **Path:** `backend/data/spendsense.db` (auto-created on startup)
- **Initialization:** Completely idempotent. Tables, indexes, and default categories are created automatically on app start without wiping existing transactions.
- **Foreign Keys:** Enforced via `PRAGMA foreign_keys = ON;`
- **Concurrency:** Uses `PRAGMA journal_mode = WAL;`
- **Persistence Verification:** All transactions, category overrides, budgets, recurring confirmations, and insight dismissals persist across backend restarts and browser refreshes.

---

## 🧪 Testing & Verification

### Running Automated Test Suite
SpendSense includes 18 unit, analytical, and full end-to-end acceptance tests:
```powershell
pytest -v
```

Tests verify:
1. Income, expense, net cash flow, and savings rate calculations
2. Transfer exclusions and refund handling
3. Category percentage breakdown
4. Budget pacing, utilization, and drift warnings
5. Recurring payment detection and subscription classification
6. Scenario-based savings calculations
7. Deterministic financial insights generation
8. CSV & Excel upload parsing, column detection, and duplicate rejection
9. Transaction search, filter, pagination, category override, and merchant learning
10. End-to-end 25-step acceptance workflow across simulated restarts

### Postman API Testing
Import [`spendsense-api.postman_collection.json`](file:///c:/Users/HP/OneDrive/Desktop/Group%20B/spendsense-analyzer/spendsense-api.postman_collection.json) into Postman to run requests against all 28 API endpoints.

---

## 📊 Sample Datasets

- **One-Click Demo Data:** Click the **"Load Demo Data"** button in the sidebar or landing page to instantly populate 3 months of realistic transactions (Salary, Rent, Groceries, Dining, Subscriptions, Fuel, Healthcare, Transfers, Refunds, and EMI).
- **Manual CSV Statement Upload:** Test file upload using [`data/sample_transactions.csv`](file:///c:/Users/HP/OneDrive/Desktop/Group%20B/spendsense-analyzer/data/sample_transactions.csv) on [`http://localhost:8000/upload.html`](http://localhost:8000/upload.html).

---

## 🇮🇳 India-First Architecture & Financial Accuracy

- **Currency & Number Formatting:** Complete Indian Rupee (`INR`, `₹`) support with standard Indian number formatting (`en-IN` numbering system: ₹1,50,000 for Lakhs and Crores).
- **Date Conventions & Timezone:** `Asia/Kolkata` timezone with standard Indian date formatting (`DD/MM/YYYY`).
- **Indian Mobile Authentication:** Default country selector set to India (`+91`) with strict 10-digit mobile number validation using Google's `phonenumbers` library (rejecting landlines, invalid area codes, or non-mobile prefixes).
- **Indian Payment Rails Classification:** Native detection and categorization for:
  - **UPI Transfers:** PhonePe, Google Pay, Paytm, BHIM, CRED UPI, `@okhdfcbank`, `@paytm`, `@ybl`, etc.
  - **IMPS / NEFT / RTGS:** Bank-to-bank transfers and salary deposits.
  - **ATM Withdrawals & POS:** Cash withdrawals and in-store card terminal transactions.
  - **NACH / e-Mandates / EMI:** Automated loan installments and utility debits.
  - **BBPS:** Bharat Bill Payment System utility bills (Electricity, Water, Gas, Mobile, Broadband).
- **Double-Counting Prevention:**
  - **Credit Card Bill Payments:** Identifies CC bill settlements (CRED, HDFC CC Autopay, SBI Card Payment) and isolates them as internal transfers (`is_transfer = 1`), preventing double counting alongside individual credit card line items.
  - **Internal Self-Transfers:** Recognizes transfers between own savings and current accounts.
  - **Refund Offsetting:** Accurately offsets expenses with refunds (`is_refund = 1` or category `Refunds`) rather than erroneously inflating expenditure.
- **20 Suggested Indian Financial Categories:**
  1. Groceries
  2. Food Delivery (Swiggy, Zomato)
  3. Restaurants and Cafés
  4. Rent
  5. Electricity and Utilities
  6. Mobile and Internet (Jio, Airtel, Vi)
  7. Transport and Fuel (Indian Oil, HPCL, BPCL, Shell)
  8. Public Transport (Metro, IRCTC, Auto, Bus)
  9. Shopping (Amazon, Flipkart, Myntra)
  10. Healthcare and Medicines (Apollo, 1mg, Practo)
  11. Education
  12. Entertainment (BookMyShow, PVR)
  13. Travel (MakeMyTrip, Goibibo)
  14. Subscriptions (Netflix, Prime, Hotstar, Spotify)
  15. Insurance (LIC, HDFC Life, Star Health)
  16. Loan and EMI Payments
  17. UPI Transfers
  18. ATM Withdrawals
  19. Investments (Zerodha, Groww, AngelOne)
  20. Other

---

## 🔒 Authentication & Disaster Recovery

### Twilio Verify v2 Integration
- Direct integration with official Twilio Verify v2 REST API (`/v2/Services/{VerifyServiceSid}/Verifications` and `/VerificationCheck`).
- **Indian DLT Compliance:** Supports Indian Telecom Regulatory Authority (TRAI) Distributed Ledger Technology (DLT) regulations, Principal Entity IDs, and registered SMS templates.
- **Development Safety:** In development mode (`APP_ENV=development`), codes are cleanly printed to the terminal console with 10-minute expiry. In production (`APP_ENV=production`), real SMS dispatch is enforced and verified with no silent fallbacks.

### Resend Transactional Email
- Supports Resend transactional email API with SPF/DKIM verified domains for email account verification links and secure password resets.

### Database Backups & Recovery
- **Online Atomic Backup:** Uses SQLite's native `conn.backup()` API without locking live readers or writers.
- **Integrity Verification:** Pre- and post-backup checks run `PRAGMA integrity_check;`.
- **Rotation Policy:** Automatically retains the latest 10 backups in `backend/data/backups/`.
- **One-Click Restore:** Safely rolls back state with an automatic pre-restore safety snapshot.
- **Data Portability:** Scoped CSV and full-fidelity JSON exports in user settings.

---

## 🎨 UI/UX & Motion Design

- **Typography & Theme:** Modern `Plus Jakarta Sans` typography on a warm off-white (`#FBFBFD`) surface with midnight navy text, muted emerald accents, and soft lavender highlights.
- **3D Perspective Elevation:** Interactive pointer perspective tilt on KPI metric cards (`perspective(1000px) rotateX(...) rotateY(...)`) with smooth spring return.
- **Moving Doodles:** Custom lightweight SVG line-art illustrations (floating coins, bobbing receipts, pulsing piggy bank, twinkling sparkles) that animate gently without blocking user interactions (`pointer-events: none`).
- **Accessibility:** Full `@media (prefers-reduced-motion: reduce)` compliance automatically disables transforms and continuous rotations for users who prefer reduced motion.
- **Responsive Layout:** Adaptive desktop sidebar that smoothly collapses into a responsive mobile drawer menu.

---

## 🔒 Privacy & Financial Data Integrity

- **100% Local:** Files are processed locally on your machine. No financial transactions are transmitted to external AI providers or cloud analytics.
- **Safe Sign Normalization:** Strictly distinguishes income from expenses, flags transfers between own accounts, and never invents financial figures.
