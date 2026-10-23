# Research to Simulation

> Branch-level overview: see the repo root [`README.md`](../README.md) on branch `research-to-simulation`.

Turn a research paper's method into an **interactive simulation** you can experiment with — a different product surface from Research2Code's code / dataset / evidence tabs.

## Idea

Researchers describe a model, algorithm, or system in a paper. Understanding how it behaves often means reading equations, studying diagrams, and implementing the method yourself. This tool helps you move from *reading* a method to *experimenting* with it.

**Flow**

1. **Upload** a research paper (PDF).
2. **Understand** what can realistically be simulated from the text.
3. **Build** a simple interactive environment that represents the method (not just a summary).
4. **Experiment** — change parameters, inputs, and scenarios.
5. **See results** — visuals plus an explanation tied back to the paper, with a clear split between **supported by the paper** and **assumptions we made**.

**Limitation:** Not every paper has enough detail for a faithful simulation. When details are missing, the tool says what is missing and offers a simplified simulation with assumptions stated plainly.

## Run the prototype

From this folder:

```bash
python3 server.py
```

Then open **http://127.0.0.1:8801/**

The demo uses a path-planning style method (the example in the product brief): change start, goal, and obstacles and watch how the planner responds.

## Tests and CLI demo

```bash
# unit tests (demo pack + planner)
python3 test_demo.py

# print one run of the default scene
python3 test_demo.py --demo
```

## Layout

| Path | Role |
|------|------|
| `server.py` | Local viewer (stdlib only) |
| `static/` | Simulation UI |
| `demos/` | Demo method packs (paper claims vs assumptions) |
| `planner.py` | Grid path planner (shared with tests) |
| `test_demo.py` | Unit tests and `--demo` CLI |

This folder is intentionally separate from the main R2C pipeline viewer so the simulation output screen can evolve on its own.
