"""
Bronze Layer Ingestion Pipeline

Reads raw CSV files and writes them to the Bronze layer with:
- Ingestion timestamp
- Source system identifier
- Batch/run ID
- Record hash (SHA-256 of row contents for change detection)
- Schema preservation (no destructive transforms)

Bronze layer uses Parquet format locally, Delta format in Databricks.
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def _compute_record_hash(row: pd.Series) -> str:
    """Compute SHA-256 hash of all row values for change detection."""
    content = "|".join(str(v) for v in row.values)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


class BronzeIngester:
    """
    Ingests raw source files into the Bronze layer.
    
    Adds metadata columns without modifying source data:
    - _ingested_at: UTC timestamp of ingestion
    - _source_system: e.g., 'billing', 'crm', 'analytics'
    - _run_id: UUID for this ingestion batch
    - _record_hash: SHA-256 of row content
    - _source_file: original filename
    """

    def __init__(self, bronze_dir: Path, run_id: Optional[str] = None):
        self.bronze_dir = Path(bronze_dir)
        self.bronze_dir.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id or str(uuid.uuid4())
        self.ingested_at = datetime.now(timezone.utc).isoformat()

    def ingest_csv(
        self,
        source_file: Path,
        source_system: str,
        parse_dates: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Ingest a CSV file into the Bronze layer.
        
        Returns metadata about the ingestion run.
        """
        source_file = Path(source_file)
        logger.info(f"Ingesting {source_system} from {source_file}")

        df = pd.read_csv(source_file, parse_dates=parse_dates or [])

        records_read = len(df)
        schema_before = {col: str(df[col].dtype) for col in df.columns}

        # Add bronze metadata columns
        df["_ingested_at"] = self.ingested_at
        df["_source_system"] = source_system
        df["_run_id"] = self.run_id
        df["_source_file"] = source_file.name
        df["_record_hash"] = df.apply(_compute_record_hash, axis=1)

        # Capture schema snapshot
        schema_after = {col: str(df[col].dtype) for col in df.columns}

        # Write to bronze layer as Parquet
        output_dir = self.bronze_dir / source_system
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{source_system}_{self.run_id[:8]}.parquet"
        df.to_parquet(output_path, index=False)

        # Write schema snapshot
        schema_path = output_dir / f"schema_{self.run_id[:8]}.json"
        schema_snapshot = {
            "run_id": self.run_id,
            "source_system": source_system,
            "ingested_at": self.ingested_at,
            "source_file": source_file.name,
            "records_read": records_read,
            "schema": schema_before,
        }
        with open(schema_path, "w") as f:
            json.dump(schema_snapshot, f, indent=2)

        result = {
            "run_id": self.run_id,
            "source_system": source_system,
            "source_file": str(source_file),
            "ingested_at": self.ingested_at,
            "records_read": records_read,
            "records_written": len(df),
            "output_path": str(output_path),
            "schema": schema_before,
            "status": "SUCCESS",
            "error": None,
        }

        logger.info(
            f"Bronze ingestion complete: {source_system} "
            f"({records_read} records → {output_path})"
        )
        return result

    def ingest_all(self, raw_dir: Path, generated_dir: Optional[Path] = None) -> list[dict[str, Any]]:
        """
        Ingest all known source files from the raw data directory.
        """
        raw_dir = Path(raw_dir)
        results = []

        # Billing
        billing_file = raw_dir / "billing_dataset.csv"
        if billing_file.exists():
            results.append(self.ingest_csv(billing_file, "billing"))

        # Analytics
        analytics_file = raw_dir / "analytics_dataset.csv"
        if analytics_file.exists():
            results.append(self.ingest_csv(analytics_file, "analytics"))

        # CRM (generated)
        crm_candidates = [
            raw_dir / "crm.csv",
            (generated_dir / "crm.csv") if generated_dir else None,
        ]
        for crm_file in crm_candidates:
            if crm_file and crm_file.exists():
                results.append(self.ingest_csv(crm_file, "crm"))
                break

        return results

    def read_bronze(self, source_system: str) -> pd.DataFrame:
        """Read the latest bronze layer file for a source system."""
        source_dir = self.bronze_dir / source_system
        if not source_dir.exists():
            raise FileNotFoundError(f"No bronze data for source: {source_system}")

        parquet_files = sorted(source_dir.glob("*.parquet"))
        if not parquet_files:
            raise FileNotFoundError(f"No parquet files in {source_dir}")

        # Read all parquet files and concatenate (handles multiple ingestion runs)
        dfs = [pd.read_parquet(f) for f in parquet_files]
        df = pd.concat(dfs, ignore_index=True)

        # If multiple runs, keep latest version of each record by hash
        # (simplified Delta-like dedup)
        if "_run_id" in df.columns:
            df = df.sort_values("_ingested_at").drop_duplicates(
                subset=["_record_hash"], keep="last"
            )

        logger.info(f"Read {len(df)} records from bronze.{source_system}")
        return df
