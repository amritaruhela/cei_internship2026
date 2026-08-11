"""
Silver Layer Transformer

Performs cleaning, standardization, deduplication, and quarantine.
Reads from Bronze layer, writes to Silver layer.

Key operations:
- Type normalization
- Date normalization  
- Null handling per configured rules
- Duplicate detection and flagging
- Business key validation
- Invalid record quarantine (NOT deletion)
- Schema normalization
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class QuarantineRecord:
    """Represents a quarantined record with audit metadata."""
    def __init__(
        self,
        run_id: str,
        source_system: str,
        record_id: str,
        reason: str,
        rule_id: str,
        raw_record: dict,
    ):
        self.run_id = run_id
        self.source_system = source_system
        self.record_id = record_id
        self.reason = reason
        self.rule_id = rule_id
        self.detected_at = datetime.now(timezone.utc).isoformat()
        self.raw_record = raw_record

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "source_system": self.source_system,
            "record_id": self.record_id,
            "reason": self.reason,
            "rule_id": self.rule_id,
            "detected_at": self.detected_at,
            "raw_record": json.dumps(self.raw_record, default=str),
        }


class SilverTransformer:
    """
    Transforms Bronze layer data into Silver layer cleaned data.
    Invalid records are quarantined, not deleted.
    """

    EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
    VALID_BILLING_STATUSES = {"completed", "pending", "failed", "refunded"}
    VALID_CRM_STATUSES = {"ACTIVE", "INACTIVE", "CHURNED", "SUSPENDED"}

    def __init__(self, silver_dir: Path, run_id: Optional[str] = None):
        self.silver_dir = Path(silver_dir)
        self.silver_dir.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id or str(uuid.uuid4())
        self.quarantine_records: list[dict] = []

    def _quarantine(
        self,
        source_system: str,
        record_id: str,
        reason: str,
        rule_id: str,
        raw_record: dict,
    ) -> None:
        q = QuarantineRecord(
            run_id=self.run_id,
            source_system=source_system,
            record_id=record_id,
            reason=reason,
            rule_id=rule_id,
            raw_record=raw_record,
        )
        self.quarantine_records.append(q.to_dict())

    def transform_billing(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and standardize billing data.
        Business rule: only 'completed' status = recognized revenue.
        """
        logger.info(f"Silver transform: billing ({len(df)} rows)")
        df = df.copy()

        # Remove bronze metadata columns for processing (keep reference cols)
        bronze_cols = [c for c in df.columns if c.startswith("_")]
        
        # 1. Type normalization
        if "amount" in df.columns:
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        
        if "transaction_date" in df.columns:
            df["transaction_date"] = pd.to_datetime(
                df["transaction_date"], errors="coerce"
            ).dt.date

        # 2. Standardize status to lowercase
        if "status" in df.columns:
            df["status"] = df["status"].str.lower().str.strip()

        # 3. Duplicate detection
        if "transaction_id" in df.columns:
            dup_mask = df.duplicated(subset=["transaction_id"], keep=False)
            n_dups = dup_mask.sum()
            if n_dups > 0:
                logger.warning(f"Found {n_dups} duplicate transaction_ids in billing")
                for _, row in df[dup_mask].iterrows():
                    self._quarantine(
                        source_system="billing",
                        record_id=str(row.get("transaction_id", "UNKNOWN")),
                        reason=f"Duplicate transaction_id",
                        rule_id="DQ-B002",
                        raw_record=row.to_dict(),
                    )
                # Keep first occurrence
                df = df.drop_duplicates(subset=["transaction_id"], keep="first")

        # 4. Validity checks - invalid status
        if "status" in df.columns:
            invalid_status_mask = ~df["status"].isin(self.VALID_BILLING_STATUSES) & df["status"].notna()
            for _, row in df[invalid_status_mask].iterrows():
                self._quarantine(
                    source_system="billing",
                    record_id=str(row.get("transaction_id", "UNKNOWN")),
                    reason=f"Invalid status: {row.get('status')}",
                    rule_id="DQ-B004",
                    raw_record=row.to_dict(),
                )
            df = df[~invalid_status_mask]

        # 5. Null amount is flagged but NOT removed (reported as completeness issue)
        null_amount_mask = df["amount"].isna()
        for _, row in df[null_amount_mask].iterrows():
            self._quarantine(
                source_system="billing",
                record_id=str(row.get("transaction_id", "UNKNOWN")),
                reason="Null amount — completeness violation",
                rule_id="DQ-B001",
                raw_record=row.to_dict(),
            )

        # 6. Negative amount quarantine
        if "amount" in df.columns:
            neg_mask = (df["amount"] < 0) & df["amount"].notna()
            for _, row in df[neg_mask].iterrows():
                self._quarantine(
                    source_system="billing",
                    record_id=str(row.get("transaction_id", "UNKNOWN")),
                    reason=f"Negative amount: {row.get('amount')}",
                    rule_id="DQ-B005",
                    raw_record=row.to_dict(),
                )

        # 7. Add silver metadata
        df["_is_recognized_revenue"] = df["status"] == "completed"
        df["_silver_processed_at"] = datetime.now(timezone.utc).isoformat()
        df["_silver_run_id"] = self.run_id

        logger.info(
            f"Billing silver complete: {len(df)} clean records, "
            f"{len(self.quarantine_records)} quarantined"
        )
        return df

    def transform_analytics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize analytics data."""
        logger.info(f"Silver transform: analytics ({len(df)} rows)")
        df = df.copy()

        # 1. Type normalization
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date

        if "total_revenue" in df.columns:
            df["total_revenue"] = pd.to_numeric(df["total_revenue"], errors="coerce")

        if "total_customers" in df.columns:
            df["total_customers"] = pd.to_numeric(
                df["total_customers"], errors="coerce"
            ).astype("Int64")

        if "avg_transaction" in df.columns:
            df["avg_transaction"] = pd.to_numeric(df["avg_transaction"], errors="coerce")

        # 2. Duplicate date detection
        if "date" in df.columns:
            dup_dates = df[df.duplicated(subset=["date"], keep=False)]
            if len(dup_dates) > 0:
                for _, row in dup_dates.iterrows():
                    self._quarantine(
                        source_system="analytics",
                        record_id=str(row.get("date")),
                        reason="Duplicate date — should be one row per day",
                        rule_id="DQ-A002",
                        raw_record=row.to_dict(),
                    )
                df = df.drop_duplicates(subset=["date"], keep="first")

        # 3. NULL total_revenue is flagged (NOT replaced with 0)
        null_rev_mask = df["total_revenue"].isna()
        n_null = null_rev_mask.sum()
        if n_null > 0:
            logger.warning(f"Analytics has {n_null} rows with NULL total_revenue")
            for _, row in df[null_rev_mask].iterrows():
                self._quarantine(
                    source_system="analytics",
                    record_id=str(row.get("date")),
                    reason="NULL total_revenue — completeness violation",
                    rule_id="DQ-A001",
                    raw_record=row.to_dict(),
                )

        # 4. Inconsistency: customers=0 but revenue > 0
        if "total_customers" in df.columns and "total_revenue" in df.columns:
            inconsistent = (df["total_customers"] == 0) & (df["total_revenue"] > 0) & df["total_revenue"].notna()
            for _, row in df[inconsistent].iterrows():
                self._quarantine(
                    source_system="analytics",
                    record_id=str(row.get("date")),
                    reason=f"Zero customers but revenue={row.get('total_revenue')} — internal inconsistency",
                    rule_id="DQ-A003",
                    raw_record=row.to_dict(),
                )

        # 5. Add silver metadata
        df["_silver_processed_at"] = datetime.now(timezone.utc).isoformat()
        df["_silver_run_id"] = self.run_id
        df["_has_null_revenue"] = null_rev_mask

        logger.info(
            f"Analytics silver complete: {len(df)} records, "
            f"{n_null} null revenue rows flagged"
        )
        return df

    def transform_crm(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize CRM data."""
        logger.info(f"Silver transform: CRM ({len(df)} rows)")
        df = df.copy()

        # 1. Type normalization
        if "signup_date" in df.columns:
            df["signup_date"] = pd.to_datetime(df["signup_date"], errors="coerce").dt.date
        if "updated_at" in df.columns:
            df["updated_at"] = pd.to_datetime(df["updated_at"], errors="coerce")

        # 2. Duplicate customer_id
        if "customer_id" in df.columns:
            dup_cids = df[df.duplicated(subset=["customer_id"], keep=False)]
            for _, row in dup_cids.iterrows():
                self._quarantine(
                    source_system="crm",
                    record_id=str(row.get("customer_id")),
                    reason="Duplicate customer_id",
                    rule_id="DQ-C001",
                    raw_record=row.to_dict(),
                )
            df = df.drop_duplicates(subset=["customer_id"], keep="first")

        # 3. Invalid status
        if "customer_status" in df.columns:
            df["customer_status"] = df["customer_status"].str.upper().str.strip()
            invalid_status = ~df["customer_status"].isin(self.VALID_CRM_STATUSES) & df["customer_status"].notna()
            for _, row in df[invalid_status].iterrows():
                self._quarantine(
                    source_system="crm",
                    record_id=str(row.get("customer_id")),
                    reason=f"Invalid customer_status: {row.get('customer_status')}",
                    rule_id="DQ-C003",
                    raw_record=row.to_dict(),
                )

        # 4. Email validation
        if "email" in df.columns:
            null_email = df["email"].isna()
            for _, row in df[null_email].iterrows():
                self._quarantine(
                    source_system="crm",
                    record_id=str(row.get("customer_id")),
                    reason="Null email",
                    rule_id="DQ-C002",
                    raw_record=row.to_dict(),
                )

            invalid_email = df["email"].notna() & ~df["email"].apply(
                lambda e: bool(self.EMAIL_PATTERN.match(str(e))) if e else False
            )
            for _, row in df[invalid_email].iterrows():
                self._quarantine(
                    source_system="crm",
                    record_id=str(row.get("customer_id")),
                    reason=f"Invalid email format: {row.get('email')}",
                    rule_id="DQ-C004",
                    raw_record=row.to_dict(),
                )

        df["_silver_processed_at"] = datetime.now(timezone.utc).isoformat()
        df["_silver_run_id"] = self.run_id

        logger.info(f"CRM silver complete: {len(df)} records")
        return df

    def save_silver(self, df: pd.DataFrame, source_system: str) -> Path:
        """Write Silver layer Parquet file."""
        output_dir = self.silver_dir / source_system
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{source_system}_{self.run_id[:8]}.parquet"
        df.to_parquet(output_path, index=False)
        logger.info(f"Saved silver.{source_system} → {output_path}")
        return output_path

    def save_quarantine(self) -> Optional[Path]:
        """Save all quarantine records to the quarantine layer."""
        if not self.quarantine_records:
            logger.info("No quarantine records to save")
            return None

        quarantine_dir = self.silver_dir / "quarantine"
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        output_path = quarantine_dir / f"quarantine_{self.run_id[:8]}.parquet"

        qdf = pd.DataFrame(self.quarantine_records)
        qdf.to_parquet(output_path, index=False)
        logger.info(
            f"Saved {len(self.quarantine_records)} quarantine records → {output_path}"
        )
        return output_path

    def read_silver(self, source_system: str) -> pd.DataFrame:
        """Read latest Silver layer data for a source."""
        source_dir = self.silver_dir / source_system
        if not source_dir.exists():
            raise FileNotFoundError(f"No silver data for: {source_system}")
        files = sorted(source_dir.glob("*.parquet"))
        if not files:
            raise FileNotFoundError(f"No parquet files in {source_dir}")
        dfs = [pd.read_parquet(f) for f in files]
        return pd.concat(dfs, ignore_index=True)

    def read_quarantine(self) -> pd.DataFrame:
        """Read all quarantine records."""
        quarantine_dir = self.silver_dir / "quarantine"
        if not quarantine_dir.exists():
            return pd.DataFrame()
        files = list(quarantine_dir.glob("*.parquet"))
        if not files:
            return pd.DataFrame()
        dfs = [pd.read_parquet(f) for f in files]
        return pd.concat(dfs, ignore_index=True)
