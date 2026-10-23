# Research to Learn by Doing

> Branch overview: see the repo root [`README.md`](../README.md) on branch `research-to-learn-by-doing`.

Turn a research paper’s method into a **guided, hands-on exercise** so you learn by trying the method — not only by reading it.

## Run the prototype

```bash
python3 server.py
```

Open **http://127.0.0.1:8803/** (separate from Simulation on 8801 and Research Gap on 8802).

Use **Use image-classification lesson** to walk through Upload → Method → Exercise → Try it → Explain → Challenge.

## Tests and CLI demo

```bash
python3 test_demo.py
python3 test_demo.py --demo
```

## Layout

| Path | Role |
|------|------|
| `server.py` | Local viewer (stdlib only), port **8803** |
| `static/` | Guided exercise UI |
| `demos/` | Lesson packs (paper claims vs teaching simplifications) |
| `lesson.py` | Scoring / validation helpers |
| `test_demo.py` | Unit tests and `--demo` |

## What the output shows

- A guided interactive exercise based on the paper  
- A small example “dataset” (feature cards standing in for images)  
- Step-by-step method walkthrough  
- Places to change inputs and run the classifier  
- Feedback on mistakes and how the exercise maps to the paper  
- Clear labels for **from the paper** vs **simplified for teaching**  

## Important limitation

The exercise must reflect the paper’s actual method. When details are missing, the tool builds a simplified teaching example and says what was simplified.

---

## Future scope

**Third-party connectors:** Coursera, edX, Udacity, Khan Academy, DeepLearning.AI, Udemy, LinkedIn Learning, MIT OpenCourseWare, YouTube Learning, Fast.ai, Kaggle Learn, Google Skills / Cloud Skills Boost.

We can offer options like this to access related courses and study material after (or alongside) the guided exercise. The UI includes a **Connectors** button that lists these platforms; live APIs are not wired yet.
