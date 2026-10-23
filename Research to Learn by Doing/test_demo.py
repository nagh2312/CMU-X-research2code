#!/usr/bin/env python3
"""Tests and CLI demo for Research to Learn by Doing.

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

from lesson import predict, run_all, validate_lesson  # noqa: E402

DEMO = ROOT / "demos" / "image_classification_lesson.json"


def load() -> dict:
    return json.loads(DEMO.read_text(encoding="utf-8"))


class LessonPackTests(unittest.TestCase):
    def test_pack_valid(self):
        pack = load()
        self.assertEqual(validate_lesson(pack), [])
        self.assertTrue(pack["teaching_simplifications"])
        self.assertGreaterEqual(len(pack["exercise"]["samples"]), 4)

    def test_default_run_mostly_correct(self):
        pack = load()
        result = run_all(pack)
        self.assertEqual(result["total"], len(pack["exercise"]["samples"]))
        self.assertGreaterEqual(result["correct"], result["total"] - 2)

    def test_predict_nearest_prototype(self):
        pack = load()
        classes = pack["exercise"]["classes"]
        # Exactly on class A prototype
        pred = predict([8.0, 2.0], classes)
        self.assertEqual(pred["predicted"], "A")

    def test_challenge_sample_exists(self):
        pack = load()
        sid = pack["challenge"]["sample_id"]
        ids = {s["id"] for s in pack["exercise"]["samples"]}
        self.assertIn(sid, ids)

    def test_evidence_boundaries(self):
        pack = load()
        self.assertTrue(pack["evidence_boundaries"]["from_paper"])
        self.assertTrue(pack["evidence_boundaries"]["simplified_for_teaching"])


def print_demo() -> None:
    pack = load()
    result = run_all(pack)
    print("Research to Learn by Doing — image-classification lesson")
    print(f"  paper: {pack['paper']['name']}")
    print(f"  accuracy on demo set: {result['correct']}/{result['total']} ({result['accuracy']})")
    print("  simplifications:")
    for s in pack["teaching_simplifications"][:3]:
        print(f"    - {s}")
    miss = [r for r in result["rows"] if not r["correct"]]
    if miss:
        print("  misses:", ", ".join(r["id"] for r in miss))
    else:
        print("  misses: none")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        print_demo()
        sys.exit(0)
    unittest.main(verbosity=2, argv=[sys.argv[0]])
