"""Domain models for the annual-report analyst.

Core concepts:
  - FinancialStatements: the three statements, as exact decimals, for one or
    more reporting periods.
  - RatioSet: the computed ratios derived from the statements.
  - Citation: a grounded reference back to a passage in the source document.
  - AnalysisMemo: the final structured output — judgment plus citations.

Design notes:
  - Money is Decimal, never float, to avoid drift on financial figures.
  - Every field that can be absent in a real filing is Optional; the ratio
    layer degrades gracefully rather than crashing on gaps.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class Sector(str, Enum):
    technology = "technology"
    financials = "financials"
    healthcare = "healthcare"
    industrials = "industrials"
    consumer = "consumer"
    energy = "energy"
    materials = "materials"
    other = "other"


class IncomeStatement(BaseModel):
    revenue: Decimal | None = None
    cost_of_revenue: Decimal | None = None
    operating_income: Decimal | None = None
    interest_expense: Decimal | None = None
    net_income: Decimal | None = None
    depreciation_amortization: Decimal | None = None

    @property
    def gross_profit(self) -> Decimal | None:
        if self.revenue is not None and self.cost_of_revenue is not None:
            return self.revenue - self.cost_of_revenue
        return None

    @property
    def ebitda(self) -> Decimal | None:
        # EBITDA = operating income + D&A. Honest, transparent build-up.
        if self.operating_income is not None and self.depreciation_amortization is not None:
            return self.operating_income + self.depreciation_amortization
        return None


class BalanceSheet(BaseModel):
    total_assets: Decimal | None = None
    current_assets: Decimal | None = None
    cash: Decimal | None = None
    total_liabilities: Decimal | None = None
    current_liabilities: Decimal | None = None
    total_debt: Decimal | None = None
    total_equity: Decimal | None = None


class CashFlow(BaseModel):
    operating_cash_flow: Decimal | None = None
    capex: Decimal | None = None

    @property
    def free_cash_flow(self) -> Decimal | None:
        if self.operating_cash_flow is not None and self.capex is not None:
            # capex stored as a positive outflow; subtract it.
            return self.operating_cash_flow - self.capex
        return None


class FinancialStatements(BaseModel):
    fiscal_year: int | None = None
    income: IncomeStatement = Field(default_factory=IncomeStatement)
    balance: BalanceSheet = Field(default_factory=BalanceSheet)
    cash_flow: CashFlow = Field(default_factory=CashFlow)


class Citation(BaseModel):
    """A grounded reference: which passage supports a qualitative claim."""

    claim: str
    source_text: str
    page: int | None = None
    score: float = Field(default=0.0, description="retrieval similarity 0..1")


class RatioSet(BaseModel):
    """Computed ratios. All optional — depends on what the filing provided."""

    gross_margin: Decimal | None = None
    operating_margin: Decimal | None = None
    net_margin: Decimal | None = None
    ebitda_margin: Decimal | None = None
    current_ratio: Decimal | None = None
    debt_to_equity: Decimal | None = None
    net_leverage: Decimal | None = None
    return_on_equity: Decimal | None = None
    return_on_assets: Decimal | None = None
    interest_coverage: Decimal | None = None
    fcf_margin: Decimal | None = None


class BenchmarkEntry(BaseModel):
    """One ratio compared to its sector norm, for the benchmark visual."""

    name: str
    value: float
    norm: float
    verdict: str  # above / in_line / below


class AnalysisMemo(BaseModel):
    company_name: str
    sector: Sector
    fiscal_year: int | None = None
    ratios: RatioSet
    strengths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    narrative: str = ""
    citations: list[Citation] = Field(default_factory=list)
    data_caveats: list[str] = Field(default_factory=list)
    benchmarks: list[BenchmarkEntry] = Field(default_factory=list)
    health_score: float | None = Field(
        default=None, description="0..100 composite financial-health score"
    )
