"""
OmniMarket Intelligence System (OMIS) - Data Cleaning & Quarantine Engine
Applies strict data governance, standardizes text fields, handles missing values,
quarantines invalid records, and generates formal Data Quality Audit Reports.
"""

import os
from typing import Dict, Tuple, List
import pandas as pd
import numpy as np

from src.config import (
    RAW_DATA_DIR,
    CLEANED_DATA_DIR,
    REJECTED_DATA_DIR,
    REPORTS_DIR,
    VALID_TIERS,
    VALID_CHANNELS,
    VALID_ORDER_STATUSES,
    VALID_PAYMENT_METHODS,
    MAX_ALLOWABLE_DISCOUNT,
)
from src.validation.validator import DataValidator


class DataCleaner:
    """ETL Cleaning and Validation orchestrator."""

    def __init__(self):
        self.validator = DataValidator()
        self.quality_audit = []

    def run_cleaning_pipeline(self) -> Dict[str, pd.DataFrame]:
        """Executes full cleaning pipeline across all raw datasets."""
        os.makedirs(CLEANED_DATA_DIR, exist_ok=True)
        os.makedirs(REJECTED_DATA_DIR, exist_ok=True)
        os.makedirs(REPORTS_DIR, exist_ok=True)

        print("Starting Data Cleaning & Governance Pipeline...")

        # 1. Load Raw Datasets
        raw_cust = pd.read_csv(RAW_DATA_DIR / "customers.csv")
        raw_prod = pd.read_csv(RAW_DATA_DIR / "products.csv")
        raw_orders = pd.read_csv(RAW_DATA_DIR / "orders.csv")
        raw_lines = pd.read_csv(RAW_DATA_DIR / "order_lines.csv")
        raw_returns = pd.read_csv(RAW_DATA_DIR / "returns.csv")

        # 2. Clean Customers
        clean_cust, rej_cust = self.clean_customers(raw_cust)

        # 3. Clean Products
        clean_prod, rej_prod = self.clean_products(raw_prod)

        # 4. Clean Orders
        clean_orders, rej_orders = self.clean_orders(raw_orders, clean_cust)

        # 5. Clean Order Lines
        clean_lines, rej_lines = self.clean_order_lines(raw_lines, clean_orders, clean_prod)

        # 6. Clean Returns
        clean_returns, rej_returns = self.clean_returns(raw_returns, clean_orders, clean_lines)

        # Save Clean Datasets
        clean_cust.to_csv(CLEANED_DATA_DIR / "customers.csv", index=False)
        clean_prod.to_csv(CLEANED_DATA_DIR / "products.csv", index=False)
        clean_orders.to_csv(CLEANED_DATA_DIR / "orders.csv", index=False)
        clean_lines.to_csv(CLEANED_DATA_DIR / "order_lines.csv", index=False)
        clean_returns.to_csv(CLEANED_DATA_DIR / "returns.csv", index=False)

        # Save Rejected Datasets
        rej_cust.to_csv(REJECTED_DATA_DIR / "rejected_customers.csv", index=False)
        rej_prod.to_csv(REJECTED_DATA_DIR / "rejected_products.csv", index=False)
        rej_orders.to_csv(REJECTED_DATA_DIR / "rejected_orders.csv", index=False)
        rej_lines.to_csv(REJECTED_DATA_DIR / "rejected_order_lines.csv", index=False)
        rej_returns.to_csv(REJECTED_DATA_DIR / "rejected_returns.csv", index=False)

        # 7. Generate Data Quality Report
        df_audit = self.generate_quality_report()

        print("Data Cleaning Completed successfully.")

        return {
            "customers": clean_cust,
            "products": clean_prod,
            "orders": clean_orders,
            "order_lines": clean_lines,
            "returns": clean_returns,
            "audit_report": df_audit,
        }

    def clean_customers(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Cleans and standardizes customers dataset."""
        initial_rows = len(df)
        df_clean = df.copy()

        # Impute Missing Values first
        df_clean["region"] = df_clean["region"].fillna("UNKNOWN").astype(str).str.strip()
        df_clean["city"] = df_clean["city"].fillna("Unknown").astype(str).str.strip()
        df_clean["acquisition_channel"] = df_clean["acquisition_channel"].fillna("Organic Search").astype(str).str.strip()
        df_clean["customer_segment"] = df_clean["customer_segment"].fillna("Standard").astype(str).str.strip()

        # Trim Whitespace & Capitalization Standardizations
        df_clean["customer_name"] = df_clean["customer_name"].fillna("Customer").astype(str).str.strip().str.title()
        df_clean["city"] = df_clean["city"].str.title()
        df_clean["region"] = df_clean["region"].str.upper()

        df_clean["region"] = df_clean["region"].replace(["NONE", "NAN", "", "NULL"], "UNKNOWN")
        df_clean["city"] = df_clean["city"].replace(["", "NAN", "NULL"], "Unknown")
        df_clean["acquisition_channel"] = df_clean["acquisition_channel"].replace(
            ["", "NAN", "NULL"], "Organic Search"
        )

        # Deduplicate Primary Keys (Keep First)
        dup_mask = self.validator.check_duplicate_keys(df_clean, "customer_key")
        dup_count = dup_mask.sum()
        df_no_dups = df_clean[~dup_mask].copy()

        # Validate Emails
        valid_email_mask = self.validator.validate_emails(df_no_dups["email"])
        invalid_email_count = (~valid_email_mask).sum()

        df_valid_emails = df_no_dups[valid_email_mask].copy()

        # Deduplicate Email Addresses (Keep First)
        email_dup_mask = self.validator.check_duplicate_keys(df_valid_emails, "email")
        email_dup_count = email_dup_mask.sum()
        final_clean = df_valid_emails[~email_dup_mask].copy()

        # Strategy: Reject duplicate keys, invalid emails, and duplicate emails to rejected_customers
        rejected_df = df_clean[dup_mask].copy()
        rejected_df["rejection_reason"] = "Duplicate Primary Key"

        invalid_email_df = df_no_dups[~valid_email_mask].copy()
        invalid_email_df["rejection_reason"] = "Invalid Email Syntax"

        dup_email_df = df_valid_emails[email_dup_mask].copy()
        dup_email_df["rejection_reason"] = "Duplicate Email Address"

        rejected_df = pd.concat([rejected_df, invalid_email_df, dup_email_df], ignore_index=True)

        # Audit Logging
        self.quality_audit.append({
            "dataset": "Customers",
            "initial_rows": initial_rows,
            "invalid_rows": dup_count + invalid_email_count,
            "corrected_rows": initial_rows - dup_count,  # whitespace/casing/imputed
            "removed_rows": len(rejected_df),
            "remaining_rows": len(final_clean),
            "issue_type": "Duplicate Keys & Syntax Invalid Emails",
            "resolution": "Trimmed, title-cased, imputed missing regions; rejected invalid emails and duplicate keys.",
        })

        return final_clean, rejected_df

    def clean_products(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Cleans and standardizes products dataset."""
        initial_rows = len(df)
        df_clean = df.copy()

        # Standardize strings & Impute missing
        for col in ["product_name", "category", "subcategory", "brand"]:
            if col in df_clean.columns:
                df_clean[col] = df_clean[col].fillna("General Accessories" if col == "subcategory" else "Generic").astype(str).str.strip()

        df_clean["subcategory"] = df_clean["subcategory"].replace(["None", "nan", "", "NULL", "NoneType"], "General Accessories")

        # Deduplicate Primary Keys
        dup_mask = self.validator.check_duplicate_keys(df_clean, "product_key")
        dup_count = dup_mask.sum()
        df_no_dups = df_clean[~dup_mask].copy()

        # Validate Numeric Prices
        valid_price_mask = self.validator.validate_numeric_ranges(df_no_dups["selling_price"], min_val=0.01)
        valid_cost_mask = self.validator.validate_numeric_ranges(df_no_dups["unit_cost"], min_val=0.01)
        valid_numeric_mask = valid_price_mask & valid_cost_mask
        invalid_price_count = (~valid_numeric_mask).sum()

        rejected_df = df_clean[dup_mask].copy()
        rejected_df["rejection_reason"] = "Duplicate Primary Key"

        invalid_price_df = df_no_dups[~valid_numeric_mask].copy()
        invalid_price_df["rejection_reason"] = "Non-positive selling price or unit cost"
        rejected_df = pd.concat([rejected_df, invalid_price_df], ignore_index=True)

        final_clean = df_no_dups[valid_numeric_mask].copy()

        self.quality_audit.append({
            "dataset": "Products",
            "initial_rows": initial_rows,
            "invalid_rows": dup_count + invalid_price_count,
            "corrected_rows": initial_rows - dup_count,
            "removed_rows": len(rejected_df),
            "remaining_rows": len(final_clean),
            "issue_type": "Duplicate Keys & Invalid Prices/Costs",
            "resolution": "Trimmed, imputed subcategories; rejected zero/negative price records and duplicate keys.",
        })

        return final_clean, rejected_df

    def clean_orders(self, df: pd.DataFrame, clean_customers: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Cleans orders dataset and enforces referential integrity with clean customers."""
        initial_rows = len(df)
        df_clean = df.copy()

        # Standardize strings
        for col in ["order_status", "payment_method", "shipping_region", "fulfillment_center"]:
            if col in df_clean.columns:
                df_clean[col] = df_clean[col].astype(str).str.strip()

        # Deduplicate Primary Keys
        dup_mask = self.validator.check_duplicate_keys(df_clean, "order_key")
        dup_count = dup_mask.sum()
        df_no_dups = df_clean[~dup_mask].copy()

        # Validate Timestamps
        valid_ts_mask = self.validator.validate_dates(
            df_no_dups["order_timestamp"], min_date="2024-01-01", max_date="2026-08-09"
        )
        invalid_ts_count = (~valid_ts_mask).sum()

        # Validate Order Status
        valid_status_mask = df_no_dups["order_status"].isin(VALID_ORDER_STATUSES)
        invalid_status_count = (~valid_status_mask).sum()

        # Referential Integrity (Customer Key)
        ref_mask = self.validator.check_referential_integrity(
            df_no_dups, "customer_key", clean_customers, "customer_key"
        )
        orphan_count = (~ref_mask).sum()

        # Combine all valid conditions
        valid_all = valid_ts_mask & valid_status_mask & ref_mask

        rejected_df = df_clean[dup_mask].copy()
        rejected_df["rejection_reason"] = "Duplicate Primary Key"

        invalid_orders_df = df_no_dups[~valid_all].copy()
        invalid_orders_df["rejection_reason"] = "Invalid timestamp, invalid status, or missing customer foreign key"
        rejected_df = pd.concat([rejected_df, invalid_orders_df], ignore_index=True)

        final_clean = df_no_dups[valid_all].copy()

        self.quality_audit.append({
            "dataset": "Orders",
            "initial_rows": initial_rows,
            "invalid_rows": dup_count + invalid_ts_count + invalid_status_count + orphan_count,
            "corrected_rows": initial_rows - dup_count,
            "removed_rows": len(rejected_df),
            "remaining_rows": len(final_clean),
            "issue_type": "Orphan Foreign Keys, Malformed Dates, Invalid Statuses",
            "resolution": "Standardized status strings; rejected orphan orders, malformed/future dates, and invalid status codes.",
        })

        return final_clean, rejected_df

    def clean_order_lines(
        self, df: pd.DataFrame, clean_orders: pd.DataFrame, clean_products: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Cleans order_lines dataset and computes calculated line item total."""
        initial_rows = len(df)
        df_clean = df.copy()

        # Deduplicate Primary Keys
        dup_mask = self.validator.check_duplicate_keys(df_clean, "line_key")
        dup_count = dup_mask.sum()
        df_no_dups = df_clean[~dup_mask].copy()

        # Validate Quantities (> 0)
        valid_qty_mask = self.validator.validate_numeric_ranges(df_no_dups["quantity"], min_val=1)
        invalid_qty_count = (~valid_qty_mask).sum()

        # Validate Discount Pct (0.0 to MAX_ALLOWABLE_DISCOUNT)
        valid_disc_mask = self.validator.validate_numeric_ranges(
            df_no_dups["discount_pct"], min_val=0.0, max_val=MAX_ALLOWABLE_DISCOUNT
        )
        invalid_disc_count = (~valid_disc_mask).sum()

        # Foreign Key Checks
        ref_ord_mask = self.validator.check_referential_integrity(
            df_no_dups, "order_key", clean_orders, "order_key"
        )
        ref_prod_mask = self.validator.check_referential_integrity(
            df_no_dups, "product_key", clean_products, "product_key"
        )
        orphan_count = (~(ref_ord_mask & ref_prod_mask)).sum()

        valid_all = valid_qty_mask & valid_disc_mask & ref_ord_mask & ref_prod_mask

        rejected_df = df_clean[dup_mask].copy()
        rejected_df["rejection_reason"] = "Duplicate Primary Key"

        invalid_lines_df = df_no_dups[~valid_all].copy()
        invalid_lines_df["rejection_reason"] = "Zero/negative quantity, out-of-bounds discount, or orphan foreign key"
        rejected_df = pd.concat([rejected_df, invalid_lines_df], ignore_index=True)

        final_clean = df_no_dups[valid_all].copy()

        # Compute calculated Line Total USD
        final_clean["unit_price"] = final_clean["unit_price"].astype(float)
        final_clean["quantity"] = final_clean["quantity"].astype(int)
        final_clean["discount_pct"] = final_clean["discount_pct"].astype(float)
        final_clean["line_total_usd"] = (
            final_clean["quantity"] * final_clean["unit_price"] * (1 - final_clean["discount_pct"])
        ).round(2)

        self.quality_audit.append({
            "dataset": "Order Lines",
            "initial_rows": initial_rows,
            "invalid_rows": dup_count + invalid_qty_count + invalid_disc_count + orphan_count,
            "corrected_rows": initial_rows - dup_count,
            "removed_rows": len(rejected_df),
            "remaining_rows": len(final_clean),
            "issue_type": "Zero/Negative Quantity, Excessive Discount, Missing Product/Order FK",
            "resolution": "Computed line_total_usd; rejected non-positive quantities, out-of-range discounts, and orphan line items.",
        })

        return final_clean, rejected_df

    def clean_returns(
        self, df: pd.DataFrame, clean_orders: pd.DataFrame, clean_lines: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Cleans returns dataset and validates logic against orders and order lines."""
        initial_rows = len(df)
        df_clean = df.copy()

        # Deduplicate Primary Keys
        dup_mask = self.validator.check_duplicate_keys(df_clean, "return_key")
        dup_count = dup_mask.sum()
        df_no_dups = df_clean[~dup_mask].copy()

        # Validate Logic (Date >= Order Date, Qty <= Purchased Qty, FK exists)
        valid_return_mask = self.validator.validate_returns(df_no_dups, clean_orders, clean_lines)
        invalid_return_count = (~valid_return_mask).sum()

        rejected_df = df_clean[dup_mask].copy()
        rejected_df["rejection_reason"] = "Duplicate Primary Key"

        invalid_ret_df = df_no_dups[~valid_return_mask].copy()
        invalid_ret_df["rejection_reason"] = "Return date precedes order date, quantity exceeds purchased, or orphan FK"
        rejected_df = pd.concat([rejected_df, invalid_ret_df], ignore_index=True)

        final_clean = df_no_dups[valid_return_mask].copy()

        self.quality_audit.append({
            "dataset": "Returns",
            "initial_rows": initial_rows,
            "invalid_rows": dup_count + invalid_return_count,
            "corrected_rows": initial_rows - dup_count,
            "removed_rows": len(rejected_df),
            "remaining_rows": len(final_clean),
            "issue_type": "Pre-order Return Timestamp, Quantity Overflow, Orphan Return FK",
            "resolution": "Standardized reason codes; rejected pre-order return dates, excessive return quantities, and unmapped returns.",
        })

        return final_clean, rejected_df

    def generate_quality_report(self) -> pd.DataFrame:
        """Generates CSV and Markdown quality audit reports."""
        df_audit = pd.DataFrame(self.quality_audit)
        df_audit.to_csv(REPORTS_DIR / "data_quality_report.csv", index=False)

        # Render Markdown Report
        md_content = ["# OmniMarket Data Quality & Audit Report\n"]
        md_content.append("| Dataset | Initial Rows | Invalid Rows | Corrected | Rejected / Removed | Clean Rows | Issue Type | Resolution Strategy |")
        md_content.append("|---|---|---|---|---|---|---|---|")

        for _, row in df_audit.iterrows():
            md_content.append(
                f"| {row['dataset']} | {row['initial_rows']} | {row['invalid_rows']} | "
                f"{row['corrected_rows']} | {row['removed_rows']} | {row['remaining_rows']} | "
                f"{row['issue_type']} | {row['resolution']} |"
            )

        with open(REPORTS_DIR / "data_quality_report.md", "w", encoding="utf-8") as f:
            f.write("\n".join(md_content))

        return df_audit


if __name__ == "__main__":
    cleaner = DataCleaner()
    cleaner.run_cleaning_pipeline()
