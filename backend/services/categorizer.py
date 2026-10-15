import re
from typing import Tuple, Dict, Any, List, Optional
import sqlite3
from backend.database import get_db

# 20 Suggested India-First Default Spending Categories
INDIA_EXPENSE_CATEGORIES = [
    "Groceries",
    "Food Delivery",
    "Restaurants and Cafés",
    "Rent",
    "Electricity and Utilities",
    "Mobile and Internet",
    "Transport and Fuel",
    "Public Transport",
    "Shopping",
    "Healthcare and Medicines",
    "Education",
    "Entertainment",
    "Travel",
    "Subscriptions",
    "Insurance",
    "Loan and EMI Payments",
    "UPI Transfers",
    "ATM Withdrawals",
    "Investments",
    "Other"
]

INDIA_INCOME_CATEGORIES = [
    "Salary",
    "Freelance Income",
    "Business Income",
    "Interest",
    "Investment Income",
    "Refunds",
    "Other Income"
]

# Comprehensive keyword patterns for Indian financial ecosystem
CATEGORY_RULES: Dict[str, List[str]] = {
    # 1. Groceries
    "Groceries": [
        r"zepto", r"blinkit", r"bigbasket", r"dmart", r"nature's basket", r"spencer",
        r"reliance smart", r"reliance fresh", r"jiomart", r"more retail", r"more supermarket",
        r"kirana", r"provision", r"vegetables", r"fruits", r"milk", r"dairy", r"amul",
        r"mother dairy", r"meat", r"licious", r"freshtohome", r"grocery", r"supermarket"
    ],

    # 2. Food Delivery
    "Food Delivery": [
        r"swiggy", r"zomato", r"eatclub", r"magicpin", r"dunzo", r"box8", r"faasos", r"behrouz",
        r"ovenstory", r"freshmenu", r"food delivery", r"swiggy instamart food"
    ],

    # 3. Restaurants and Cafés
    "Restaurants and Cafés": [
        r"starbucks", r"mcdonald", r"domino", r"pizza hut", r"burger king", r"kfc", r"subway",
        r"cafe coffee day", r"ccd", r"chai point", r"chaayos", r"barbeque nation", r"haldiram",
        r"sagar ratna", r"bikanervala", r"bistro", r"cafe", r"coffee", r"bakery", r"brewery",
        r"dining", r"restaurant", r"dhabha", r"bhojanalaya", r"hotel dining", r"eatery", r"bar"
    ],

    # 4. Rent
    "Rent": [
        r"rent", r"landlord", r"house rent", r"apartment rent", r"society maintenance",
        r"maintenance society", r"mygate", r"nobroker", r"nestaway", r"housing society dues"
    ],

    # 5. Electricity and Utilities
    "Electricity and Utilities": [
        r"electricity", r"bescom", r"tneb", r"tata power", r"adani electricity", r"msedcl",
        r"torrent power", r"cesc", r"bses", r"water bill", r"jal board", r"piped gas", r"igl",
        r"mahanagar gas", r"indane", r"bharat gas", r"hp gas", r"utility", r"bbps", r"billpay"
    ],

    # 6. Mobile and Internet
    "Mobile and Internet": [
        r"airtel", r"jio", r"vodafone", r"\bvi\b", r"bsnl", r"act fibernet", r"hathway",
        r"you broadband", r"tata play", r"dishtv", r"mobile recharge", r"broadband", r"wifi", r"postpaid"
    ],

    # 7. Transport and Fuel
    "Transport and Fuel": [
        r"petrol", r"diesel", r"cng", r"hpcl", r"bpcl", r"iocl", r"shell", r"gas station",
        r"fuel", r"fastag", r"nhai", r"toll plaza", r"toll", r"park\+", r"parking",
        r"uber", r"ola", r"rapido", r"auto", r"cab", r"taxi"
    ],

    # 8. Public Transport
    "Public Transport": [
        r"irctc", r"indian railways", r"metro", r"delhi metro", r"dmrc", r"bengaluru metro",
        r"namma metro", r"mumbai metro", r"uts", r"bmtc", r"dtc", r"msrtc", r"state transport",
        r"bus ticket", r"train ticket", r"local train"
    ],

    # 9. Shopping
    "Shopping": [
        r"amazon", r"flipkart", r"myntra", r"ajio", r"nykaa", r"tata cliq", r"meesho",
        r"zara", r"h&m", r"uniqlo", r"shoppers stop", r"lifestyle", r"westside", r"max fashion",
        r"decathlon", r"croma", r"reliance digital", r"vijay sales", r"ikea", r"pepperfry",
        r"apparel", r"clothing", r"footwear", r"retail", r"mall"
    ],

    # 10. Healthcare and Medicines
    "Healthcare and Medicines": [
        r"apollo", r"medplus", r"1mg", r"pharmeasy", r"netmeds", r"tata 1mg", r"hospital",
        r"clinic", r"doctor", r"diagnostic", r"pathology", r"dr lal pathlabs", r"srl diagnostics",
        r"metropolis", r"dental", r"dentist", r"medicine", r"pharmacy", r"chemist"
    ],

    # 11. Education
    "Education": [
        r"school", r"college", r"university", r"tuition", r"coaching", r"allen", r"aakash",
        r"fiitjee", r"unacademy", r"byju", r"coursera", r"udemy", r"upgrad", r"books",
        r"stationery", r"exam fee", r"course"
    ],

    # 12. Entertainment
    "Entertainment": [
        r"pvr", r"inox", r"cinepolis", r"bookmyshow", r"movie", r"cinema", r"theatre",
        r"gaming", r"steam", r"playstation", r"concert", r"event ticket", r"amusement park",
        r"wonderla", r"imagica"
    ],

    # 13. Travel
    "Travel": [
        r"makemytrip", r"goibibo", r"easemytrip", r"cleartrip", r"yatra", r"indigo",
        r"air india", r"vistara", r"akasa", r"spicejet", r"hotel", r"airbnb", r"oyo",
        r"booking\.com", r"resort", r"flight", r"baggage"
    ],

    # 14. Subscriptions
    "Subscriptions": [
        r"netflix", r"spotify", r"prime video", r"hotstar", r"disney", r"sonyliv", r"zee5",
        r"apple services", r"apple music", r"icloud", r"google one", r"youtube premium",
        r"chatgpt", r"openai", r"github", r"medium", r"audible", r"canva", r"subscription"
    ],

    # 15. Insurance
    "Insurance": [
        r"lic", r"hdfc life", r"icici pru", r"sbi life", r"max life", r"policybazaar",
        r"star health", r"care health", r"niva bupa", r"tata aig", r"bajaj allianz",
        r"motor insurance", r"car insurance", r"bike insurance", r"term life", r"health insurance",
        r"insurance premium"
    ],

    # 16. Loan and EMI Payments
    "Loan and EMI Payments": [
        r"\bemi\b", r"loan emi", r"home loan", r"car loan", r"personal loan", r"bajaj finance",
        r"bajaj finserv", r"hdfc ltd", r"sbi home", r"tata capital", r"navi", r"kreditbee",
        r"moneytap", r"nach emi", r"ecs loan", r"mortgage"
    ],

    # 17. UPI Transfers
    "UPI Transfers": [
        r"upi/p2p", r"transfer to", r"sent to upi", r"upi payment to", r"vpa transfer"
    ],

    # 18. ATM Withdrawals
    "ATM Withdrawals": [
        r"atm\s+wdl", r"atm\s+cash", r"nfs\s+atm", r"cash\s+withdrawal", r"atm-cash", r"atm-wdl"
    ],

    # 19. Investments
    "Investments": [
        r"zerodha", r"groww", r"upstox", r"angel one", r"kuvera", r"cams", r"kfintech",
        r"mutual fund", r"mf sip", r"ppf", r"nps", r"epfo", r"sgb", r"sovereign gold",
        r"nse", r"bse", r"shares", r"equities", r"fixed deposit", r"term deposit"
    ],

    # Income
    "Salary": [
        r"salary", r"payroll", r"direct deposit", r"wages", r"monthly stipend"
    ],
    "Freelance Income": [
        r"freelance", r"upwork", r"fiverr", r"client payment", r"consulting fee", r"contract payment"
    ],
    "Business Income": [
        r"business receipt", r"merchant settlement", r"pos settlement", r"razorpay settlement", r"stripe payout"
    ],
    "Interest": [
        r"interest credit", r"bank interest", r"savings interest", r"fd interest", r"int\.coll"
    ],
    "Investment Income": [
        r"dividend", r"mutual fund redemption", r"capital gain", r"shares payout"
    ],
    "Refunds": [
        r"refund", r"reversal", r"cashback", r"chargeback", r"returned txn"
    ]
}

