"""Tests for the deterministic ratio engine and sector benchmarking."""

from decimal import Decimal

import pytest

from reportanalyst.benchmark.engine import benchmark
from reportanalyst.models.domain import (
    BalanceSheet,
    CashFlow,
    FinancialStatements,
    IncomeStatement,
    Sector,
)
from reportanalyst.ratios.engine import compute_ratios, list_missing


@pytest.fixture
def healthy() -> FinancialStatements:
    return FinancialStatements(
        fiscal_year=2024,
        income=IncomeStatement(
            revenue=Decimal("1000"),
            cost_of_revenue=Decimal("350"),
            operating_income=Decimal("200"),
            interest_expense=Decimal("20"),
            net_income=Decimal("150"),
            depreciation_amortization=Decimal("50"),
        ),
        balance=BalanceSheet(
            total_assets=Decimal("2000"),
            current_assets=Decimal("800"),
            cash=Decimal("300"),
            current_liabilities=Decimal("400"),
            total_debt=Decimal("500"),
            total_equity=Decimal("1000"),
        ),
        cash_flow=CashFlow(operating_cash_flow=Decimal("220"), capex=Decimal("70")),
    )


def test_margins(healthy):
    r = compute_ratios(healthy)
    assert r.gross_margin == Decimal("0.65")  # (1000-350)/1000
    assert r.operating_margin == Decimal("0.20")
    assert r.net_margin == Decimal("0.15")
    assert r.ebitda_margin == Decimal("0.25")  # (200+50)/1000


def test_leverage_and_coverage(healthy):
    r = compute_ratios(healthy)
    assert r.debt_to_equity == Decimal("0.5")
    # net debt = 500 - 300 = 200; ebitda = 250; 200/250 = 0.8
    assert r.net_leverage == Decimal("0.8")
    assert r.interest_coverage == Decimal("10")  # 200/20


def test_fcf_margin(healthy):
    r = compute_ratios(healthy)
    # fcf = 220 - 70 = 150; /1000 = 0.15
    assert r.fcf_margin == Decimal("0.15")


def test_missing_data_yields_none_not_crash():
    fs = FinancialStatements(income=IncomeStatement(revenue=Decimal("100")))
    r = compute_ratios(fs)
    assert r.gross_margin is None  # no cost_of_revenue
    assert r.net_leverage is None  # no debt/ebitda
    missing = list_missing(r)
    assert "net_leverage" in missing


def test_zero_denominator_is_safe():
    fs = FinancialStatements(income=IncomeStatement(revenue=Decimal("0"), net_income=Decimal("10")))
    r = compute_ratios(fs)
    assert r.net_margin is None  # division by zero revenue -> None


def test_benchmark_verdicts(healthy):
    r = compute_ratios(healthy)
    b = benchmark(r, Sector.technology)
    # gross margin 0.65 vs tech norm 0.65 -> in line
    assert b["gross_margin"]["verdict"] == "in_line"
    # operating margin 0.20 == norm 0.20 -> in line
    assert b["operating_margin"]["verdict"] == "in_line"


def test_benchmark_skips_missing_ratios():
    fs = FinancialStatements(income=IncomeStatement(revenue=Decimal("100")))
    r = compute_ratios(fs)
    b = benchmark(r, Sector.technology)
    # gross_margin couldn't be computed, so it shouldn't appear
    assert "gross_margin" not in b
