#!/usr/bin/env python3
"""Tests and CLI demo for Research to Research Gap.

  python3 test_demo.py
  python3 test_demo.py --demo
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from analyze import gap_kinds, prioritize_steps, summary_lines, validate_pack  # noqa: E402

DEMOS = ROOT / "demos"


def load(name: str) -> dict:
    return json.loads((DEMOS / name).read_text(encoding="utf-8"))


class PackTests(unittest.TestCase):
    def test_driving_demo_valid_and_has_gap(self):
        pack = load("autonomous_driving_detection.json")
        self.assertEqual(validate_pack(pack), [])
        self.assertTrue(pack["gap_assessment"]["has_clear_gap"])
        self.assertGreaterEqual(len(pack["gap_assessment"]["gaps"]), 1)
        kinds = gap_kinds(pack)
        self.assertGreaterEqual(kinds["author_acknowledged"], 1)
        steps = prioritize_steps(pack["next_steps"])
        self.assertEqual(steps[0]["priority"], 1)
        self.assertIn("rain", pack["established"]["limitations"][1].lower() + pack["gap_assessment"]["gaps"][0]["title"].lower())

    def test_closed_demo_does_not_invent_gap(self):
        pack = load("paper_already_closed.json")
        self.assertEqual(validate_pack(pack), [])
        self.assertFalse(pack["gap_assessment"]["has_clear_gap"])
        self.assertEqual(pack["gap_assessment"]["gaps"], [])
        self.assertTrue(pack["gap_assessment"].get("invented_gap_warning"))

    def test_evidence_boundaries_present(self):
        for name in ("autonomous_driving_detection.json", "paper_already_closed.json"):
            pack = load(name)
            self.assertTrue(pack["evidence_boundaries"]["from_uploaded_paper"])
            self.assertTrue(pack["evidence_boundaries"]["would_need_related_literature"])

    def test_validate_rejects_invented_gaps(self):
        pack = load("paper_already_closed.json")
        pack = json.loads(json.dumps(pack))
        pack["gap_assessment"]["gaps"] = [{"id": "x", "title": "fake"}]
        problems = validate_pack(pack)
        self.assertTrue(any("invent" in p.lower() or "false" in p.lower() for p in problems))


class SummaryTests(unittest.TestCase):
    def test_summary_mentions_gap_status(self):
        lines = summary_lines(load("autonomous_driving_detection.json"))
        self.assertTrue(any("yes" in x.lower() for x in lines))
        lines2 = summary_lines(load("paper_already_closed.json"))
        self.assertTrue(any("no" in x.lower() for x in lines2))


def print_demo() -> None:
    pack = load("autonomous_driving_detection.json")
    print("Research to Research Gap — autonomous-driving demo")
    for line in summary_lines(pack):
        print(f"  {line}")
    print()
    print("Gaps:")
    for g in pack["gap_assessment"]["gaps"]:
        print(f"  [{g['kind']}] {g['title']}")
    print()
    print("Next steps:")
    for s in prioritize_steps(pack["next_steps"]):
        print(f"  {s['priority']}. {s['title']}")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        print_demo()
        sys.exit(0)
    unittest.main(verbosity=2, argv=[sys.argv[0]])
