"""Synthetic financial data generation for testing."""

from __future__ import annotations

import random
import uuid
from datetime import datetime

import structlog

logger = structlog.get_logger()

# Common OneStream dimension members for synthetic data
ENTITIES = ["Corp", "US_East", "US_West", "EU_North", "EU_South", "APAC", "Elim_IC"]
ACCOUNTS = ["Revenue", "COGS", "OpEx", "CapEx", "Depreciation", "IC_Revenue", "IC_COGS", "Tax", "NetIncome"]
SCENARIOS = ["Actual", "Budget", "Forecast_Q1", "Forecast_Q2"]
PERIODS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CNY"]


async def generate_synthetic(
    data_type: str = "financial",
    row_count: int = 100,
    schema: dict | None = None,
) -> dict:
    """Generate synthetic data for testing OneStream business rules."""
    logger.info("synthetic.generate", data_type=data_type, row_count=row_count)

    if data_type == "financial":
        return _generate_financial_data(row_count, schema or {})
    elif data_type == "dimension":
        return _generate_dimension_data(schema or {})
    elif data_type == "journal":
        return _generate_journal_entries(row_count)
    else:
        return {"error": f"Unknown data type: {data_type}"}


def _generate_financial_data(row_count: int, schema: dict) -> dict:
    """Generate synthetic consolidation financial data."""
    rows = []
    for _ in range(row_count):
        rows.append({
            "Entity": random.choice(ENTITIES),
            "Account": random.choice(ACCOUNTS),
            "Scenario": random.choice(SCENARIOS),
            "Period": random.choice(PERIODS),
            "Year": random.choice(["2024", "2025"]),
            "Currency": random.choice(CURRENCIES),
            "Amount": round(random.uniform(-1_000_000, 10_000_000), 2),
            "View": "YTD",
        })

    return {
        "type": "financial",
        "row_count": len(rows),
        "columns": ["Entity", "Account", "Scenario", "Period", "Year", "Currency", "Amount", "View"],
        "rows": rows,
    }


def _generate_dimension_data(schema: dict) -> dict:
    """Generate synthetic dimension member hierarchies."""
    dimension = schema.get("dimension", "Entity")

    if dimension == "Entity":
        members = [
            {"name": "Corp", "parent": "", "is_leaf": False},
            {"name": "US_East", "parent": "Corp", "is_leaf": True},
            {"name": "US_West", "parent": "Corp", "is_leaf": True},
            {"name": "EU_North", "parent": "Corp", "is_leaf": True},
            {"name": "EU_South", "parent": "Corp", "is_leaf": True},
            {"name": "APAC", "parent": "Corp", "is_leaf": True},
            {"name": "Elim_IC", "parent": "Corp", "is_leaf": True},
        ]
    elif dimension == "Account":
        members = [
            {"name": "TotalPL", "parent": "", "is_leaf": False},
            {"name": "Revenue", "parent": "TotalPL", "is_leaf": True},
            {"name": "COGS", "parent": "TotalPL", "is_leaf": True},
            {"name": "GrossProfit", "parent": "TotalPL", "is_leaf": False},
            {"name": "OpEx", "parent": "GrossProfit", "is_leaf": True},
            {"name": "NetIncome", "parent": "TotalPL", "is_leaf": False},
        ]
    else:
        members = [{"name": f"Member_{i}", "parent": "" if i == 0 else "Member_0", "is_leaf": i > 0} for i in range(10)]

    return {"type": "dimension", "dimension": dimension, "members": members}


def _generate_journal_entries(row_count: int) -> dict:
    """Generate synthetic journal entries for data management testing."""
    entries = []
    for i in range(row_count):
        journal_id = f"JE-{uuid.uuid4().hex[:8].upper()}"
        debit_amount = round(random.uniform(1_000, 500_000), 2)
        entries.append({
            "JournalId": journal_id,
            "Entity": random.choice(ENTITIES[:5]),
            "Account": random.choice(ACCOUNTS[:4]),
            "DebitAmount": debit_amount,
            "CreditAmount": 0,
            "Description": f"Synthetic entry {i + 1}",
            "Period": random.choice(PERIODS),
        })
        # Offsetting credit entry
        entries.append({
            "JournalId": journal_id,
            "Entity": random.choice(ENTITIES[:5]),
            "Account": random.choice(ACCOUNTS[4:]),
            "DebitAmount": 0,
            "CreditAmount": debit_amount,
            "Description": f"Synthetic entry {i + 1} - offset",
            "Period": entries[-1]["Period"],
        })

    return {"type": "journal", "row_count": len(entries), "entries": entries}
