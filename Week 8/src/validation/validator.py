"""
OmniMarket Intelligence System (OMIS) - Validation Engine
Granular data quality validation rules for email syntax, date ranges, numeric bounds, and referential integrity.
"""

import re
import pandas as pd
import numpy as np


class DataValidator:
    """Contains modular validation functions for marketplace datasets."""

    EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$")

    @staticmethod
    def validate_emails(series: pd.Series) -> pd.Series:
        """
        Validates email syntax.
        Returns a boolean Series where True indicates a valid email.
        """
        def is_valid(email):
            if pd.isna(email) or not isinstance(email, str):
                return False
            return bool(DataValidator.EMAIL_REGEX.match(email.strip()))

        return series.apply(is_valid)

    @staticmethod
    def validate_dates(series: pd.Series, min_date: str = "2024-01-01", max_date: str = "2026-08-09") -> pd.Series:
        """
        Validates string dates for parseability and range bounds.
        Returns a boolean Series where True indicates a valid date.
        """
        min_dt = pd.to_datetime(min_date)
        max_dt = pd.to_datetime(max_date)

        def is_valid_dt(val):
            if pd.isna(val):
                return False
            try:
                dt = pd.to_datetime(val)
                return min_dt <= dt <= max_dt
            except Exception:
                return False

        return series.apply(is_valid_dt)

    @staticmethod
    def validate_numeric_ranges(series: pd.Series, min_val: float = None, max_val: float = None) -> pd.Series:
        """
        Validates numeric series against inclusive min and max bounds.
        Returns a boolean Series where True indicates a valid value.
        """
        valid = pd.Series(True, index=series.index)
        converted = pd.to_numeric(series, errors="coerce")

        valid &= converted.notna()
        if min_val is not None:
            valid &= converted >= min_val
        if max_val is not None:
            valid &= converted <= max_val

        return valid

    @staticmethod
    def check_duplicate_keys(df: pd.DataFrame, key_column: str) -> pd.Series:
        """
        Checks for duplicate values in a primary key column.
        Returns a boolean Series where True indicates a DUPLICATE key instance.
        """
        if key_column not in df.columns:
            return pd.Series(False, index=df.index)
        return df.duplicated(subset=[key_column], keep="first")

    @staticmethod
    def check_referential_integrity(
        child_df: pd.DataFrame, child_key: str, parent_df: pd.DataFrame, parent_key: str
    ) -> pd.Series:
        """
        Validates foreign key referential integrity.
        Returns a boolean Series where True indicates the foreign key EXISTS in parent_df.
        """
        if child_key not in child_df.columns or parent_key not in parent_df.columns:
            return pd.Series(False, index=child_df.index)

        parent_keys_set = set(parent_df[parent_key].dropna().astype(str).str.strip())
        child_keys_series = child_df[child_key].astype(str).str.strip()

        return child_keys_series.isin(parent_keys_set)

    @staticmethod
    def validate_returns(
        returns_df: pd.DataFrame, orders_df: pd.DataFrame, lines_df: pd.DataFrame
    ) -> pd.Series:
        """
        Comprehensive return record validation:
        1. Order must exist in clean orders.
        2. Product must exist in clean lines for that order.
        3. Return date must be >= order date.
        4. Returned quantity must be <= ordered quantity.
        Returns a boolean Series where True indicates a VALID return.
        """
        valid_series = pd.Series(True, index=returns_df.index)

        # Merge with orders to get order timestamp
        ret_ord = returns_df.merge(
            orders_df[["order_key", "order_timestamp"]],
            on="order_key",
            how="left",
            suffixes=("", "_ord"),
        )

        # 1. Order presence check
        valid_series &= ret_ord["order_timestamp"].notna()

        # 2. Date check (return_date >= order_timestamp)
        def date_check(row):
            if pd.isna(row["return_date"]) or pd.isna(row["order_timestamp"]):
                return False
            try:
                ret_dt = pd.to_datetime(row["return_date"])
                ord_dt = pd.to_datetime(row["order_timestamp"])
                return ret_dt >= ord_dt
            except Exception:
                return False

        valid_series &= ret_ord.apply(date_check, axis=1)

        # 3. Merge with order_lines to verify purchased product and quantity
        ret_lines = returns_df.merge(
            lines_df[["order_key", "product_key", "quantity"]],
            on=["order_key", "product_key"],
            how="left",
        )

        def qty_check(row):
            if pd.isna(row["quantity"]):
                return False
            try:
                ret_q = float(row["return_quantity"])
                ord_q = float(row["quantity"])
                return 0 < ret_q <= ord_q
            except Exception:
                return False

        valid_series &= ret_lines.apply(qty_check, axis=1)

        return valid_series
