"""FastAPI service for the annual-report analyst.

Endpoints:
  GET  /api/health              liveness
  GET  /api/sample              analyze the bundled sample filing (instant demo)
  POST /api/analyze/text        analyze pasted filing text + statement figures
  POST /api/analyze/pdf         upload a PDF + statement figures, get a memo

The statement figures are supplied alongside the document because reliably
extracting exact financials from arbitrary PDF layouts is its own hard problem;
here the user provides the headline numbers (or they come from a structured
source) and the engine does the ratios, benchmarking, and grounded narrative.
This is an honest design choice, surfaced in the UI.
"""

from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from reportanalyst.memo.analyzer import analyze
from reportanalyst.models.domain import (
    AnalysisMemo,
    BalanceSheet,
    CashFlow,
    FinancialStatements,
    IncomeStatement,
    Sector,
)
from reportanalyst.parsing.parser import parse_pdf, parse_text

DATA_DIR = Path(__file__).resolve().parents[3] / "data"

app = FastAPI(title="Annual Report Analyst", version="0.1.0")

_origins = os.getenv("ALLOWED_ORIGINS", "*")
_allow = [o.strip() for o in _origins.split(",")] if _origins != "*" else ["*"]
app.add_middleware(CORSMiddleware, allow_origins=_allow, allow_methods=["*"], allow_headers=["*"])


class StatementInput(BaseModel):
    """Headline figures the user supplies alongside the document."""

    company_name: str
    sector: Sector = Sector.technology
    fiscal_year: int | None = None
    revenue: Decimal | None = None
    cost_of_revenue: Decimal | None = None
    operating_income: Decimal | None = None
    interest_expense: Decimal | None = None
    net_income: Decimal | None = None
    depreciation_amortization: Decimal | None = None
    total_assets: Decimal | None = None
    current_assets: Decimal | None = None
    cash: Decimal | None = None
    current_liabilities: Decimal | None = None
    total_debt: Decimal | None = None
    total_equity: Decimal | None = None
    operating_cash_flow: Decimal | None = None
    capex: Decimal | None = None

    def to_statements(self) -> FinancialStatements:
        return FinancialStatements(
            fiscal_year=self.fiscal_year,
            income=IncomeStatement(
                revenue=self.revenue,
                cost_of_revenue=self.cost_of_revenue,
                operating_income=self.operating_income,
                interest_expense=self.interest_expense,
                net_income=self.net_income,
                depreciation_amortization=self.depreciation_amortization,
            ),
            balance=BalanceSheet(
                total_assets=self.total_assets,
                current_assets=self.current_assets,
                cash=self.cash,
                current_liabilities=self.current_liabilities,
                total_debt=self.total_debt,
                total_equity=self.total_equity,
            ),
            cash_flow=CashFlow(operating_cash_flow=self.operating_cash_flow, capex=self.capex),
        )


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/sample")
def sample() -> AnalysisMemo:
    text = (DATA_DIR / "sample_filing.txt").read_text()
    filing = parse_text(text)
    stmts = FinancialStatements(
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
    return analyze("Nimbus Cloud Systems", Sector.technology, stmts, filing)


class TextRequest(BaseModel):
    statements: StatementInput
    filing_text: str = ""


@app.post("/api/analyze/text")
def analyze_text_endpoint(req: TextRequest) -> AnalysisMemo:
    filing = parse_text(req.filing_text) if req.filing_text.strip() else None
    return analyze(
        req.statements.company_name,
        req.statements.sector,
        req.statements.to_statements(),
        filing,
    )


@app.post("/api/analyze/pdf")
async def analyze_pdf_endpoint(
    file: UploadFile = File(...),  # noqa: B008 - idiomatic FastAPI default
    statements_json: str = Form(...),
) -> AnalysisMemo:
    stmt = StatementInput.model_validate_json(statements_json)
    content = await file.read()
    filing = parse_pdf(content)
    return analyze(stmt.company_name, stmt.sector, stmt.to_statements(), filing)
