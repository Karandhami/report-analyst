"""Deterministic ratio computation.

A pure function of FinancialStatements -> RatioSet. No AI, no I/O. This is the
quantitative core: every ratio shown anywhere in the product is computed here,
in tested code, never produced by a language model.

Each ratio guards its own inputs and returns None when it cannot be computed
meaningfully (missing data, or a denominator of zero). Absent ratios are
surfaced to the user as caveats rather than silently shown as zero.
"""

from __future__ import annotations

from decimal import Decimal

from reportanalyst.models.domain import FinancialStatements, RatioSet


def _safe_div(num: Decimal | None, den: Decimal | None) -> Decimal | None:
    if num is None or den is None or den == 0:
        return None
    return num / den


def compute_ratios(fs: FinancialStatements) -> RatioSet:
    inc, bal, cf = fs.income, fs.balance, fs.cash_flow
    rev = inc.revenue

    net_debt = None
    if bal.total_debt is not None:
        net_debt = bal.total_debt - (bal.cash or Decimal(0))

    return RatioSet(
        gross_margin=_safe_div(inc.gross_profit, rev),
        operating_margin=_safe_div(inc.operating_income, rev),
        net_margin=_safe_div(inc.net_income, rev),
        ebitda_margin=_safe_div(inc.ebitda, rev),
        current_ratio=_safe_div(bal.current_assets, bal.current_liabilities),
        debt_to_equity=_safe_div(bal.total_debt, bal.total_equity),
        net_leverage=_safe_div(net_debt, inc.ebitda),
        return_on_equity=_safe_div(inc.net_income, bal.total_equity),
        return_on_assets=_safe_div(inc.net_income, bal.total_assets),
        interest_coverage=_safe_div(inc.operating_income, inc.interest_expense),
        fcf_margin=_safe_div(cf.free_cash_flow, rev),
    )


def list_missing(ratios: RatioSet) -> list[str]:
    """Return the names of ratios that could not be computed."""
    return [name for name, value in ratios.model_dump().items() if value is None]
