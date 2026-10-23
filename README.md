# Research to Research Gap

**Branch:** `research-to-research-gap`

Upload a research paper and find out **what remains unresolved**, whether a **genuine research gap** exists, and **what to do next**.

This is a separate product surface from [Research2Code](https://github.com/nagh2312/CMU-X-research2code) (paper → code) and from Research to Simulation. On this branch, the new work lives in:

**[`Research to Research Gap/`](./Research%20to%20Research%20Gap/)**

## Idea

Conclusions and future-work sections are often brief or hard to turn into a plan. This tool connects findings, limitations, and future scope to **actionable next steps** — and says clearly when the paper does **not** support inventing a gap.

1. **Upload** a paper you want to build on.
2. **Understand** what it establishes (question, method, findings, limitations, conclusions).
3. **Check for a research gap** — unanswered questions, addressable limitations, under-evaluated claims.
4. **Avoid inventing a gap** if the paper does not support one.
5. **Explore future scope** the authors already stated.
6. **Suggest concrete next steps** — extensions, experiments, alternatives, new conditions.
7. **Adjacency opportunity** — what else is close to the topic (without going far), plus **TAM / SAM / SOM** sizing with a credibility check on numbers you enter.

**Important limitation:** A single paper cannot prove a gap is new across the whole field. Evidence from the uploaded paper is kept separate from anything that would need related literature. Market figures are not in the paper; the tool only checks internal consistency of what you paste in.

## Quickstart

```bash
cd "Research to Research Gap"
python3 server.py
# default port 8802
```

Open **http://127.0.0.1:8802/**

### Keep products on different servers

| Product | Port | URL |
|---------|------|-----|
| **Research to Research Gap** (this branch) | **8802** | **http://127.0.0.1:8802/** |
| Research to Simulation | 8801 | http://127.0.0.1:8801/ |
| R2C output screen | 8799 | http://127.0.0.1:8799/run/terra-medium |

## What’s in this branch

| Path | Role |
|------|------|
| [`Research to Research Gap/README.md`](./Research%20to%20Research%20Gap/README.md) | Product detail |
| [`Research to Research Gap/server.py`](./Research%20to%20Research%20Gap/server.py) | Local prototype viewer |
| [`Research to Research Gap/static/`](./Research%20to%20Research%20Gap/static/) | UI |
| [`Research to Research Gap/demos/`](./Research%20to%20Research%20Gap/demos/) | Demo paper packs |
| [`Research to Research Gap/analyze.py`](./Research%20to%20Research%20Gap/analyze.py) | Gap / next-step helpers |
| [`Research to Research Gap/test_demo.py`](./Research%20to%20Research%20Gap/test_demo.py) | Tests + `--demo` CLI |

## Status

Prototype only. Upload loads a demo method pack; live PDF ingest and literature search are not wired yet.