# Patterns indicating internal transfers / self payments that must NOT be counted as consumption
TRANSFER_KEYWORDS = [
    r"transfer to self", r"self transfer", r"own account", r"internal transfer",
    r"to savings a/c", r"from savings a/c", r"to current a/c", r"sweep in", r"sweep out",
    r"sweep trf", r"savings to fd", r"fd to savings", r"linked account", r"to own a/c",
    r"from own a/c", r"trf to own", r"self trf"
]

# Patterns indicating credit card bill payments that must NOT double-count with card statement expenses
CREDIT_CARD_PAYMENT_KEYWORDS = [
    r"cred", r"autopay cc", r"cc bill", r"credit card payment", r"credit card bill",
    r"hdfc cc pymt", r"sbi card pymt", r"sbi card payment", r"card payment", r"icici cc pymt", r"axis card pymt", r"axis cc bill",
    r"payment received - thank you", r"card payment received", r"bbps cc bill", r"cc payment",
    r"card bill pymt", r"billdesk cc"
]

def is_transfer_description(text: str) -> bool:
    """Detect if transaction description indicates a self transfer or credit card bill payment."""
    lower = text.lower()
    return any(re.search(pat, lower) for pat in TRANSFER_KEYWORDS) or any(re.search(pat, lower) for pat in CREDIT_CARD_PAYMENT_KEYWORDS)

