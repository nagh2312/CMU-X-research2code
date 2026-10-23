# Research to Learn by Doing

**Branch:** `research-to-learn-by-doing`

Upload a research paper and turn its method into a **hands-on learning experience** — try it, observe what happens, and understand how it works.

This is a separate product surface from Research2Code (paper → code), Research to Simulation (explore behavior), and Research to Research Gap (what to do next). On this branch, the new work lives in:

**[`Research to Learn by Doing/`](./Research%20to%20Learn%20by%20Doing/)**

## Idea

A paper can explain a technique accurately without making it easy to apply. This tool turns the paper’s **core method** into a **guided practical exercise**, not just a summary or quiz.

1. **Upload** a paper with a method you want to understand.
2. **Identify** what the researcher did, the inputs, and how results were produced.
3. **Create** a small hands-on exercise that keeps the core idea.
4. **Try it** — change inputs, complete steps, or run a small example.
5. **Explain** what happened and how it ties back to the paper.
6. **Go further** with a harder example once the basics click.

**Important limitation:** If the paper lacks detail to reproduce the method, the tool uses a **simplified teaching example** and states clearly what was simplified.

## How this differs from the other tools

| Need | Product | Output |
|------|---------|--------|
| **Explore** — what happens when I change something? | Research to Simulation | Interactive environment |
| **Continue** — what should I investigate next? | Research to Research Gap | Evidence-based next steps |
| **Learn** — can I try the method myself? | **Research to Learn by Doing** | Guided exercise + practice |

## Quickstart

```bash
cd "Research to Learn by Doing"
python3 server.py
# default port 8803
```

Open **http://127.0.0.1:8803/**

### Keep products on different servers

| Product | Port | URL |
|---------|------|-----|
| **Research to Learn by Doing** (this branch) | **8803** | **http://127.0.0.1:8803/** |
| Research to Research Gap | 8802 | http://127.0.0.1:8802/ |
| Research to Simulation | 8801 | http://127.0.0.1:8801/ |
| R2C output screen | 8799 | http://127.0.0.1:8799/run/terra-medium |

## What’s in this branch

| Path | Role |
|------|------|
| [`Research to Learn by Doing/README.md`](./Research%20to%20Learn%20by%20Doing/README.md) | Product detail |
| [`Research to Learn by Doing/server.py`](./Research%20to%20Learn%20by%20Doing/server.py) | Local prototype viewer |
| [`Research to Learn by Doing/static/`](./Research%20to%20Learn%20by%20Doing/static/) | Guided exercise UI |
| [`Research to Learn by Doing/demos/`](./Research%20to%20Learn%20by%20Doing/demos/) | Demo lesson packs |
| [`Research to Learn by Doing/lesson.py`](./Research%20to%20Learn%20by%20Doing/lesson.py) | Exercise helpers |
| [`Research to Learn by Doing/test_demo.py`](./Research%20to%20Learn%20by%20Doing/test_demo.py) | Tests + `--demo` CLI |
| Connectors (in UI) | Coursera, edX, Udacity, DeepLearning.AI, … (future) |

## Status

Prototype only. Upload loads a demo lesson pack; live PDF ingest is not wired yet.

---

## Future scope

**Third-party connectors — online study & course platforms.** We can offer options to open related courses and study material so a learner can go from a paper exercise to a matching class or tutorial.

| Connector | Kind of material |
|-----------|------------------|
| **Coursera** | University & industry courses |
| **edX** | University MOOCs |
| **Udacity** | Nanodegrees & tech skills |
| **Khan Academy** | Free foundations |
| **DeepLearning.AI** | ML / DL specializations |
| **Udemy** | Practical skill courses |
| **LinkedIn Learning** | Professional skills |
| **MIT OpenCourseWare** | Free MIT course materials |
| **YouTube Learning** | Video lectures & playlists |
| **Fast.ai** | Practical deep learning |
| **Kaggle Learn** | Short ML micro-courses |
| **Google Skills / Cloud Skills Boost** | Cloud & ML labs |

The prototype already shows a **Connectors** control listing these platforms (live API hooks are future work).
