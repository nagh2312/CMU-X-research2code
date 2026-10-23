# Research to Research Gap

> Branch overview: see the repo root [`README.md`](../README.md) on branch `research-to-research-gap`.

Turn a research paper into a clear view of **findings, limitations, research gaps, and next steps** — without inventing a gap the paper does not support.

## Idea

Reading the conclusion and future-work section helps, but those parts are often brief or vague. This tool links what the paper establishes to practical follow-on work, and says so when no clear gap is justified.

## Run the prototype

```bash
python3 server.py
```

Open **http://127.0.0.1:8802/** (keep this port separate from Simulation on 8801 and R2C on 8799).

Use **Use autonomous-driving demo** to walk through Upload → Understand → Gaps → Next steps.

## Tests and CLI demo

```bash
python3 test_demo.py
python3 test_demo.py --demo
```

## Layout

| Path | Role |
|------|------|
| `server.py` | Local viewer (stdlib only), port **8802** |
| `static/` | UI |
| `demos/` | Demo paper packs |
| `analyze.py` | Ranking / validation helpers |
| `test_demo.py` | Unit tests and `--demo` |

## Output the tool shows

- Summary of main findings and limitations  
- Potential gaps with supporting passages  
- Authors’ stated future work  
- **Author-acknowledged** vs **inferred from the paper** (never treated as field-wide novelty)  
- Prioritized next steps (what each involves and what it could establish)  
- Suggested experiments when the paper gives enough detail  
- **Adjacency opportunity** — nearby topics to explore without leaving the main theme  
- **TAM / SAM / SOM** — definitions, how they are calculated, and a form to enter known figures and check credibility (ordering, sources, aggressive shares)

## Important limitation

A paper alone cannot prove a gap is new across the entire field. The UI labels evidence from the uploaded paper separately from anything that would need related literature.
