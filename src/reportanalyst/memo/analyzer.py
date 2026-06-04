"""The analyzer — turns statements + narrative into a grounded memo.

Flow:
  1. Compute ratios deterministically.
  2. Benchmark them against the sector.
  3. Derive strengths/risks from the *benchmarked numbers* (rule-based, so the
     judgments trace to data, not to an LLM).
  4. For each qualitative theme, retrieve a supporting passage from the filing
     narrative and attach it as a Citation — this is the grounding step.
  5. Assemble the memo, recording any data caveats.

The narrative prose can be produced by a template (offline) or, if a model
client is provided, by an LLM that receives the structured findings and is
forbidden from inventing numbers — same trust boundary as the scoring project.
"""

from __future__ import annotations

from decimal import Decimal

from reportanalyst.benchmark.engine import benchmark
from reportanalyst.models.domain import (
    AnalysisMemo,
    BenchmarkEntry,
    Citation,
    FinancialStatements,
    RatioSet,
    Sector,
)
from reportanalyst.parsing.parser import ParsedFiling
from reportanalyst.rag.retriever import Chunk, TfidfRetriever, chunk_text, split_sentences
from reportanalyst.ratios.engine import compute_ratios, list_missing

# Themes we look to ground in the narrative, with the query used to find them.
_THEMES = {
    "margin": "margin pressure cost inflation pricing gross margin",
    "growth": "revenue growth demand expansion new customers",
    "leverage": "debt leverage borrowings credit facility interest",
    "risk": "risk factors competition regulatory uncertainty",
}


def _pct(v: Decimal | None) -> str:
    return "n/a" if v is None else f"{v * 100:.1f}%"


def _derive_strengths_risks(
    ratios: RatioSet, bench: dict[str, dict]
) -> tuple[list[str], list[str]]:
    strengths, risks = [], []
    for name, info in bench.items():
        label = name.replace("_", " ")
        if info["verdict"] == "above" and name != "debt_to_equity":
            strengths.append(
                f"{label} above sector norm ({_pct(info['value'])} vs {_pct(info['norm'])})"
            )
        elif info["verdict"] == "below" and name != "debt_to_equity":
            risks.append(
                f"{label} below sector norm ({_pct(info['value'])} vs {_pct(info['norm'])})"
            )
    if ratios.net_leverage is not None and ratios.net_leverage > Decimal("3"):
        risks.append(f"elevated net leverage at {ratios.net_leverage:.1f}x")
    if ratios.interest_coverage is not None and ratios.interest_coverage < Decimal("3"):
        risks.append(f"thin interest coverage at {ratios.interest_coverage:.1f}x")
    return strengths, risks


def _best_sentence(chunk_text_str: str, query: str) -> tuple[str, float] | None:
    """Pick the single sentence in a chunk that best matches the query.

    Returns (sentence, score) or None. Scoring the *sentence* (not the whole
    chunk) avoids surfacing a heading or company name that happened to sit at
    the start of an otherwise-relevant chunk.
    """
    sentences = split_sentences(chunk_text_str)
    if not sentences:
        return None
    scored = TfidfRetriever([Chunk(text=s) for s in sentences])
    hits = scored.retrieve(query, k=1)
    if not hits:
        return None
    chunk, score = hits[0]
    return chunk.text, score


# A citation must clear this to be shown. Below it, the match is too weak to
# count as evidence, so we omit the theme rather than quote something irrelevant.
_MIN_RELEVANCE = 0.12


def _ground_themes(filing: ParsedFiling) -> list[Citation]:
    """Retrieve a supporting passage for each theme genuinely present in the text.

    Two-stage retrieval: find the most relevant chunk, then the most relevant
    *sentence* within it. A theme is only cited if that sentence clears the
    relevance bar — so a weak or absent theme produces no citation rather than
    a misleading one.
    """
    chunks = chunk_text(filing.full_text)
    if not chunks:
        return []
    retriever = TfidfRetriever(chunks)
    citations: list[Citation] = []
    for theme, query in _THEMES.items():
        hits = retriever.retrieve(query, k=2)
        best_passage, best_score = None, 0.0
        for chunk, _ in hits:
            result = _best_sentence(chunk.text, query)
            if result and result[1] > best_score:
                best_passage, best_score = result[0], result[1]
        if best_passage is None or best_score < _MIN_RELEVANCE:
            continue  # no genuinely relevant passage for this theme
        citations.append(
            Citation(
                claim=f"{theme} (grounded)",
                source_text=best_passage,
                page=filing.page_of(best_passage),
                score=round(best_score, 3),
            )
        )
    return citations


def analyze(
    company_name: str,
    sector: Sector,
    statements: FinancialStatements,
    filing: ParsedFiling | None = None,
) -> AnalysisMemo:
    ratios = compute_ratios(statements)
    bench = benchmark(ratios, sector)
    strengths, risks = _derive_strengths_risks(ratios, bench)
    citations = _ground_themes(filing) if filing else []
    caveats = []
    missing = list_missing(ratios)
    if missing:
        caveats.append("Ratios not computable from the filing: " + ", ".join(missing))

    narrative = _template_narrative(company_name, sector, ratios, strengths, risks)

    # Build benchmark entries for the visual comparison.
    bench_entries = [
        BenchmarkEntry(
            name=name.replace("_", " "),
            value=float(info["value"]),
            norm=float(info["norm"]),
            verdict=info["verdict"],
        )
        for name, info in bench.items()
    ]

    return AnalysisMemo(
        company_name=company_name,
        sector=sector,
        fiscal_year=statements.fiscal_year,
        ratios=ratios,
        strengths=strengths,
        risks=risks,
        narrative=narrative,
        citations=citations,
        data_caveats=caveats,
        benchmarks=bench_entries,
        health_score=_health_score(ratios, bench),
    )


def _health_score(ratios: RatioSet, bench: dict[str, dict]) -> float | None:
    """A transparent 0..100 composite: how many benchmarked ratios beat/meet
    their sector norm, lightly penalised for leverage and coverage stress.

    Deliberately simple and explainable — not a black box. None if there is
    nothing to score.
    """
    if not bench:
        return None
    points, total = 0.0, 0.0
    for name, info in bench.items():
        total += 1
        # debt_to_equity: lower is better, so 'below' norm is good.
        good = info["verdict"] == ("below" if name == "debt_to_equity" else "above")
        if good:
            points += 1.0
        elif info["verdict"] == "in_line":
            points += 0.6
    score = (points / total) * 100 if total else 50.0
    # Stress penalties.
    if ratios.net_leverage is not None and ratios.net_leverage > Decimal("3"):
        score -= 12
    if ratios.interest_coverage is not None and ratios.interest_coverage < Decimal("3"):
        score -= 12
    return round(max(0.0, min(100.0, score)), 1)


def _template_narrative(
    name: str, sector: Sector, ratios: RatioSet, strengths: list[str], risks: list[str]
) -> str:
    parts = [
        f"{name} ({sector.value}) shows an operating margin of "
        f"{_pct(ratios.operating_margin)} and a net margin of {_pct(ratios.net_margin)}."
    ]
    if strengths:
        parts.append("Relative strengths: " + "; ".join(strengths) + ".")
    if risks:
        parts.append("Areas of concern: " + "; ".join(risks) + ".")
    else:
        parts.append("No threshold-level risks flagged on the available ratios.")
    return " ".join(parts)