def is_credit_card_payment(text: str) -> bool:
    """Detect if transaction represents a credit card bill payment."""
    lower = text.lower()
    return any(re.search(pat, lower) for pat in CREDIT_CARD_PAYMENT_KEYWORDS)

def is_refund_description(text: str) -> bool:
    """Detect if transaction description indicates a refund or reversal."""
    lower = text.lower()
    return bool(re.search(r"refund|reversal|returned|cashback|chargeback", lower))

def detect_payment_method(text: str) -> str:
    """Identify payment rail / instrument from Indian banking description."""
    upper = text.upper()
    if "UPI" in upper or "@" in text or "VPA" in upper or "GPAY" in upper or "PHONEPE" in upper or "PAYTM" in upper:
        return "UPI"
    if "IMPS" in upper:
        return "IMPS"
    if "NEFT" in upper:
        return "NEFT"
    if "RTGS" in upper:
        return "RTGS"
    if "ATM" in upper or "NFS" in upper or "CASH WDL" in upper:
        return "ATM"
    if "POS" in upper or "EDC" in upper:
        return "Card / POS"
    if "NACH" in upper or "ECS" in upper or "ACH" in upper or "EMI" in upper:
        return "NACH / EMI"
    if "BBPS" in upper:
        return "BBPS"
    if "NETBANK" in upper or "INB" in upper or "NET BANKING" in upper:
        return "Net Banking"
    return "Bank Transfer"

