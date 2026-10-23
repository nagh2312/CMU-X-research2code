"""Grid path planner used by the Research to Simulation demo and tests."""

from __future__ import annotations

import heapq
import math
from typing import Iterable


def _key(x: int, y: int) -> tuple[int, int]:
    return (x, y)


def _heuristic(a: tuple[int, int], b: tuple[int, int], mode: str) -> float:
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    if mode == "none":
        return 0.0
    if mode == "euclidean":
        return math.hypot(dx, dy)
    return float(dx + dy)  # manhattan


def _neighbors(
    x: int, y: int, width: int, height: int, diagonal: bool
) -> Iterable[tuple[int, int, float]]:
    steps = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0)]
    if diagonal:
        root = math.sqrt(2.0)
        steps.extend([(1, 1, root), (1, -1, root), (-1, 1, root), (-1, -1, root)])
    for dx, dy, cost in steps:
        nx, ny = x + dx, y + dy
        if 0 <= nx < width and 0 <= ny < height:
            yield nx, ny, cost


def plan(
    *,
    width: int,
    height: int,
    start: tuple[int, int],
    goal: tuple[int, int],
    obstacles: set[tuple[int, int]] | Iterable[tuple[int, int]],
    heuristic: str = "manhattan",
    diagonal: bool = False,
    step_cost: float = 1.0,
) -> dict:
    """A* / Dijkstra-style search. Returns status, path, cost, and expanded cells."""
    blocked = set(map(tuple, obstacles))
    start, goal = tuple(start), tuple(goal)

    if start == goal:
        return {"status": "trivial", "path": [start], "expanded": [], "cost": 0.0}

    if start in blocked or goal in blocked:
        return {
            "status": "blocked",
            "path": [],
            "expanded": [],
            "cost": None,
            "note": "Start or goal sits on an obstacle.",
        }

    open_heap: list[tuple[float, int, tuple[int, int]]] = []
    tie = 0
    g_score = {start: 0.0}
    came: dict[tuple[int, int], tuple[int, int]] = {}
    heapq.heappush(open_heap, (_heuristic(start, goal, heuristic), tie, start))
    open_set = {start}
    expanded: list[tuple[int, int]] = []

    while open_heap:
        _, _, current = heapq.heappop(open_heap)
        if current not in open_set:
            continue
        open_set.remove(current)
        expanded.append(current)

        if current == goal:
            path = [current]
            while current in came:
                current = came[current]
                path.append(current)
            path.reverse()
            return {
                "status": "found",
                "path": path,
                "expanded": expanded,
                "cost": g_score[goal],
            }

        cx, cy = current
        for nx, ny, move_cost in _neighbors(cx, cy, width, height, diagonal):
            nxt = _key(nx, ny)
            if nxt in blocked:
                continue
            tentative = g_score[current] + move_cost * step_cost
            if tentative < g_score.get(nxt, float("inf")):
                came[nxt] = current
                g_score[nxt] = tentative
                tie += 1
                f = tentative + _heuristic(nxt, goal, heuristic)
                heapq.heappush(open_heap, (f, tie, nxt))
                open_set.add(nxt)

    return {"status": "blocked", "path": [], "expanded": expanded, "cost": None}
