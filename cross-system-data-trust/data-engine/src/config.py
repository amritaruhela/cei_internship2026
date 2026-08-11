"""
Data Engine Configuration Module
Loads settings from environment variables and YAML config files.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).parent.parent
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = Path(os.getenv("DATA_DIR", str(ROOT_DIR.parent / "data")))


class DataEngineSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Paths
    data_dir: Path = DATA_DIR
    raw_dir: Path = DATA_DIR / "raw"
    bronze_dir: Path = DATA_DIR / "bronze"
    silver_dir: Path = DATA_DIR / "silver"
    gold_dir: Path = DATA_DIR / "gold"
    generated_dir: Path = DATA_DIR / "generated"

    # Spark
    spark_local_mode: bool = True
    spark_master: str = "local[*]"
    spark_app_name: str = "DataTrust"
    spark_driver_memory: str = "2g"

    # Databricks (production only)
    databricks_host: str = ""
    databricks_token: str = ""
    databricks_cluster_id: str = ""
    delta_catalog: str = "main"
    delta_schema: str = "datatrust"

    # Environment
    environment: str = "development"
    log_level: str = "INFO"

    @field_validator("data_dir", "raw_dir", "bronze_dir", "silver_dir", "gold_dir", "generated_dir", mode="before")
    @classmethod
    def ensure_path(cls, v: Any) -> Path:
        p = Path(v)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def is_databricks(self) -> bool:
        return bool(self.databricks_host and self.databricks_token)


settings = DataEngineSettings()


def load_yaml(filename: str) -> dict[str, Any]:
    """Load a YAML configuration file from the config directory."""
    path = CONFIG_DIR / filename
    with open(path) as f:
        return yaml.safe_load(f)


def get_quality_rules() -> list[dict[str, Any]]:
    return load_yaml("quality_rules.yaml").get("rules", [])


def get_thresholds() -> dict[str, Any]:
    return load_yaml("thresholds.yaml")


def get_sources() -> dict[str, Any]:
    return load_yaml("sources.yaml")
