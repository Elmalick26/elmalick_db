"""Application-wide constants for El Malick Gest.

Import from here instead of repeating literals across modules.
"""

# ---------------------------------------------------------------------------
# RBAC Roles
# ---------------------------------------------------------------------------
ROLE_ADMIN = "Admin"
ROLE_COMPTABLE = "Comptable"
ROLE_SECRETAIRE = "Secretaire"
ROLE_PEDAGOGIQUE = "Pédagogique"
ROLE_PROF = "Prof"
ROLE_PARENT = "parent"

ALL_ROLES = (ROLE_ADMIN, ROLE_COMPTABLE, ROLE_SECRETAIRE, ROLE_PEDAGOGIQUE, ROLE_PROF)
STAFF_ROLES = ALL_ROLES  # same for now; parent is external
FINANCIAL_ROLES = (ROLE_ADMIN, ROLE_COMPTABLE)
ACADEMIC_ROLES = (ROLE_ADMIN, ROLE_PEDAGOGIQUE, ROLE_PROF)

# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------
PAGE_SIZE_DEFAULT = 50
PAGE_SIZE_LARGE = 100
PAGE_SIZE_SMALL = 25

# ---------------------------------------------------------------------------
# UI / Timeouts
# ---------------------------------------------------------------------------
TOAST_DURATION_MS = 3000  # Toast notification display duration
SESSION_TIMEOUT_MINUTES = 30  # Idle session timeout
DB_RETRY_MAX = 3  # Max DB connection retries
DB_RETRY_DELAY_S = 0.5  # Initial retry delay (doubles each attempt)

# ---------------------------------------------------------------------------
# Finance
# ---------------------------------------------------------------------------
CURRENCY_SYMBOL = "FCFA"
LATE_FEE_RATE = 0.02  # 2% monthly late fee
PAYMENT_RECEIPT_PREFIX = "REC"

# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------
ABSENCE_CRITICAL_PERCENT = 25  # Flag student when absence >= this %
LATE_ARRIVAL_MINUTES = 15  # Minutes after bell = late

# ---------------------------------------------------------------------------
# Academic / Grading
# ---------------------------------------------------------------------------
GRADE_MIN = 0.0
GRADE_MAX = 20.0
PASS_AVERAGE = 10.0  # Minimum annual average to pass
GRADE_PRECISION = 2  # Decimal places for averages

# ---------------------------------------------------------------------------
# File / Export
# ---------------------------------------------------------------------------
BACKUP_RETENTION_DAYS = 30
PHOTO_MAX_SIZE_MB = 5
ALLOWED_PHOTO_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
STUDENT_CODE_PREFIX = "EMG"  # e.g. EMG-0042
