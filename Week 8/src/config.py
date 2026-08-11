"""
OmniMarket Intelligence System (OMIS) - System Configuration
Centralized configuration management for paths, random seed, and business rule constants.
"""

from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
CLEANED_DATA_DIR = DATA_DIR / "cleaned"
REJECTED_DATA_DIR = DATA_DIR / "rejected"
REPORTS_DIR = DATA_DIR / "reports"
SQL_DIR = BASE_DIR / "sql"
DOCS_DIR = BASE_DIR / "docs"
CHARTS_DIR = DOCS_DIR / "charts"

# Database Path
DB_PATH = DATA_DIR / "omnimarket_analytics.db"

# Reproducible Random Seed
RANDOM_SEED = 42

# Data Generation Targets
NUM_CUSTOMERS = 650
NUM_PRODUCTS = 550
NUM_ORDERS = 1500
NUM_ORDER_LINES = 3200
NUM_RETURNS = 550

# Valid Range Rules
VALID_TIERS = ["Standard", "Preferred", "VIP", "Enterprise"]
VALID_CHANNELS = ["Organic Search", "Direct Referral", "Paid Search", "Social Media", "Affiliate Network"]
VALID_ORDER_STATUSES = ["Delivered", "Shipped", "Processing", "Cancelled", "Returned"]
VALID_PAYMENT_METHODS = ["Credit Card", "PayPal", "Apple Pay", "Buy Now Pay Later", "Direct Bank Transfer"]
VALID_FULFILLMENT_CENTERS = ["FC-East-01", "FC-West-02", "FC-Central-03", "FC-South-04", "FC-North-05"]
VALID_RETURN_REASONS = ["Defective Item", "Wrong Size", "Changed Mind", "Buyer Remorse", "Late Delivery"]

# Price & Discount Rules
MAX_ALLOWABLE_DISCOUNT = 0.50  # 50% max discount
MIN_UNIT_PRICE = 0.01