def extract_merchant(text: str) -> str:
    """Clean and extract a clean recognizable merchant name from raw Indian banking narration."""
    # Remove common Indian banking prefixes
    cleaned = re.sub(
        r"^(pos|upi|neft|rtgs|imps|ach|cms|e-mandate|nach|vpa|txn|nfs|bbps)[\s\:\/\-\*]+",
        "", text, flags=re.IGNORECASE
    )
    cleaned = re.sub(
        r"[\s\:\/\-\*]+(pos|upi|neft|rtgs|imps|ach|bbps)[\s\:\/\-\*]+",
        " ", cleaned, flags=re.IGNORECASE
    )
    # Remove alphanumeric reference numbers like 1234567890 or transaction IDs
    cleaned = re.sub(r"\b[0-9]{6,}\b", "", cleaned)
    # Remove UPI handles like @okhdfcbank, @okaxis, @paytm, @ybl
    cleaned = re.sub(r"@[a-zA-Z0-9_\.]+", "", cleaned)
    # Remove trailing/leading punctuation
    cleaned = re.sub(r"[^a-zA-Z0-9\s\.\&\-]", " ", cleaned)
    cleaned = " ".join(cleaned.split()).strip()
    return cleaned.title()[:50] if cleaned else text[:50]

def categorize_transaction(
    description: str,
    merchant: str = "",
    amount: float = 0.0,
    user_id: int = 1
) -> Tuple[str, str, str]:
    """
    Categorize transaction using learned SQLite mappings, India-first keyword rules, and transaction sign.
    Returns: (category, subcategory, confidence_level)
    """
    desc_clean = description.strip()
    merchant_clean = (merchant or extract_merchant(description)).strip()
    search_text = f"{desc_clean} {merchant_clean}".lower()

    # 1. Check user-learned category mappings in database
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT category_name, confidence FROM category_mappings WHERE ? LIKE '%' || merchant_pattern || '%' AND user_id = ? LIMIT 1;",
                (search_text, user_id)
            )
            row = cursor.fetchone()
            if row:
                return (row["category_name"], "", "High")
    except Exception:
        pass

    # 2. Check for credit card payment or self transfers (prevent double counting)
    if is_credit_card_payment(search_text):
        return ("Loan and EMI Payments", "Credit Card Payment", "High")

    if is_transfer_description(search_text):
        return ("Other", "Self Transfer", "High")

    # 3. Check for explicit refunds or reversals
    if is_refund_description(search_text) or (amount > 0 and "refund" in search_text):
        return ("Refunds", "Reversal", "High")

    # 4. Check ATM Cash withdrawals
    if re.search(r"atm\s+wdl|atm\s+cash|nfs\s+atm|cash\s+withdrawal", search_text):
        return ("ATM Withdrawals", "Cash", "High")

    # 5. Match against known India-first regex patterns
    for category, patterns in CATEGORY_RULES.items():
        for pat in patterns:
            if re.search(r"\b" + pat + r"\b", search_text):
                return (category, "", "High")

    # 6. Fallback based on amount sign
    if amount > 0:
        return ("Other Income", "", "Needs review")
    return ("Other", "", "Needs review")

def learn_merchant_mapping(merchant_or_desc: str, category_name: str, user_id: int = 1) -> None:
    """Save a user-corrected merchant to category mapping so future transactions use it."""
    cleaned = extract_merchant(merchant_or_desc).lower().strip()
    if not cleaned or len(cleaned) < 3:
        cleaned = merchant_or_desc.lower()[:30].strip()

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM category_mappings WHERE user_id = ? AND merchant_pattern = ?;", (user_id, cleaned))
            row = cursor.fetchone()
            if row:
                cursor.execute("UPDATE category_mappings SET category_name = ?, confidence = 1.0 WHERE id = ?;", (category_name, row["id"]))
            else:
                cursor.execute("""
                    INSERT INTO category_mappings (user_id, merchant_pattern, category_name, confidence, created_at)
                    VALUES (?, ?, ?, 1.0, datetime('now'));
                """, (user_id, cleaned, category_name))
    except Exception:
        pass
