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
