from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# Base & Health
class HealthResponse(BaseModel):
    status: str
    app: str
    version: str

# Categories
class CategoryCreate(BaseModel):
    category_name: str
    parent_category: Optional[str] = None
    category_type: str = "expense"  # 'expense' or 'income'

class CategoryResponse(BaseModel):
    id: int
    category_name: str
    parent_category: Optional[str] = None
    category_type: str
    is_default: int
    created_at: str

# Transactions
class TransactionCreate(BaseModel):
    transaction_date: str
    description: str
    merchant: Optional[str] = ""
    amount: float
    transaction_type: str = "expense"  # 'income' or 'expense'
    category: str
    subcategory: Optional[str] = ""
    currency: Optional[str] = "INR"
    payment_method: Optional[str] = ""
    is_recurring: Optional[bool] = False
    is_transfer: Optional[bool] = False
    is_refund: Optional[bool] = False
    notes: Optional[str] = ""

class TransactionUpdate(BaseModel):
    description: Optional[str] = None
    merchant: Optional[str] = None
    amount: Optional[float] = None
    transaction_type: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    is_transfer: Optional[bool] = None
    is_refund: Optional[bool] = None
    is_recurring: Optional[bool] = None
    notes: Optional[str] = None

class TransactionResponse(BaseModel):
    id: int
    upload_id: Optional[int] = None
    transaction_date: str
    description: str
    merchant: str
    amount: float
    transaction_type: str
    category: str
    subcategory: str
    currency: str
    payment_method: str
    is_recurring: int
    is_transfer: int
    is_refund: int
    notes: str
    created_at: str

