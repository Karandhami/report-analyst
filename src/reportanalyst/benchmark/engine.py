"""Sector benchmarking.

Positions a company's ratios against representative sector norms, so the
analysis reads relatively ("margins are strong for this sector") rather than
in the abstract. The benchmark table is a small curated dataset of typical
mid-point values — clearly an approximation, and labelled as such in output.

A production version would source these from a peer set computed live; here
they are reasonable, documented reference points that make the comparison
meaningful for a demo.
"""

from __future__ import annotations

from decimal import Decimal

from reportanalyst.models.domain import RatioSet, Sector

# Representative sector mid-points. Margins/returns as fractions; ratios as x.
# Documented reference values — not authoritative, used for relative framing.
_BENCHMARKS: dict[Sector, dict[str, Decimal]] = {
    Sector.technology: {
        "gross_margin": Decimal("0.65"),
        "operating_margin": Decimal("0.20"),
        "net_margin": Decimal("0.15"),
        "ebitda_margin": Decimal("0.25"),
        "debt_to_equity": Decimal("0.4"),
        "return_on_equity": Decimal("0.18"),
    },
    Sector.healthcare: {
        "gross_margin": Decimal("0.55"),
        "operating_margin": Decimal("0.15"),
        "net_margin": Decimal("0.10"),
        "ebitda_margin": Decimal("0.20"),
        "debt_to_equity": Decimal("0.6"),
        "return_on_equity": Decimal("0.14"),
    },
    Sector.industrials: {
        "gross_margin": Decimal("0.30"),
        "operating_margin": Decimal("0.12"),
        "net_margin": Decimal("0.08"),
        "ebitda_margin": Decimal("0.16"),
        "debt_to_equity": Decimal("0.8"),
        "return_on_equity": Decimal("0.13"),
    },
    Sector.consumer: {
        "gross_margin": Decimal("0.38"),
        "operating_margin": Decimal("0.10"),
        "net_margin": Decimal("0.07"),
        "ebitda_margin": Decimal("0.13"),
        "debt_to_equity": Decimal("0.7"),
        "return_on_equity": Decimal("0.15"),
    },
}


def benchmark(ratios: RatioSet, sector: Sector) -> dict[str, dict]:
    """Compare each available ratio to the sector norm.

    Returns {ratio_name: {value, norm, verdict}} where verdict is
    'above' / 'in_line' / 'below' (within +-15% counts as in line).
    """
    norms = _BENCHMARKS.get(sector, {})
    out: dict[str, dict] = {}
    values = ratios.model_dump()
    for name, norm in norms.items():
        val = values.get(name)
        if val is None:
            continue
        val = Decimal(str(val))
        band = norm * Decimal("0.15")
        if val > norm + band:
            verdict = "above"
        elif val < norm - band:
            verdict = "below"
        else:
            verdict = "in_line"
        out[name] = {"value": val, "norm": norm, "verdict": verdict}
    return out
