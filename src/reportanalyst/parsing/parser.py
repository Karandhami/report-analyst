"""Filing parser — extract text and narrative sections from a report.

Two entry points:
  - parse_pdf(bytes): real-world path, uses pdfplumber to pull text page by
    page. Handles native-text PDFs; scanned-only pages return empty text and
    are flagged (a production version would OCR them).
  - parse_text(str): a plain-text path, so the full pipeline is testable and
    runnable without a binary PDF.

The parser separates two things the downstream layers need:
  - `full_text` / page map  -> fed to the retriever for grounding.
  - `sections`              -> named narrative blocks (MD&A, risk factors)
    located by common filing headings, used to focus retrieval.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

# Common headings in 10-Ks / annual reports, used to locate narrative sections.
_SECTION_PATTERNS = {
    "business": r"item\s*1[^0-9a-z].{0,30}business",
    "risk_factors": r"item\s*1a.{0,30}risk\s*factors",
    "mdna": r"management.s\s*discussion\s*and\s*analysis",
    "outlook": r"\boutlook\b|forward.looking",
}


@dataclass
class ParsedFiling:
    full_text: str
    pages: list[str] = field(default_factory=list)
    sections: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def page_of(self, snippet: str) -> int | None:
        """Best-effort: which page a snippet came from (1-indexed)."""
        head = snippet[:60]
        for i, page in enumerate(self.pages):
            if head and head in page:
                return i + 1
        return None


def _locate_sections(text: str) -> dict[str, str]:
    lowered = text.lower()
    found: dict[str, int] = {}
    for name, pat in _SECTION_PATTERNS.items():
        m = re.search(pat, lowered)
        if m:
            found[name] = m.start()
    # Slice each section from its start to the next section's start.
    ordered = sorted(found.items(), key=lambda kv: kv[1])
    sections: dict[str, str] = {}
    for idx, (name, start) in enumerate(ordered):
        end = ordered[idx + 1][1] if idx + 1 < len(ordered) else len(text)
        sections[name] = text[start:end].strip()
    return sections


def parse_text(text: str) -> ParsedFiling:
    pages = text.split("\f") if "\f" in text else [text]
    return ParsedFiling(
        full_text=text,
        pages=pages,
        sections=_locate_sections(text),
    )


def parse_pdf(content: bytes) -> ParsedFiling:
    try:
        import pdfplumber
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("pdfplumber not installed; install the 'parse' extra") from e

    pages: list[str] = []
    warnings: list[str] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for i, page in enumerate(pdf.pages):
            txt = page.extract_text() or ""
            if not txt.strip():
                warnings.append(f"page {i + 1} had no extractable text (possibly scanned)")
            pages.append(txt)
    full = "\n".join(pages)
    pf = ParsedFiling(full_text=full, pages=pages, sections=_locate_sections(full))
    pf.warnings = warnings
    return pf