class TransactionListResponse(BaseModel):
    items: List[TransactionResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int

# Budgets
class BudgetCreate(BaseModel):
    category: str
    budget_amount: float = Field(gt=0, description="Budget amount must be positive")
    period_type: str = "monthly"
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class BudgetUpdate(BaseModel):
    budget_amount: Optional[float] = Field(None, gt=0)
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class BudgetResponse(BaseModel):
    id: int
    category: str
    budget_amount: float
    actual_spending: float
    remaining_budget: float
    utilization_pct: float
    status: str  # 'On Track', 'Approaching Limit', 'Over Budget', 'Insufficient Data'
    days_elapsed: int
    days_remaining: int
    projected_spend: Optional[float] = None
    drift_alert: Optional[str] = None
    period_type: str
    created_at: str

# Recurring
class RecurringUpdate(BaseModel):
    status: Optional[str] = None  # 'detected', 'confirmed', 'dismissed'
    is_subscription: Optional[bool] = None
    is_essential: Optional[bool] = None
    review_notes: Optional[str] = None

class RecurringResponse(BaseModel):
    id: int
    merchant: str
    normalized_description: str
    category: str
    average_amount: float
    frequency: str
    last_detected_date: str
    next_expected_date: Optional[str] = None
    confidence_score: float
    status: str
    is_subscription: int
    is_essential: int
    review_notes: str
    annual_estimate: float
    occurrences_count: int
    created_at: str

# Insights
class InsightUpdate(BaseModel):
    status: str  # 'active', 'reviewed', 'dismissed'

class InsightResponse(BaseModel):
    id: int
    insight_type: str
    title: str
    summary: str
    supporting_evidence: Dict[str, Any]
    severity: str
    suggested_action: str
    confidence_level: str
    period: str
    status: str
    created_at: str

# Uploads
class DetectedColumnMapping(BaseModel):
    date_col: Optional[str] = None
    desc_col: Optional[str] = None
    merchant_col: Optional[str] = None
    amount_col: Optional[str] = None
    debit_col: Optional[str] = None
    credit_col: Optional[str] = None
    category_col: Optional[str] = None
    type_col: Optional[str] = None

class ParsedRowPreview(BaseModel):
    row_index: int
    raw_date: str
    parsed_date: Optional[str] = None
    raw_description: str
    merchant: str
    raw_amount: Any
    parsed_amount: Optional[float] = None
    transaction_type: str
    category: str
    confidence: str
    is_duplicate: bool
    validation_error: Optional[str] = None

class UploadPreviewResponse(BaseModel):
    filename: str
    file_type: str
    total_rows: int
    valid_rows_count: int
    duplicate_rows_count: int
    error_rows_count: int
    columns_found: List[str]
    column_mapping: DetectedColumnMapping
    preview_rows: List[ParsedRowPreview]
    temp_file_token: str

class UploadConfirmRequest(BaseModel):
    temp_file_token: str
    column_mapping: DetectedColumnMapping
    skip_duplicates: bool = True
    default_currency: str = "INR"

class UploadResponse(BaseModel):
    id: int
    original_filename: str
    file_type: str
    uploaded_at: str
    transaction_count: int
    duplicate_count: int
    error_count: int
    import_status: str

# Analytics
class SummaryMetrics(BaseModel):
    reporting_period: str
    total_income: float
    total_expenses: float
    net_cash_flow: float
    savings_rate: Optional[float] = None  # None when income <= 0
    savings_rate_label: str
    mom_spending_change_pct: Optional[float] = None
    mom_spending_change_label: str
    active_recurring_expenses: float
    active_recurring_count: int
    currency: str
    transaction_count: int

class CategoryAnalyticsItem(BaseModel):
    category: str
    total_spend: float
    transaction_count: int
    percentage: float
    previous_period_spend: float
    absolute_change: float
    percentage_change: Optional[float] = None
    average_amount: float
    median_amount: float
    largest_transaction: float
    daily_average: float

class TrendPoint(BaseModel):
    period: str  # e.g. "2026-03" or "2026-03-15"
    income: float
    expense: float
    net: float

class BehaviourAnalytics(BaseModel):
    weekday_spend: float
    weekend_spend: float
    weekday_pct: float
    weekend_pct: float
    discretionary_spend: float
    essential_spend: float
    discretionary_pct: float
    essential_pct: float
    top_merchants: List[Dict[str, Any]]
    anomalies: List[Dict[str, Any]]

# Savings Opportunities
class SavingsOpportunity(BaseModel):
    id: str
    opportunity_type: str
    title: str
    category: Optional[str] = None
    merchant: Optional[str] = None
    estimated_potential_monthly_savings: float
    baseline_spending: float
    calculation_method: str
    assumptions: str
    confidence: str
    suggested_action: str
    supporting_transactions_count: int

# Settings
class UserSettingsResponse(BaseModel):
    display_name: str
    default_currency: str
    anomaly_sensitivity: str
    budget_drift_threshold: str
    theme_mode: str
    categories: List[CategoryResponse]

# Backup & Restore
class RestoreBackupRequest(BaseModel):
    backup_filename: str

# Authentication Models
class RegisterEmailRequest(BaseModel):
    full_name: str
    email: str
    password: str
    confirm_password: str
    terms_accepted: bool = True
    role: Optional[str] = "customer"  # 'customer' or 'owner'

class LoginEmailRequest(BaseModel):
    email: str
    password: str
    remember_me: Optional[bool] = False
    role: Optional[str] = None  # optional role hint

class SendOtpRequest(BaseModel):
    country_code: str = "+91"
    phone: str
    purpose: Optional[str] = None  # 'register' or 'login'
    role: Optional[str] = "customer"

class VerifyOtpRequest(BaseModel):
    country_code: str = "+91"
    phone: str
    otp_code: str
    full_name: Optional[str] = None
    purpose: Optional[str] = None  # 'register' or 'login'
    role: Optional[str] = "customer"

class ResendVerificationRequest(BaseModel):
    email: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    email: str
    token: str
    new_password: str
    confirm_password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    default_currency: Optional[str] = None
    role: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    full_name: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    email_verified: int
    phone_verified: int
    account_status: str
    default_currency: str
    role: str = "customer"
    created_at: str

class AuthResponse(BaseModel):
    user: UserResponse
    message: str
    session_token: str

# Database Management Models
class SqlQueryRequest(BaseModel):
    query: str

class SqlQueryResponse(BaseModel):
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    execution_time_ms: float
    error: Optional[str] = None

class TableRowInsertRequest(BaseModel):
    data: Dict[str, Any]

class TableRowUpdateRequest(BaseModel):
    data: Dict[str, Any]

