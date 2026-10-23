"""Helpers for Research to Research Gap demos and tests."""

from __future__ import annotations

from typing import Any


REQUIRED_TOP = (
    "id",
    "title",
    "paper",
    "established",
    "gap_assessment",
    "author_future_work",
    "next_steps",
    "evidence_boundaries",
)


def validate_pack(pack: dict[str, Any]) -> list[str]:
    """Return a list of validation problems (empty if OK)."""
    problems: list[str] = []
    for key in REQUIRED_TOP:
        if key not in pack:
            problems.append(f"missing top-level key: {key}")
    ga = pack.get("gap_assessment") or {}
    if "has_clear_gap" not in ga:
        problems.append("gap_assessment.has_clear_gap is required")
    elif ga["has_clear_gap"] and not ga.get("gaps"):
        problems.append("has_clear_gap is true but gaps list is empty")
    elif ga.get("has_clear_gap") is False and ga.get("gaps"):
        problems.append("has_clear_gap is false but gaps were listed (do not invent gaps)")
    for i, step in enumerate(pack.get("next_steps") or []):
        if "priority" not in step or "title" not in step:
            problems.append(f"next_steps[{i}] needs priority and title")
    return problems


def prioritize_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(steps, key=lambda s: (s.get("priority", 99), s.get("title", "")))


def gap_kinds(pack: dict[str, Any]) -> dict[str, int]:
    counts = {"author_acknowledged": 0, "inferred_from_paper": 0, "other": 0}
    for g in (pack.get("gap_assessment") or {}).get("gaps") or []:
        kind = g.get("kind") or "other"
        counts[kind if kind in counts else "other"] += 1
    return counts


def summary_lines(pack: dict[str, Any]) -> list[str]:
    """Short CLI-oriented summary."""
    ga = pack["gap_assessment"]
    lines = [
        pack["title"],
        f"Paper: {pack['paper']['name']}",
        f"Clear gap supported by paper: {'yes' if ga['has_clear_gap'] else 'no'}",
        ga.get("summary") or "",
    ]
    if ga.get("invented_gap_warning"):
        lines.append(f"Warning: {ga['invented_gap_warning']}")
    steps = prioritize_steps(pack.get("next_steps") or [])
    if steps:
        lines.append("Top next step: " + steps[0]["title"])
    return lines


def check_market_credibility(data: dict[str, Any]) -> dict[str, Any]:
    """Check internal consistency of TAM / SAM / SOM inputs.

    This does not verify that a source is factually correct — only whether the
    numbers and metadata look coherent enough to trust as a working estimate.
    """
    issues: list[dict[str, str]] = []
    notes: list[str] = []

    def num(key: str) -> float | None:
        raw = data.get(key)
        if raw is None or raw == "":
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            issues.append({"level": "error", "msg": f"{key.upper()} is not a number."})
            return None

    tam, sam, som = num("tam"), num("sam"), num("som")
    year = data.get("year")
    currency = (data.get("currency") or "").strip()
    method = (data.get("method") or "").strip()

    if tam is None or sam is None or som is None:
        issues.append({"level": "error", "msg": "Enter TAM, SAM, and SOM (all three)."})
    if not currency:
        issues.append({"level": "warn", "msg": "Currency is empty — figures may be incomparable."})
    try:
        y = int(year) if year not in (None, "") else None
    except (TypeError, ValueError):
        y = None
        issues.append({"level": "error", "msg": "Year must be an integer."})
    if y is not None and (y < 1990 or y > 2100):
        issues.append({"level": "warn", "msg": f"Year {y} looks unusual for a market snapshot."})

    if tam is not None and tam < 0:
        issues.append({"level": "error", "msg": "TAM cannot be negative."})
    if sam is not None and sam < 0:
        issues.append({"level": "error", "msg": "SAM cannot be negative."})
    if som is not None and som < 0:
        issues.append({"level": "error", "msg": "SOM cannot be negative."})

    if tam is not None and sam is not None and som is not None and tam >= 0 and sam >= 0 and som >= 0:
        if not (som <= sam <= tam):
            issues.append({
                "level": "error",
                "msg": "Ordering broken: require SOM ≤ SAM ≤ TAM (same units and year).",
            })
        else:
            notes.append("Ordering OK: SOM ≤ SAM ≤ TAM.")
        if tam > 0:
            sam_pct = 100.0 * sam / tam
            som_pct_tam = 100.0 * som / tam
            som_pct_sam = 100.0 * som / sam if sam > 0 else 0.0
            notes.append(f"SAM is {sam_pct:.1f}% of TAM; SOM is {som_pct_sam:.1f}% of SAM ({som_pct_tam:.2f}% of TAM).")
            if sam_pct > 95:
                issues.append({"level": "warn", "msg": "SAM is almost equal to TAM — filters may be missing."})
            if sam_pct < 0.1 and sam > 0:
                issues.append({"level": "warn", "msg": "SAM is a tiny fraction of TAM — confirm the filters."})
            if som_pct_sam > 50:
                issues.append({
                    "level": "warn",
                    "msg": "SOM > 50% of SAM is aggressive for an early product — explain capacity/share assumptions.",
                })
            if som_pct_sam < 0.01 and som > 0:
                issues.append({"level": "warn", "msg": "SOM is a very small slice of SAM — fine if intentional."})

    for label, key in (("TAM", "tam_source"), ("SAM", "sam_source"), ("SOM", "som_source")):
        src = (data.get(key) or "").strip()
        if not src:
            issues.append({"level": "warn", "msg": f"{label} has no source note — credibility is weak without a citation."})
        elif len(src) < 8:
            issues.append({"level": "warn", "msg": f"{label} source is very short — add report name, year, or URL."})

    if method not in ("top_down", "bottom_up", "mixed", ""):
        issues.append({"level": "warn", "msg": f"Unknown method “{method}”."})
    elif method == "top_down":
        notes.append("Top-down: industry TAM → apply segment/region/product filters → SAM → apply share/capacity → SOM.")
    elif method == "bottom_up":
        notes.append("Bottom-up: (# buyers or units) × attach rate × price; roll up to SAM/SOM, then sanity-check against TAM.")
    elif method == "mixed":
        notes.append("Mixed: reconcile top-down and bottom-up; large gaps between them reduce credibility.")

    errors = sum(1 for i in issues if i["level"] == "error")
    warns = sum(1 for i in issues if i["level"] == "warn")
    if errors:
        verdict = "Not credible yet"
        detail = "Fix the errors before treating these figures as a working estimate."
    elif warns:
        verdict = "Partly credible"
        detail = "Numbers may be usable, but address the warnings (sources, aggressive shares, missing filters)."
    else:
        verdict = "Internally credible"
        detail = "Passed consistency checks. Still verify sources outside this tool — a paper alone does not prove market size."

    return {
        "verdict": verdict,
        "detail": detail,
        "errors": errors,
        "warnings": warns,
        "issues": issues,
        "notes": notes,
    }
