"""Tests for synthetic financial data generation.

Pure logic tests — no mocks needed.

Covers:
- Financial data: correct row counts, valid dimension members, numeric amounts
- Journal entries: balanced debit/credit, correct pairing, valid members
- Dimension data: hierarchical structure, known member names
- Unknown data type returns error
"""

from __future__ import annotations

import pytest

from synthetic.generator import (
    ACCOUNTS,
    CURRENCIES,
    ENTITIES,
    PERIODS,
    SCENARIOS,
    _generate_dimension_data,
    _generate_financial_data,
    _generate_journal_entries,
    generate_synthetic,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Financial data generation tests
# ---------------------------------------------------------------------------
class TestGenerateFinancialData:
    """Tests for _generate_financial_data."""

    def test_correct_row_count(self):
        result = _generate_financial_data(50, {})
        assert result["row_count"] == 50
        assert len(result["rows"]) == 50

    def test_single_row(self):
        result = _generate_financial_data(1, {})
        assert result["row_count"] == 1

    def test_large_row_count(self):
        result = _generate_financial_data(1000, {})
        assert result["row_count"] == 1000

    def test_type_is_financial(self):
        result = _generate_financial_data(10, {})
        assert result["type"] == "financial"

    def test_columns_present(self):
        result = _generate_financial_data(10, {})
        expected_cols = ["Entity", "Account", "Scenario", "Period", "Year", "Currency", "Amount", "View"]
        assert result["columns"] == expected_cols

    def test_valid_entity_members(self):
        result = _generate_financial_data(100, {})
        entities = {row["Entity"] for row in result["rows"]}
        assert entities.issubset(set(ENTITIES))

    def test_valid_account_members(self):
        result = _generate_financial_data(100, {})
        accounts = {row["Account"] for row in result["rows"]}
        assert accounts.issubset(set(ACCOUNTS))

    def test_valid_scenario_members(self):
        result = _generate_financial_data(100, {})
        scenarios = {row["Scenario"] for row in result["rows"]}
        assert scenarios.issubset(set(SCENARIOS))

    def test_valid_period_members(self):
        result = _generate_financial_data(100, {})
        periods = {row["Period"] for row in result["rows"]}
        assert periods.issubset(set(PERIODS))

    def test_valid_currency_members(self):
        result = _generate_financial_data(100, {})
        currencies = {row["Currency"] for row in result["rows"]}
        assert currencies.issubset(set(CURRENCIES))

    def test_amount_is_float(self):
        result = _generate_financial_data(10, {})
        for row in result["rows"]:
            assert isinstance(row["Amount"], float)

    def test_amount_has_two_decimal_places(self):
        result = _generate_financial_data(100, {})
        for row in result["rows"]:
            str_amount = str(row["Amount"])
            if "." in str_amount:
                decimal_places = len(str_amount.split(".")[1])
                assert decimal_places <= 2

    def test_year_values(self):
        result = _generate_financial_data(100, {})
        years = {row["Year"] for row in result["rows"]}
        assert years.issubset({"2024", "2025"})

    def test_view_is_ytd(self):
        result = _generate_financial_data(10, {})
        for row in result["rows"]:
            assert row["View"] == "YTD"


# ---------------------------------------------------------------------------
# Journal entry generation tests
# ---------------------------------------------------------------------------
class TestGenerateJournalEntries:
    """Tests for _generate_journal_entries."""

    def test_correct_row_count_doubled(self):
        """Each journal entry produces a debit + credit row, so total = 2x input."""
        result = _generate_journal_entries(10)
        assert result["row_count"] == 20
        assert len(result["entries"]) == 20

    def test_type_is_journal(self):
        result = _generate_journal_entries(5)
        assert result["type"] == "journal"

    def test_balanced_debit_credit(self):
        """For each journal ID, total debits should equal total credits."""
        result = _generate_journal_entries(50)

        # Group by JournalId
        journals: dict[str, dict] = {}
        for entry in result["entries"]:
            jid = entry["JournalId"]
            if jid not in journals:
                journals[jid] = {"debit": 0.0, "credit": 0.0}
            journals[jid]["debit"] += entry["DebitAmount"]
            journals[jid]["credit"] += entry["CreditAmount"]

        for jid, totals in journals.items():
            assert abs(totals["debit"] - totals["credit"]) < 0.01, (
                f"Journal {jid} is unbalanced: debit={totals['debit']}, credit={totals['credit']}"
            )

    def test_debit_entry_has_zero_credit(self):
        result = _generate_journal_entries(10)
        debit_entries = [e for e in result["entries"] if e["DebitAmount"] > 0]
        for entry in debit_entries:
            assert entry["CreditAmount"] == 0

    def test_credit_entry_has_zero_debit(self):
        result = _generate_journal_entries(10)
        credit_entries = [e for e in result["entries"] if e["CreditAmount"] > 0]
        for entry in credit_entries:
            assert entry["DebitAmount"] == 0

    def test_journal_ids_are_unique_per_pair(self):
        result = _generate_journal_entries(20)
        journal_ids = [e["JournalId"] for e in result["entries"]]
        # Each journal ID appears exactly twice (debit + credit)
        from collections import Counter

        counts = Counter(journal_ids)
        for jid, count in counts.items():
            assert count == 2, f"Journal {jid} appeared {count} times, expected 2"

    def test_journal_id_format(self):
        result = _generate_journal_entries(5)
        for entry in result["entries"]:
            assert entry["JournalId"].startswith("JE-")
            assert len(entry["JournalId"]) == 11  # "JE-" + 8 hex chars

    def test_valid_entity_members_in_journals(self):
        result = _generate_journal_entries(50)
        entities = {e["Entity"] for e in result["entries"]}
        # Journal entries use ENTITIES[:5]
        assert entities.issubset(set(ENTITIES[:5]))

    def test_debit_credit_same_period(self):
        """Paired entries should share the same Period."""
        result = _generate_journal_entries(20)
        entries = result["entries"]
        # Entries come in pairs (debit at even index, credit at odd index)
        for i in range(0, len(entries), 2):
            assert entries[i]["Period"] == entries[i + 1]["Period"]

    def test_amounts_are_positive(self):
        result = _generate_journal_entries(50)
        for entry in result["entries"]:
            # At least one of debit/credit should be positive
            assert entry["DebitAmount"] >= 0
            assert entry["CreditAmount"] >= 0
            assert entry["DebitAmount"] > 0 or entry["CreditAmount"] > 0


# ---------------------------------------------------------------------------
# Dimension data generation tests
# ---------------------------------------------------------------------------
class TestGenerateDimensionData:
    """Tests for _generate_dimension_data."""

    def test_entity_dimension_structure(self):
        result = _generate_dimension_data({"dimension": "Entity"})
        assert result["type"] == "dimension"
        assert result["dimension"] == "Entity"
        assert len(result["members"]) == 7  # Corp + 6 children

    def test_entity_root_is_corp(self):
        result = _generate_dimension_data({"dimension": "Entity"})
        root = result["members"][0]
        assert root["name"] == "Corp"
        assert root["parent"] == ""
        assert root["is_leaf"] is False

    def test_entity_children_have_corp_parent(self):
        result = _generate_dimension_data({"dimension": "Entity"})
        children = result["members"][1:]
        for child in children:
            assert child["parent"] == "Corp"
            assert child["is_leaf"] is True

    def test_account_dimension_structure(self):
        result = _generate_dimension_data({"dimension": "Account"})
        assert result["dimension"] == "Account"
        assert len(result["members"]) == 6

    def test_account_root_is_totalpl(self):
        result = _generate_dimension_data({"dimension": "Account"})
        root = result["members"][0]
        assert root["name"] == "TotalPL"
        assert root["parent"] == ""
        assert root["is_leaf"] is False

    def test_unknown_dimension_generates_generic_members(self):
        result = _generate_dimension_data({"dimension": "Custom"})
        assert len(result["members"]) == 10
        # First member is root with no parent
        assert result["members"][0]["parent"] == ""
        assert result["members"][0]["is_leaf"] is False

    def test_default_dimension_is_entity(self):
        result = _generate_dimension_data({})
        assert result["dimension"] == "Entity"


# ---------------------------------------------------------------------------
# generate_synthetic async wrapper tests
# ---------------------------------------------------------------------------
class TestGenerateSyntheticAsync:
    """Tests for the async generate_synthetic entry point."""

    @pytest.mark.asyncio
    async def test_financial_type(self):
        result = await generate_synthetic("financial", row_count=10)
        assert result["type"] == "financial"
        assert result["row_count"] == 10

    @pytest.mark.asyncio
    async def test_journal_type(self):
        result = await generate_synthetic("journal", row_count=5)
        assert result["type"] == "journal"

    @pytest.mark.asyncio
    async def test_dimension_type(self):
        result = await generate_synthetic("dimension", schema={"dimension": "Entity"})
        assert result["type"] == "dimension"

    @pytest.mark.asyncio
    async def test_unknown_type_returns_error(self):
        result = await generate_synthetic("unknown_type")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_default_row_count(self):
        result = await generate_synthetic("financial")
        assert result["row_count"] == 100
