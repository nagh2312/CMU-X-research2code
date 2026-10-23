#!/usr/bin/env python3
"""Tests and a tiny CLI demo for Research to Simulation.

Run tests:
  python3 test_demo.py
  # or: python3 -m unittest test_demo.py -v

Run a one-shot demo printout:
  python3 test_demo.py --demo
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from planner import plan  # noqa: E402


DEMO_PATH = ROOT / "demos" / "path_planning.json"


def load_demo() -> dict:
    return json.loads(DEMO_PATH.read_text(encoding="utf-8"))


class DemoPackTests(unittest.TestCase):
    def test_demo_json_has_required_fields(self):
        demo = load_demo()
        self.assertEqual(demo["id"], "path-planning-demo")
        for key in (
            "title",
            "paper",
            "simulatable",
            "supported_by_paper",
            "assumptions",
            "controls",
            "default_scene",
            "explain_templates",
        ):
            self.assertIn(key, demo)
        self.assertTrue(demo["supported_by_paper"])
        self.assertTrue(demo["assumptions"])
        self.assertIn("missing", demo["simulatable"])

    def test_default_scene_finds_a_path(self):
        demo = load_demo()
        scene = demo["default_scene"]
        ctrl = demo["controls"]
        result = plan(
            width=ctrl["grid_w"],
            height=ctrl["grid_h"],
            start=tuple(scene["start"]),
            goal=tuple(scene["goal"]),
            obstacles=[tuple(o) for o in scene["obstacles"]],
            heuristic=ctrl.get("heuristic", "manhattan"),
            diagonal=bool(ctrl.get("allow_diagonal")),
            step_cost=float(ctrl.get("step_cost", 1)),
        )
        self.assertEqual(result["status"], "found")
        self.assertGreaterEqual(len(result["path"]), 2)
        self.assertEqual(result["path"][0], tuple(scene["start"]))
        self.assertEqual(result["path"][-1], tuple(scene["goal"]))
        for cell in result["path"]:
            self.assertNotIn(cell, {tuple(o) for o in scene["obstacles"]})


class PlannerTests(unittest.TestCase):
    def test_open_corridor(self):
        result = plan(
            width=5,
            height=3,
            start=(0, 1),
            goal=(4, 1),
            obstacles=set(),
            heuristic="manhattan",
        )
        self.assertEqual(result["status"], "found")
        self.assertEqual(result["cost"], 4)

    def test_wall_blocks_path(self):
        # Full vertical wall with no gap.
        obstacles = {(2, 0), (2, 1), (2, 2)}
        result = plan(
            width=5,
            height=3,
            start=(0, 1),
            goal=(4, 1),
            obstacles=obstacles,
            heuristic="none",
        )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["path"], [])

    def test_wall_with_gap(self):
        obstacles = {(2, 0), (2, 2)}  # gap at (2, 1)
        result = plan(
            width=5,
            height=3,
            start=(0, 1),
            goal=(4, 1),
            obstacles=obstacles,
            heuristic="manhattan",
        )
        self.assertEqual(result["status"], "found")
        self.assertIn((2, 1), result["path"])

    def test_trivial_start_equals_goal(self):
        result = plan(
            width=4,
            height=4,
            start=(1, 1),
            goal=(1, 1),
            obstacles=set(),
        )
        self.assertEqual(result["status"], "trivial")

    def test_start_on_obstacle(self):
        result = plan(
            width=4,
            height=4,
            start=(1, 1),
            goal=(3, 3),
            obstacles={(1, 1)},
        )
        self.assertEqual(result["status"], "blocked")
        self.assertIn("obstacle", result.get("note", "").lower())


def print_demo() -> None:
    demo = load_demo()
    scene = demo["default_scene"]
    ctrl = demo["controls"]
    result = plan(
        width=ctrl["grid_w"],
        height=ctrl["grid_h"],
        start=tuple(scene["start"]),
        goal=tuple(scene["goal"]),
        obstacles=[tuple(o) for o in scene["obstacles"]],
        heuristic=ctrl.get("heuristic", "manhattan"),
        diagonal=bool(ctrl.get("allow_diagonal")),
    )
    print("Research to Simulation — path-planning demo")
    print(f"  paper:  {demo['paper']['name']}")
    print(f"  start:  {scene['start']}  goal: {scene['goal']}")
    print(f"  status: {result['status']}")
    print(f"  cost:   {result['cost']}")
    print(f"  steps:  {max(0, len(result['path']) - 1)}")
    print(f"  expanded cells: {len(result['expanded'])}")
    if result["status"] == "found":
        print("  path:", " → ".join(f"({x},{y})" for x, y in result["path"][:8]), "…" if len(result["path"]) > 8 else "")
    print()
    print("Assumptions (not claimed as paper facts):")
    for a in demo["assumptions"][:3]:
        print(f"  - {a}")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        print_demo()
        sys.exit(0)
    unittest.main(verbosity=2, argv=[sys.argv[0]])
