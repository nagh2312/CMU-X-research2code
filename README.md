# Research to Simulation

**Branch:** `research-to-simulation`

Turn a research paper’s method into an **interactive simulation** you can experiment with.

This is a separate product surface from [Research2Code (R2C)](https://github.com/nagh2312/CMU-X-research2code) (paper → working code and other outputs). On this branch, the new work lives in:

**[`Research to Simulation/`](./Research%20to%20Simulation/)**

## Idea

Researchers describe a model, algorithm, or system in a paper, but understanding how it behaves often means reading equations, studying diagrams, and implementing the method yourself. This tool helps you move from reading about a method to experimenting with it.

1. **Upload** a research paper (PDF).
2. **Understand** what can realistically be simulated from the text.
3. **Build** a simple interactive environment that represents the method (not only a summary).
4. **Experiment** — change parameters, inputs, and scenarios.
5. **See results** — visuals plus an explanation tied to the paper, with a clear split between **supported by the paper** and **assumptions we made**.

**Limitation:** Not every paper has enough detail for a faithful simulation. When details are missing, the tool explains what is missing and offers a simplified simulation with assumptions stated plainly.

## Quickstart

```bash
cd "Research to Simulation"
python3 server.py
# default port 8801
```

Open **http://127.0.0.1:8801/**

### Keep the two products on different servers

| Product | Server | URL |
|---------|--------|-----|
| **Research to Simulation** (this branch) | `Research to Simulation/server.py` | **http://127.0.0.1:8801/** |
| **R2C output screen** (Code / Dataset / Experiment / … tabs) | `scripts/r2c_watch.py` | **http://127.0.0.1:8799/run/terra-medium** |

Do not run both on the same port. Example for the R2C output demo:

```bash
python3 scripts/r2c_watch.py --runs-root /tmp/r2c-demo-runs --port 8799
```

Use **Use path-planning demo** (or drop a PDF — the prototype loads the demo method pack) to walk through Upload → Understand → Simulate → Results.

### Demo controls

- Click a free cell → **start**
- Shift-click → **goal**
- Alt-click → toggle **obstacle**
- **Run scenario** → see path, expansions, and a paper-linked explanation

## What’s in this branch

| Path | Role |
|------|------|
| [`Research to Simulation/README.md`](./Research%20to%20Simulation/README.md) | Product detail for this tool |
| [`Research to Simulation/server.py`](./Research%20to%20Simulation/server.py) | Local prototype viewer (stdlib only) |
| [`Research to Simulation/static/`](./Research%20to%20Simulation/static/) | Simulation UI |
| [`Research to Simulation/demos/`](./Research%20to%20Simulation/demos/) | Demo method packs (claims vs assumptions) |
| [`Research to Simulation/planner.py`](./Research%20to%20Simulation/planner.py) | Grid planner used by the demo |
| [`Research to Simulation/test_demo.py`](./Research%20to%20Simulation/test_demo.py) | Unit tests + `python3 test_demo.py --demo` |

The rest of the repository is still the R2C codebase (pipeline, agents, output-screen tabs). For the main R2C README and how to run paper → code, switch to the `main` branch.

## Status

Prototype only. Real paper ingest and multi-method simulation packs are not wired to the R2C agents yet.

---

## Future scope

**Third-party connectors.** We can offer options to connect out to external simulation environments and run (or mirror) the method there — so users pick a target and simulate in that environment, not only in the built-in viewer.

Examples:

| Connector | Kind of environment |
|-----------|---------------------|
| **AutoCAD** | CAD / drafting and geometry |
| **Tinkercad** | Browser CAD / simple 3D design |
| **SimScale** | Cloud CAE (CFD, FEA, thermal) |
| **MATLAB / Simulink** | Models, control, and system simulation |
| **Gazebo** | Robot / world simulation (often with ROS) |
| **Webots** | Robot simulation |
| **Unity** | Interactive 3D / game-engine sims |
| **Unreal Engine** | High-fidelity 3D environments |
| **ANSYS** | Engineering multiphysics |
| **COMSOL Multiphysics** | Physics-based FEM simulation |
| **Blender** | 3D scenes and simple physics |
| **PyBullet / MuJoCo** | Physics engines for robotics & RL |
| **NVIDIA Isaac Sim** | Robotics simulation |
| **OpenModelica** | Modelica-based system simulation |

The prototype already shows a **Connectors** control that lists these options (wiring to real APIs is future work).
