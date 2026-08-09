"""
OmniMarket Intelligence System (OMIS) - Automated Edge Case & Pipeline Test Suite
Uses standard Python library unittest to validate data governance, validation rules, cleaning logic, and edge cases.
"""

import unittest
import os
import sqlite3
import pandas as pd
import numpy as np

from src.validation.validator import DataValidator
from src.cleaning.cleaner import DataCleaner
from src.database.db_manager import DatabaseManager


class TestOmniMarketPipeline(unittest.TestCase):
    """Test suite verifying all mandatory 12 edge cases and validation rules."""

    def setUp(self):
        self.validator = DataValidator()
        self.cleaner = DataCleaner()

    # ------------------------------------------------------------
    # 1. Invalid Foreign Key Rejection
    # ------------------------------------------------------------
    def test_01_invalid_foreign_key(self):
        parent_df = pd.DataFrame({"customer_key": ["CUST-000001", "CUST-000002"]})
        child_df = pd.DataFrame({"customer_key": ["CUST-000001", "CUST-999999"]})

        valid_mask = self.validator.check_referential_integrity(
            child_df, "customer_key", parent_df, "customer_key"
        )
        self.assertTrue(valid_mask.iloc[0])
        self.assertFalse(valid_mask.iloc[1])

    # ------------------------------------------------------------
    # 2. Invalid Email Syntax Validation
    # ------------------------------------------------------------
    def test_02_invalid_email(self):
        emails = pd.Series(["valid.user@gmail.com", "missing_at.com", "double@@domain.com", "user@domain..com"])
        valid_mask = self.validator.validate_emails(emails)
        self.assertTrue(valid_mask.iloc[0])
        self.assertFalse(valid_mask.iloc[1])
        self.assertFalse(valid_mask.iloc[2])
        self.assertFalse(valid_mask.iloc[3])

    # ------------------------------------------------------------
    # 3. Invalid Date Range & Parsing Validation
    # ------------------------------------------------------------
    def test_03_invalid_date(self):
        dates = pd.Series(["2025-05-15 10:30:00", "99-99-9999 INVALID", "2029-12-31 23:59:59"])
        valid_mask = self.validator.validate_dates(dates, min_date="2024-01-01", max_date="2026-08-09")
        self.assertTrue(valid_mask.iloc[0])
        self.assertFalse(valid_mask.iloc[1])
        self.assertFalse(valid_mask.iloc[2])

    # ------------------------------------------------------------
    # 4. Duplicate Primary Key Deduplication
    # ------------------------------------------------------------
    def test_04_duplicate_key(self):
        df = pd.DataFrame({"customer_key": ["CUST-001", "CUST-002", "CUST-001"]})
        dup_mask = self.validator.check_duplicate_keys(df, "customer_key")
        self.assertFalse(dup_mask.iloc[0])
        self.assertFalse(dup_mask.iloc[1])
        self.assertTrue(dup_mask.iloc[2])

    # ------------------------------------------------------------
    # 5. Zero Quantity Rejection
    # ------------------------------------------------------------
    def test_05_zero_quantity(self):
        qtys = pd.Series([5, 0, 1])
        valid_mask = self.validator.validate_numeric_ranges(qtys, min_val=1)
        self.assertTrue(valid_mask.iloc[0])
        self.assertFalse(valid_mask.iloc[1])
        self.assertTrue(valid_mask.iloc[2])

    # ------------------------------------------------------------
    # 6. Negative Quantity Rejection
    # ------------------------------------------------------------
    def test_06_negative_quantity(self):
        qtys = pd.Series([2, -3, -1])
        valid_mask = self.validator.validate_numeric_ranges(qtys, min_val=1)
        self.assertTrue(valid_mask.iloc[0])
        self.assertFalse(valid_mask.iloc[1])
        self.assertFalse(valid_mask.iloc[2])

    # ------------------------------------------------------------
    # 7. Discount Above Valid Range Rejection
    # ------------------------------------------------------------
    def test_07_discount_above_valid_range(self):
        discounts = pd.Series([0.10, 0.50, 1.75, -0.15])
        valid_mask = self.validator.validate_numeric_ranges(discounts, min_val=0.0, max_val=0.50)
        self.assertTrue(valid_mask.iloc[0])
        self.assertTrue(valid_mask.iloc[1])
        self.assertFalse(valid_mask.iloc[2])
        self.assertFalse(valid_mask.iloc[3])

    # ------------------------------------------------------------
    # 8. Empty Dataset Pipeline Execution
    # ------------------------------------------------------------
    def test_08_empty_dataset(self):
        empty_df = pd.DataFrame(columns=["customer_key", "customer_name", "email", "signup_date", "customer_segment", "city", "region", "acquisition_channel"])
        clean_df, rej_df = self.cleaner.clean_customers(empty_df)
        self.assertEqual(len(clean_df), 0)
        self.assertEqual(len(rej_df), 0)

    # ------------------------------------------------------------
    # 9. Customer with No Orders
    # ------------------------------------------------------------
    def test_09_customer_with_no_orders(self):
        db = DatabaseManager()
        query = """
        SELECT c.customer_id, COUNT(o.order_id) AS order_count
        FROM dim_customers c
        LEFT JOIN fact_orders o ON c.customer_id = o.customer_id
        GROUP BY c.customer_id
        HAVING order_count = 0
        """
        df = db.execute_query(query)
        self.assertIsInstance(df, pd.DataFrame)

    # ------------------------------------------------------------
    # 10. Product with No Sales
    # ------------------------------------------------------------
    def test_10_product_with_no_sales(self):
        db = DatabaseManager()
        query = """
        SELECT p.product_id, COALESCE(SUM(l.order_qty), 0) AS total_sales
        FROM dim_products p
        LEFT JOIN fact_order_lines l ON p.product_id = l.product_id
        GROUP BY p.product_id
        """
        df = db.execute_query(query)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)

    # ------------------------------------------------------------
    # 11. Return Without Corresponding Purchase
    # ------------------------------------------------------------
    def test_11_return_without_purchase(self):
        returns_df = pd.DataFrame({
            "return_key": ["RET-001"],
            "order_key": ["ORD-999999"],
            "product_key": ["PROD-000001"],
            "return_date": ["2025-05-01 10:00:00"],
            "return_quantity": [1]
        })
        orders_df = pd.DataFrame({"order_key": ["ORD-000001"], "order_timestamp": ["2025-04-01 10:00:00"]})
        lines_df = pd.DataFrame({"order_key": ["ORD-000001"], "product_key": ["PROD-000001"], "quantity": [2]})

        valid_mask = self.validator.validate_returns(returns_df, orders_df, lines_df)
        self.assertFalse(valid_mask.iloc[0])

    # ------------------------------------------------------------
    # 12. Date Range with No Records
    # ------------------------------------------------------------
    def test_12_date_range_with_no_records(self):
        db = DatabaseManager()
        query = """
        SELECT COUNT(*) as cnt FROM fact_orders 
        WHERE order_timestamp >= '2010-01-01' AND order_timestamp <= '2010-12-31'
        """
        df = db.execute_query(query)
        self.assertEqual(df["cnt"].iloc[0], 0)


if __name__ == "__main__":
    unittest.main()
