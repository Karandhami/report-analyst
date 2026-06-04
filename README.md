# Annual Report Analyst

Turns a company filing (10-K / annual report) into a one-page commercial
judgment — the way a diligence analyst or equity researcher would. It extracts
the financials, computes the ratios, benchmarks them against the sector, and
writes a structured memo in which **every qualitative claim is traced to a
specific passage in the source document**.

> **Scope note.** Portfolio-grade, production-*minded*: clean architecture,
> deterministic core, tested, runs offline with no API key. It is a first-read
> accelerator, **not** a substitute for full diligence — see
> [Production hardening path](#production-hardening-path).

---

## The two design decisions that matter

**1. The numbers are never AI-generated.** Every ratio is computed in a pure,
tested function from the supplied financials. The language layer only writes
narrative around fixed figures — the same trust boundary that keeps screening
output honest.

**2. Every qualitative claim is grounded.** When the analyst says "management
flags margin pressure," it retrieves the passage in the filing that supports
it and attaches it as a citation with a similarity score. The UI lets you click
any claim and read the source text. This is how the system proves it isn't
hallucinating — retrieval with **citation faithfulness**, not just generation.

---

## Architecture

```
filing (PDF / text)
      │
   parser ── full text + located sections (MD&A, risk factors, …)
      │
      ├──────────────► RAG retriever (local TF-IDF, upgradeable to embeddings)
      │                      │ grounds each theme in a source passage
financials (supplied)        │
      │                      ▼
  ratio engine ──► benchmark ──► analyzer ──► AnalysisMemo (ratios + judgment + citations)
  (deterministic)  (vs sector)   (assembles)
```

- **`ratios/`** — pure `FinancialStatements -> RatioSet`. The quantitative core.
- **`benchmark/`** — positions ratios against sector norms (relative, not absolute).
- **`rag/`** — chunking + a local TF-IDF retriever that needs no API key; returns
  the supporting passage *and* a similarity score. Architected to swap in a real
  embeddings model when a key is present (graceful upgrade, not a fake fallback).
- **`parsing/`** — PDF (pdfplumber, with scanned-page warnings) and plain-text
  paths; locates filing sections by common headings.
- **`memo/`** — the analyzer: derives strengths/risks from the benchmarked
  numbers and grounds qualitative themes in the narrative.
- **`api/`** — FastAPI service. **`frontend/`** — React research-note dashboard.

---

## Quickstart

### Backend
```bash
pip install -e ".[api,dev]"
pytest                       # 11 tests: ratios, benchmarking, grounding, pipeline
uvicorn reportanalyst.api.main:app --reload --port 8100
```

### Frontend
```bash
cd frontend
npm install
npm run dev                  # http://localhost:5174
```

Click **Analyze sample filing** — it runs the engine on a bundled 10-K excerpt
and returns the financial summary, benchmarked margin chart, strengths/risks,
and the grounded evidence (click a claim to see its source passage).

---

## How the grounding works

The filing narrative is chunked into overlapping word-windows and indexed with
TF-IDF. For each analytical theme (margin, growth, leverage, risk), the system
retrieves the most similar passage and attaches it as a `Citation` with a score.
Claims below a relevance threshold are dropped rather than forced — so a citation
only appears when the filing genuinely supports it.

---

## Production hardening path

| Area | Production requirement |
|---|---|
| Extraction | Reliable financials extraction from arbitrary PDF layouts (here, headline figures are supplied) |
| Retrieval | Embeddings model + vector DB; OCR for scanned filings |
| Benchmarks | Live peer-set computation rather than a curated reference table |
| Review | Human analyst sign-off before any memo informs a decision |

The architecture isolates each of these so they slot in without touching the core.

---

## Project layout

```
src/reportanalyst/
  models/      domain + result types
  parsing/     PDF + text filing parser
  ratios/      deterministic ratio engine (the core)
  benchmark/   sector positioning
  rag/         chunking + grounded retrieval
  memo/        analyzer (assembles the grounded memo)
  api/         FastAPI service
frontend/      React research-note dashboard
data/          sample filing
tests/         ratio + pipeline tests
```
