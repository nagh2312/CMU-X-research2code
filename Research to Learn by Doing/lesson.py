"""Helpers for Research to Learn by Doing lessons and tests."""

from __future__ import annotations

import math
from typing import Any


REQUIRED_TOP = (
    "id",
    "title",
    "paper",
    "core_method",
    "teaching_simplifications",
    "exercise",
    "explanations",
    "evidence_boundaries",
)


def validate_lesson(pack: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    for key in REQUIRED_TOP:
        if key not in pack:
            problems.append(f"missing top-level key: {key}")
    ex = pack.get("exercise") or {}
    if not ex.get("classes"):
        problems.append("exercise.classes is required")
    if not ex.get("samples"):
        problems.append("exercise.samples is required")
    if not pack.get("teaching_simplifications"):
        problems.append("teaching_simplifications must list what was simplified")
    return problems


def distance(a: list[float], b: list[float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def predict(features: list[float], classes: list[dict[str, Any]]) -> dict[str, Any]:
    """Nearest class prototype (1-NN to centers)."""
    best = None
    best_d = float("inf")
    detail = []
    for c in classes:
        d = distance(features, c["prototype"])
        detail.append({"class_id": c["id"], "name": c["name"], "distance": round(d, 3)})
        if d < best_d:
            best_d = d
            best = c
    return {
        "predicted": best["id"] if best else None,
        "predicted_name": best["name"] if best else None,
        "distance": round(best_d, 3) if best else None,
        "detail": sorted(detail, key=lambda x: x["distance"]),
    }


def run_all(pack: dict[str, Any], overrides: dict[str, list[float]] | None = None) -> dict[str, Any]:
    """Score every sample; optional feature overrides by sample id."""
    overrides = overrides or {}
    classes = pack["exercise"]["classes"]
    rows = []
    correct = 0
    for s in pack["exercise"]["samples"]:
        feats = list(overrides.get(s["id"], s["features"]))
        pred = predict(feats, classes)
        ok = pred["predicted"] == s["label"]
        if ok:
            correct += 1
        rows.append({
            "id": s["id"],
            "true_label": s["label"],
            "features": feats,
            "predicted": pred["predicted"],
            "correct": ok,
            "distances": pred["detail"],
        })
    n = len(rows) or 1
    return {
        "rows": rows,
        "correct": correct,
        "total": len(rows),
        "accuracy": round(correct / n, 3),
    }
