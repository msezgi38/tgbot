# =============================================================================
# Configuration for Press-1 IVR Bot
# =============================================================================

import os

# =============================================================================
# Telegram Bot Configuration
# =============================================================================
TELEGRAM_BOT_TOKEN = "8585205125:AAGvYYdfHJRBqamvqJJKPyLU82xiv1TzLNQ"

# =============================================================================
# Oxapay Payment Gateway Configuration
# =============================================================================
OXAPAY_API_KEY = "QSTFGZ-C3IXYJ-XCEWN6-GZZHAS"
OXAPAY_API_URL = "https://api.oxapay.com/merchants/request"
OXAPAY_WEBHOOK_URL = "https://your-domain.com/webhook/oxapay"  # ⚠️ UPDATE THIS

# Payment Configuration
CREDIT_PACKAGES = {
    "10": {"credits": 10, "price": 5.00, "currency": "USDT"},
    "50": {"credits": 50, "price": 20.00, "currency": "USDT"},
    "100": {"credits": 100, "price": 35.00, "currency": "USDT"},
    "500": {"credits": 500, "price": 150.00, "currency": "USDT"},
}

# =============================================================================
# Database Configuration
# =============================================================================
DATABASE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "ivr_bot",
    "user": "postgres",                 # ⚠️ UPDATE WITH YOUR DB USER
    "password": "your_db_password",     # ⚠️ UPDATE WITH YOUR DB PASSWORD
}

DATABASE_URL = f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"

# =============================================================================
# Asterisk AMI Configuration
# =============================================================================
AMI_CONFIG = {
    "host": "127.0.0.1",
    "port": 5038,
    "username": "ivr_bot",
    "secret": "IVRBot@Secure2026!",      # ⚠️ Must match manager.conf
}

# =============================================================================
# Asterisk Trunk Configuration
# =============================================================================
TRUNK_NAME = "magnus_trunk"
DEFAULT_CALLER_ID = "1234567890"         # ⚠️ UPDATE WITH VERIFIED NUMBER
IVR_CONTEXT = "press-one-ivr"

# =============================================================================
# Webhook Server Configuration
# =============================================================================
WEBHOOK_HOST = "0.0.0.0"
WEBHOOK_PORT = 8000
WEBHOOK_URL = "http://localhost:8000"    # Internal webhook for Asterisk

# =============================================================================
# Billing Configuration
# =============================================================================
COST_PER_MINUTE = 1.0                    # 1 credit = 1 minute
MINIMUM_BILLABLE_SECONDS = 6             # Minimum 6 seconds billing
BILLING_INCREMENT_SECONDS = 6            # Bill in 6-second increments

# =============================================================================
# Campaign Configuration
# =============================================================================
MAX_CONCURRENT_CALLS = 10                # Max simultaneous calls
CALL_TIMEOUT_SECONDS = 30                # Total call timeout
DTMF_TIMEOUT_SECONDS = 10                # Wait time for DTMF input
RETRY_FAILED_CALLS = False               # Retry failed calls
DELAY_BETWEEN_CALLS = 2                  # Seconds between each call

# =============================================================================
# Logging Configuration
# =============================================================================
LOG_LEVEL = "INFO"                       # DEBUG, INFO, WARNING, ERROR
LOG_FILE = "bot.log"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# =============================================================================
# Admin Configuration
# =============================================================================
ADMIN_TELEGRAM_IDS = [123456789]         # ⚠️ Add your Telegram ID for admin access

# =============================================================================
# File Paths
# =============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
AUDIO_DIR = os.path.join(BASE_DIR, "audio")

# Create directories if they don't exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)
