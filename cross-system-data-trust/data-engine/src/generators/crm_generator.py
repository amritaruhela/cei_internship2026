"""
Synthetic CRM Data Generator
Generates realistic, deterministic CRM customer records.
Usage:
    python -m generators.crm_generator --seed 42 --count 10000 --output ./data/generated/crm.csv
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import random
import string
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import logging

logger = logging.getLogger(__name__)


REGIONS = ["North", "South", "East", "West", "Central"]
SEGMENTS = ["Enterprise", "SMB", "Startup", "Individual", "Government"]
STATUSES = ["ACTIVE", "INACTIVE", "CHURNED", "SUSPENDED"]
STATUS_WEIGHTS = [0.65, 0.15, 0.12, 0.08]

FIRST_NAMES = [
    "Aarav", "Priya", "Rahul", "Ananya", "Vikram", "Sneha", "Arjun", "Divya",
    "Rohan", "Kavya", "Aditya", "Pooja", "Karan", "Nisha", "Saurabh", "Meera",
    "Amit", "Shreya", "Nikhil", "Riya", "Raj", "Anjali", "Suresh", "Deepika",
    "James", "Sarah", "Michael", "Emma", "David", "Olivia", "John", "Sophie",
    "Liam", "Amelia", "Noah", "Isabella", "William", "Mia", "Ethan", "Charlotte",
    "Mohammed", "Fatima", "Ali", "Zara", "Ahmed", "Layla", "Omar", "Yasmin",
]

LAST_NAMES = [
    "Sharma", "Patel", "Kumar", "Singh", "Gupta", "Mehta", "Shah", "Verma",
    "Joshi", "Reddy", "Nair", "Iyer", "Pillai", "Menon", "Rao", "Naidu",
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Davis", "Miller", "Wilson",
    "Anderson", "Thomas", "Taylor", "Moore", "Martin", "Jackson", "Lee", "Harris",
    "Khan", "Ali", "Ahmed", "Hassan", "Rahman", "Malik", "Hussain", "Iqbal",
]

EMAIL_DOMAINS = [
    "gmail.com", "yahoo.com", "outlook.com", "company.com", "enterprise.io",
    "business.net", "corp.org", "startup.co", "tech.com", "digital.in",
]


def _rng(seed: int) -> random.Random:
    return random.Random(seed)


def _generate_email(first: str, last: str, rng: random.Random) -> str:
    patterns = [
        f"{first.lower()}.{last.lower()}@{rng.choice(EMAIL_DOMAINS)}",
        f"{first.lower()}{last.lower()[0]}@{rng.choice(EMAIL_DOMAINS)}",
        f"{first.lower()[0]}{last.lower()}@{rng.choice(EMAIL_DOMAINS)}",
        f"{first.lower()}{rng.randint(1, 999)}@{rng.choice(EMAIL_DOMAINS)}",
    ]
    return rng.choice(patterns)


def _generate_invalid_email(rng: random.Random) -> str:
    """Occasionally generate invalid emails to test validation rules."""
    invalids = [
        "notanemail",
        "missing@domain",
        "@nodomain.com",
        "spaces in@email.com",
        "",
    ]
    return rng.choice(invalids)


def generate_crm_records(
    count: int = 10000,
    seed: int = 42,
    null_email_rate: float = 0.03,
    invalid_email_rate: float = 0.02,
    start_customer_id: int = 0,
) -> list[dict[str, Any]]:
    """
    Generate deterministic CRM records.
    
    Args:
        count: Number of records to generate
        seed: Random seed for reproducibility
        null_email_rate: Fraction of records with null email (tests completeness)
        invalid_email_rate: Fraction with invalid email format (tests validity)
        start_customer_id: Starting customer ID number
    
    Returns:
        List of CRM record dicts
    """
    rng = _rng(seed)
    records = []

    start_date = date(2018, 1, 1)
    end_date = date(2024, 6, 30)
    date_range = (end_date - start_date).days

    for i in range(count):
        cid_num = start_customer_id + i
        customer_id = f"CRM{cid_num:06d}"

        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        customer_name = f"{first} {last}"

        # Email with controlled quality issues
        roll = rng.random()
        if roll < null_email_rate:
            email = None
        elif roll < null_email_rate + invalid_email_rate:
            email = _generate_invalid_email(rng)
        else:
            email = _generate_email(first, last, rng)

        signup_date = start_date + timedelta(days=rng.randint(0, date_range))
        status = rng.choices(STATUSES, weights=STATUS_WEIGHTS, k=1)[0]
        region = rng.choice(REGIONS)
        segment = rng.choice(SEGMENTS)

        # updated_at: recent for ACTIVE, older for CHURNED
        if status == "ACTIVE":
            days_ago = rng.randint(0, 30)
        elif status == "CHURNED":
            days_ago = rng.randint(180, 730)
        else:
            days_ago = rng.randint(30, 365)

        updated_at = datetime.now() - timedelta(days=days_ago)

        records.append({
            "customer_id": customer_id,
            "customer_name": customer_name,
            "email": email,
            "signup_date": signup_date.isoformat(),
            "customer_status": status,
            "region": region,
            "segment": segment,
            "updated_at": updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        })

    logger.info(f"Generated {len(records)} CRM records (seed={seed})")
    return records


def save_crm_csv(records: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["customer_id", "customer_name", "email", "signup_date",
                  "customer_status", "region", "segment", "updated_at"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    logger.info(f"Saved CRM data to {output_path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="CRM Data Generator")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--count", type=int, default=10000, help="Number of records")
    parser.add_argument("--output", type=str, default="./data/generated/crm.csv")
    parser.add_argument("--null-email-rate", type=float, default=0.03)
    parser.add_argument("--invalid-email-rate", type=float, default=0.02)
    args = parser.parse_args()

    records = generate_crm_records(
        count=args.count,
        seed=args.seed,
        null_email_rate=args.null_email_rate,
        invalid_email_rate=args.invalid_email_rate,
    )
    save_crm_csv(records, Path(args.output))
    print(f"✓ Generated {len(records)} CRM records → {args.output}")
