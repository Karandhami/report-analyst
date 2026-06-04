"""End-to-end test: parse a filing, analyze, produce a grounded memo."""

from decimal import Decimal
from pathlib import Path

from reportanalyst.memo.analyzer import analyze
from reportanalyst.models.domain import (
    BalanceSheet,
    CashFlow,
    FinancialStatements,
    IncomeStatement,
    Sector,
)
from reportanalyst.parsing.parser import parse_text

DATA = Path(__file__).resolve().parents[1] / "data"


def _statements() -> FinancialStatements:
    return FinancialStatements(
        fiscal_year=2024,
        income=IncomeStatement(
            revenue=Decimal("500"),
            cost_of_revenue=Decimal("190"),
            operating_income=Decimal("70"),
            interest_expense=Decimal("8"),
            net_income=Decimal("52"),
            depreciation_amortization=Decimal("30"),
        ),
        balance=BalanceSheet(
            total_assets=Decimal("900"),
            current_assets=Decimal("400"),
            cash=Decimal("180"),
            current_liabilities=Decimal("160"),
            total_debt=Decimal("120"),
            total_equity=Decimal("520"),
        ),
        cash_flow=CashFlow(operating_cash_flow=Decimal("95"), capex=Decimal("25")),
    )


def test_parse_locates_sections():
    text = (DATA / "sample_filing.txt").read_text()
    filing = parse_text(text)
    assert "risk_factors" in filing.sections
    assert "mdna" in filing.sections
    assert "outlook" in filing.sections


def test_full_analysis_produces_memo():
    text = (DATA / "sample_filing.txt").read_text()
    filing = parse_text(text)
    memo = analyze("Nimbus Cloud Systems", Sector.technology, _statements(), filing)

    assert memo.company_name == "Nimbus Cloud Systems"
    assert memo.fiscal_year == 2024
    assert memo.ratios.gross_margin == Decimal("0.62")  # (500-190)/500
    assert memo.narrative  # non-empty
    # The filing discusses margin/growth/risk, so we expect grounded citations.
    assert len(memo.citations) >= 1
    # Every citation must carry the passage it was grounded in.
    assert all(c.source_text for c in memo.citations)


def test_citations_are_grounded_in_real_passages():
    text = (DATA / "sample_filing.txt").read_text()
    filing = parse_text(text)
    memo = analyze("Nimbus Cloud Systems", Sector.technology, _statements(), filing)
    # Normalise whitespace: the chunker joins words with single spaces, while
    # the source has line breaks. Grounding is real if the words appear in order.
    normalised_source = " ".join(text.split())
    for c in memo.citations:
        normalised_passage = " ".join(c.source_text.split())
        assert normalised_passage[:40] in normalised_source


def test_citations_are_relevant_not_just_company_name():
    """Guard against the retriever surfacing the company-name/heading chunk.

    Each grounded citation must be a genuinely relevant passage, not a weak
    match that happens to quote the filing's opening line.
    """
    text = (DATA / "sample_filing.txt").read_text()
    filing = parse_text(text)
    memo = analyze("Nimbus Cloud Systems", Sector.technology, _statements(), filing)
    for c in memo.citations:
        # No citation should just be the company name / section heading.
        assert "Nimbus Cloud Systems, Inc." not in c.source_text[:40]
        # Every shown citation must clear the relevance bar.
        assert c.score >= 0.12


def test_analysis_without_filing_still_works():
    memo = analyze("NoNarrative Co", Sector.technology, _statements(), None)
    assert memo.citations == []
    assert memo.ratios.net_margin is not None
