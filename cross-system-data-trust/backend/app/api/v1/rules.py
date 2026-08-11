"""Configurable Data Quality Rules API routes."""
from typing import Any, List, Optional
import yaml
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_db
from app.models.models import QualityRule
from app.schemas.schemas import QualityRuleResponse
from app.core.config import settings

router = APIRouter()

RULES_YAML_PATH = Path(__file__).parent.parent.parent.parent.parent / "data-engine" / "config" / "quality_rules.yaml"


@router.get("", response_model=List[QualityRuleResponse], summary="List Configured Data Quality Rules")
async def list_quality_rules(
    source: Optional[str] = None,
    enabled_only: bool = False,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List data quality rules loaded from YAML configuration or PostgreSQL."""
    query = select(QualityRule)
    if source:
        query = query.where(QualityRule.source == source.lower())
    if enabled_only:
        query = query.where(QualityRule.enabled == True)

    result = await db.execute(query)
    rules = result.scalars().all()

    if not rules and RULES_YAML_PATH.exists():
        # Fallback reading YAML directly
        try:
            with open(RULES_YAML_PATH) as f:
                data = yaml.safe_load(f)
                yaml_rules = data.get("rules", [])
                out = []
                import datetime
                now = datetime.datetime.now(datetime.timezone.utc)
                for idx, r in enumerate(yaml_rules):
                    if source and r.get("source") != source.lower():
                        continue
                    if enabled_only and not r.get("enabled", True):
                        continue
                    out.append(QualityRuleResponse(
                        id=str(idx),
                        rule_id=r.get("rule_id", f"DQ-{idx}"),
                        source=r.get("source", "billing"),
                        column=r.get("column"),
                        rule_type=r.get("rule_type", "completeness"),
                        description=r.get("description", ""),
                        threshold=r.get("threshold", 0.95),
                        severity=r.get("severity", "HIGH"),
                        enabled=r.get("enabled", True),
                        config=r,
                        created_at=now,
                    ))
                return out
        except Exception:
            pass

    return rules


@router.patch("/{rule_id}", summary="Update Rule Configuration or Threshold")
async def update_quality_rule(
    rule_id: str,
    enabled: Optional[bool] = None,
    threshold: Optional[float] = None,
    severity: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Update a rule's threshold or enabled status.
    Allows user configuration without editing code.
    """
    result = await db.execute(select(QualityRule).where(QualityRule.rule_id == rule_id))
    rule = result.scalars().first()

    if rule:
        if enabled is not None:
            rule.enabled = enabled
        if threshold is not None:
            rule.threshold = threshold
        if severity is not None:
            rule.severity = severity.upper()
        await db.commit()
        await db.refresh(rule)
        return rule

    # Also update YAML config file directly if present
    if RULES_YAML_PATH.exists():
        try:
            with open(RULES_YAML_PATH) as f:
                data = yaml.safe_load(f)
            
            rules_list = data.get("rules", [])
            updated = False
            for r in rules_list:
                if r.get("rule_id") == rule_id:
                    if enabled is not None:
                        r["enabled"] = enabled
                    if threshold is not None:
                        r["threshold"] = threshold
                    if severity is not None:
                        r["severity"] = severity.upper()
                    updated = True
                    break
            
            if updated:
                with open(RULES_YAML_PATH, "w") as f:
                    yaml.dump(data, f, sort_keys=False)
                return {"message": f"Rule {rule_id} updated in YAML config", "rule_id": rule_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to update rule YAML: {e}")

    raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
