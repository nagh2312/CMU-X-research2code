"""Read-only builders for the output screen's extra tabs (everything except Code).

Each `build_<tab>(run_dir)` turns files a finished run already wrote into one
JSON payload for the viewer. Nothing here dispatches agents or touches the
delivered package; the only writes are the knowledge-graph selection and the
output-screen job state, both under `<run>/.pipeline/ui/`.

Standard library only: the viewer is launched with a bare `python3` that may
not have numpy, so the pipeline's own parsers are imported lazily.
"""

from __future__ import annotations

import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path

import run_layout

UI_DIRNAME = "ui"
TABS = ("dataset", "experiment", "decision", "teaching", "graph", "evidence")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path | None):
    if path is None:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _pipeline(run_dir: Path, name: str):
    return _load_json(run_dir / ".pipeline" / name)


def ui_dir(run_dir: Path) -> Path:
    return run_dir / ".pipeline" / UI_DIRNAME


def _paper_title(run_dir: Path) -> str:
    spec = _pipeline(run_dir, "method_spec.json") or {}
    paper_map = _pipeline(run_dir, "paper_map.json") or {}
    return ((spec.get("paper") or {}).get("title") or paper_map.get("title") or run_dir.name)


def _paradigm(run_dir: Path) -> str:
    ledger = _pipeline(run_dir, "claims_ledger.json") or {}
    if ledger.get("paradigm"):
        return str(ledger["paradigm"])
    spec = _pipeline(run_dir, "method_spec.json") or {}
    return str(((spec.get("comparison") or {}).get("classification") or {}).get("id") or "")


def _elements(run_dir: Path) -> list[dict]:
    paper_map = _pipeline(run_dir, "paper_map.json") or {}
    return [e for e in paper_map.get("elements") or [] if isinstance(e, dict) and e.get("id")]


def _manifest(run_dir: Path) -> dict:
    path = run_layout.resolve_existing(run_dir, run_layout.FINAL_MANIFEST_JSON)
    return _load_json(path) or {}


def _require(value, what: str):
    if not value:
        raise LookupError(f"This run has no {what} yet, so this tab cannot be built.")
    return value


def build(tab: str, run_dir: Path) -> dict:
    builders = {
        "dataset": build_dataset,
        "experiment": build_experiment,
        "decision": build_decision,
        "teaching": build_teaching,
        "graph": build_graph,
        "evidence": build_evidence,
    }
    builder = builders.get(tab)
    if builder is None:
        raise KeyError(tab)
    return builder(run_dir)


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

# Well-known public datasets. Sizes are the official archive sizes; `files`
# are the anonymous download URLs the official pages point to.
KNOWN_DATASETS = {
    "mnist": {
        "name": "MNIST",
        "source": "https://yann.lecun.com/exdb/mnist/",
        "size": "70,000 images (60,000 train / 10,000 test), about 11 MB compressed",
        "format": "IDX binary files (gzip), 28x28 grayscale images",
        "files": [
            "https://ossci-datasets.s3.amazonaws.com/mnist/train-images-idx3-ubyte.gz",
            "https://ossci-datasets.s3.amazonaws.com/mnist/train-labels-idx1-ubyte.gz",
            "https://ossci-datasets.s3.amazonaws.com/mnist/t10k-images-idx3-ubyte.gz",
            "https://ossci-datasets.s3.amazonaws.com/mnist/t10k-labels-idx1-ubyte.gz",
        ],
        "schema": [
            ("image", "28x28 grayscale pixels, values 0 to 255"),
            ("label", "The handwritten digit shown, an integer 0 to 9"),
        ],
    },
    "fashion-mnist": {
        "name": "Fashion-MNIST",
        "source": "https://github.com/zalandoresearch/fashion-mnist",
        "size": "70,000 images (60,000 train / 10,000 test), about 30 MB compressed",
        "format": "IDX binary files (gzip), 28x28 grayscale images",
        "files": [
            "http://fashion-mnist.s3-website.eu-central-1.amazonaws.com/train-images-idx3-ubyte.gz",
            "http://fashion-mnist.s3-website.eu-central-1.amazonaws.com/train-labels-idx1-ubyte.gz",
            "http://fashion-mnist.s3-website.eu-central-1.amazonaws.com/t10k-images-idx3-ubyte.gz",
            "http://fashion-mnist.s3-website.eu-central-1.amazonaws.com/t10k-labels-idx1-ubyte.gz",
        ],
        "schema": [
            ("image", "28x28 grayscale pixels, values 0 to 255"),
            ("label", "Clothing category, an integer 0 to 9"),
        ],
    },
    "cifar-10": {
        "name": "CIFAR-10",
        "source": "https://www.cs.toronto.edu/~kriz/cifar.html",
        "size": "60,000 images (50,000 train / 10,000 test), about 163 MB",
        "format": "Python pickle batches in a tar.gz, 32x32 colour images",
        "files": ["https://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz"],
        "schema": [
            ("image", "32x32 RGB pixels, values 0 to 255"),
            ("label", "Object class, an integer 0 to 9"),
        ],
    },
    "cifar-100": {
        "name": "CIFAR-100",
        "source": "https://www.cs.toronto.edu/~kriz/cifar.html",
        "size": "60,000 images (50,000 train / 10,000 test), about 161 MB",
        "format": "Python pickle batches in a tar.gz, 32x32 colour images",
        "files": ["https://www.cs.toronto.edu/~kriz/cifar-100-python.tar.gz"],
        "schema": [
            ("image", "32x32 RGB pixels, values 0 to 255"),
            ("fine_label", "Fine object class, an integer 0 to 99"),
            ("coarse_label", "Superclass, an integer 0 to 19"),
        ],
    },
    "svhn": {
        "name": "SVHN (Street View House Numbers)",
        "source": "http://ufldl.stanford.edu/housenumbers/",
        "size": "99,289 digit crops (73,257 train / 26,032 test), about 182 MB",
        "format": "MATLAB .mat files, 32x32 colour digit crops",
        "files": [
            "http://ufldl.stanford.edu/housenumbers/train_32x32.mat",
            "http://ufldl.stanford.edu/housenumbers/test_32x32.mat",
        ],
        "schema": [
            ("X", "32x32 RGB pixels of a cropped house-number digit"),
            ("y", "The digit shown, 1 to 10 (10 means the digit 0)"),
        ],
    },
}

_KNOWN_ALIASES = {
    "mnist": "mnist", "fashion-mnist": "fashion-mnist", "fashionmnist": "fashion-mnist",
    "cifar-10": "cifar-10", "cifar10": "cifar-10", "cifar-100": "cifar-100",
    "cifar100": "cifar-100", "svhn": "svhn",
}

_OPENML_RE = re.compile(r"openml\D*(\d+)", re.IGNORECASE)


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "dataset"


def _match_known(name: str) -> str | None:
    key = re.sub(r"\s+", "", name.lower())
    for alias, canonical in _KNOWN_ALIASES.items():
        if key == alias or key.startswith(alias + "(") or key == alias.replace("-", ""):
            return canonical
    return None


def _paper_text(run_dir: Path) -> str:
    try:
        return (run_dir / ".pipeline" / "paper.md").read_text(encoding="utf-8")
    except OSError:
        return ""


def dataset_entries(run_dir: Path) -> list[dict]:
    """Every dataset the paper names, plus data links the paper itself cites."""
    spec = _pipeline(run_dir, "method_spec.json") or {}
    data_req = spec.get("data_requirements") or {}
    entries: list[dict] = []
    seen: set[str] = set()

    for raw in data_req.get("example_datasets") or []:
        name = str(raw).strip()
        if not name:
            continue
        known = _match_known(name)
        openml = _OPENML_RE.search(name)
        if known:
            info = KNOWN_DATASETS[known]
            entry = {
                "id": known, "name": info["name"], "availability": "public",
                "source": info["source"], "size": info["size"], "format": info["format"],
                "download_urls": list(info["files"]), "fetchable": True,
                "schema": [{"field": f, "meaning": m} for f, m in info["schema"]],
                "schema_origin": "Official dataset documentation",
            }
        elif openml:
            did = openml.group(1)
            entry = {
                "id": f"openml-{did}", "name": name, "availability": "public",
                "source": f"https://www.openml.org/d/{did}",
                "size": "Listed on the OpenML page", "format": "ARFF / CSV table on OpenML",
                "download_urls": [f"https://www.openml.org/d/{did}"], "fetchable": False,
                "fetch_note": "Open the OpenML page to download; automatic fetch is not set up for OpenML.",
                "schema": None, "schema_origin": None,
            }
        else:
            entry = {
                "id": _slugify(name), "name": name, "availability": "not_found",
                "source": None, "size": None, "format": None, "download_urls": [],
                "fetchable": False, "schema": None, "schema_origin": None,
            }
        if entry["id"] in seen:
            continue
        seen.add(entry["id"])
        entries.append(entry)

    # Links on whitelisted data hosts that appear verbatim in the paper text.
    try:
        from dataset_acquisition import candidate_sources
        cited = candidate_sources(_paper_text(run_dir))
    except Exception:
        cited = []
    for source in cited:
        did = "cited-" + _slugify(source.download_url)[-40:]
        if did in seen:
            continue
        seen.add(did)
        entries.append({
            "id": did, "name": f"Data link cited in the paper ({source.host})",
            "availability": "needs_login" if source.credentialed else "public",
            "source": source.cited_url, "size": "Unknown until fetched", "format": "Unknown until fetched",
            "download_urls": [source.download_url], "fetchable": not source.credentialed,
            "fetch_note": "This host needs a login, so it cannot be fetched automatically." if source.credentialed else None,
            "schema": None, "schema_origin": None,
        })
    return entries


def _paper_schema(spec: dict) -> list[dict]:
    """Schema built from the method analysis of the paper text."""
    rows: list[dict] = []
    for item in (spec.get("try_it_out") or {}).get("user_provides") or []:
        if isinstance(item, dict) and item.get("type") == "data":
            rows.append({"field": item.get("name") or "data", "meaning": item.get("description") or ""})
    fmt = (spec.get("data_requirements") or {}).get("format")
    if fmt:
        rows.append({"field": "format (as described)", "meaning": fmt})
    return rows


def synthetic_sample(run_dir: Path, rows: int = 8) -> dict:
    """A small, clearly synthetic sample shaped like the method's input."""
    spec = _pipeline(run_dir, "method_spec.json") or {}
    rng = random.Random(f"r2c-synthetic-{run_dir.name}")
    paradigm = _paradigm(run_dir)
    if "time_series" in paradigm:
        columns = ["timestamp", "value"]
        data = [[f"2026-01-{i + 1:02d}", round(10 + rng.gauss(0, 1) + i * 0.3, 3)] for i in range(rows)]
    else:
        n_classes = 3
        columns = ["feature_1", "feature_2", "feature_3", "feature_4", "label"]
        data = []
        for _ in range(rows):
            label = rng.randrange(n_classes)
            data.append([round(rng.gauss(label, 0.6), 3) for _ in range(4)] + [label])
    return {
        "label": "Synthetic",
        "columns": columns,
        "rows": data,
        "note": ((spec.get("data_requirements") or {}).get("synthetic_description")
                 or "Randomly generated rows shaped like the method's input."),
        "warning": "Synthetic data, generated by R2C. This is not the paper's data.",
    }


def _fetched(run_dir: Path, dataset_id: str) -> dict | None:
    record = _load_json(run_dir / "data" / dataset_id / "provenance.json")
    return record if isinstance(record, dict) else None


def build_dataset(run_dir: Path) -> dict:
    spec = _require(_pipeline(run_dir, "method_spec.json"), "method analysis (method_spec.json)")
    data_req = spec.get("data_requirements") or {}
    entries = dataset_entries(run_dir)
    for entry in entries:
        entry["fetched"] = _fetched(run_dir, entry["id"])
    any_public = any(e["availability"] == "public" for e in entries)
    return {
        "title": _paper_title(run_dir),
        "datasets": entries,
        "any_public": any_public,
        "demo_data": data_req.get("auto_download_details"),
        "paper_schema": _paper_schema(spec),
        "paper_schema_origin": "Built from the paper text by the method analysis stage",
        "synthetic": synthetic_sample(run_dir),
    }


# ---------------------------------------------------------------------------
# Experiment
# ---------------------------------------------------------------------------

TEST_STRENGTH = {
    "tested": ("Strong", "A planted bug made this test fail, so it really checks the code."),
    "weak": ("Weak", "The test still passed with a planted bug, so it may miss real mistakes."),
    "no_mutant": ("Unchecked", "There was nothing simple to break, so the test's strength is unknown."),
}
_SEED_LINE_RE = re.compile(r"^(\s*)SEED\s*=\s*(\d+)", re.MULTILINE)
_METRIC_WORDS = ("accuracy", "acc", "loss", "error", "f1", "auc", "precision", "recall",
                 "mse", "mae", "rmse", "nll", "reward", "bleu", "perplexity", "iou", "map", "score")
_SIMPLE_METRIC_RE = re.compile(
    r"(?P<label>[A-Za-z][A-Za-z _\-]{0,40}?)\s*[=:]\s*(?P<num>-?\d+(?:\.\d+)?(?:[eE]-?\d+)?)")
RUNS_FILE = "experiment_runs.json"


def _cell_source(cell: dict) -> str:
    src = cell.get("source", "")
    return "".join(src) if isinstance(src, list) else str(src)


def notebook_seed(nb: dict) -> int | None:
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "code":
            match = _SEED_LINE_RE.search(_cell_source(cell))
            if match:
                return int(match.group(2))
    return None


def _simple_observations(nb: dict) -> list[dict]:
    """Fallback metric reader for when the pipeline's parser (needs numpy) is unavailable."""
    out: list[dict] = []
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        for output in cell.get("outputs") or []:
            text = output.get("text") or (output.get("data") or {}).get("text/plain") or ""
            text = "".join(text) if isinstance(text, list) else str(text)
            for line in text.splitlines():
                round_match = re.search(r"\bround\s+(\d+)", line.lower())
                for m in _SIMPLE_METRIC_RE.finditer(line):
                    label = " ".join(m.group("label").split()).lower()
                    if not any(w in label.split() or label.endswith(w) for w in _METRIC_WORDS):
                        continue
                    out.append({"label": label, "value": float(m.group("num")), "line": line.strip(),
                                "temporal": "final" if "final" in line.lower() else ("round" if round_match else "point"),
                                "round": int(round_match.group(1)) if round_match else None})
    return out


def notebook_observations(nb: dict) -> list[dict]:
    try:
        from probes.claims import executed_metric_observations
        return executed_metric_observations(nb)
    except Exception:
        return _simple_observations(nb)


def final_metrics(observations: list[dict]) -> dict[str, float]:
    """Last reported value per metric label: a 'final' line wins, else the latest one."""
    finals: dict[str, float] = {}
    marked: set[str] = set()
    for obs in observations:
        label = obs.get("label") or obs.get("metric")
        if not label or label in marked:
            continue
        finals[label] = obs["value"]
        if obs.get("temporal") == "final":
            marked.add(label)
    return finals


def _load_notebook(run_dir: Path) -> dict | None:
    data = _load_json(run_dir / run_layout.NOTEBOOK_IPYNB)
    return data if isinstance(data, dict) else None


def experiment_runs(run_dir: Path) -> list[dict]:
    data = _load_json(ui_dir(run_dir) / RUNS_FILE)
    return data if isinstance(data, list) else []


def _own_data_supported(run_dir: Path, nb: dict | None) -> bool:
    try:
        data_py = (run_dir / "method" / "data.py").read_text(encoding="utf-8")
    except OSError:
        return False
    has_path_arg = re.search(r"def load_data\([^)]*\bpath\b", data_py, re.DOTALL) is not None
    calls = nb is not None and any("load_data(" in _cell_source(c) for c in nb.get("cells", []) if c.get("cell_type") == "code")
    return has_path_arg and calls


def build_experiment(run_dir: Path) -> dict:
    spec = _pipeline(run_dir, "method_spec.json") or {}
    elements = {e["id"]: e for e in _elements(run_dir)}
    tests = _pipeline(run_dir, "element_tests.json") or {}
    probes = _pipeline(run_dir, "probe_report.json") or {}
    demo = _pipeline(run_dir, "demo_verdict.json") or {}
    params = (_pipeline(run_dir, "params.json") or {}).get("params") or {}
    ledger = _pipeline(run_dir, "claims_ledger.json") or {}
    nb = _load_notebook(run_dir)
    _require(nb or tests or probes, "notebook or test results")

    statuses = tests.get("statuses") or {}
    modules = []
    for eid in tests.get("eligible") or list(statuses):
        status = (statuses.get(eid) or {}).get("status")
        strength, meaning = TEST_STRENGTH.get(status, ("No test", "No per-element test was written for this part."))
        modules.append({"id": eid, "name": (elements.get(eid) or {}).get("name") or eid,
                        "test_file": (statuses.get(eid) or {}).get("module"),
                        "strength": strength, "meaning": meaning})

    checks = [{"id": v.get("probe_id"), "result": v.get("verdict"), "message": v.get("message"),
               "kind": v.get("tier")} for v in probes.get("verdicts") or []]

    runs = []
    if nb is not None:
        runs.append({"id": "delivered", "kind": "delivered", "seed": notebook_seed(nb),
                     "label": "Delivered run", "status": "done",
                     "metrics": final_metrics(notebook_observations(nb))})
    runs.extend(experiment_runs(run_dir))
    metric_names = sorted({m for r in runs for m in (r.get("metrics") or {})})
    primary = str((spec.get("comparison") or {}).get("primary_metric") or "").lower()
    # Prefer the paper's primary metric on held-out data, e.g. "test accuracy".
    ranked = sorted(metric_names, key=lambda m: (m.split()[-1] not in primary,
                                                 not any(w in m for w in ("test", "val", "eval")), m))
    default_metric = ranked[0] if ranked else None

    paper_rows = []
    for claim in ledger.get("claims") or []:
        side = claim.get("paper_side")
        if isinstance(side, dict) and side.get("value") is not None:
            paper_rows.append({"claim": claim.get("name"), "metric": side.get("metric"),
                               "split": side.get("split"), "paper_value": side.get("value")})

    settings = []
    for name, p in params.items():
        if not isinstance(p, dict):
            continue
        paper_value = p.get("paper_value", p.get("value") if p.get("source") == "paper" else None)
        settings.append({"name": name, "paper": paper_value, "rebuilt": p.get("value"),
                         "source": p.get("source"), "why": p.get("reasoning") or p.get("note") or ""})

    return {
        "title": _paper_title(run_dir),
        "works": {"verdict": demo.get("verdict"), "evidence": demo.get("evidence_line"),
                  "decided_by": demo.get("marker_gloss")},
        "label": (_manifest(run_dir).get("delivery") or {}).get("label"),
        "modules": modules,
        "checks": checks,
        "runs": runs,
        "metric_names": metric_names,
        "default_metric": default_metric,
        "paper_claimed_results": (spec.get("paper_claims") or {}).get("claimed_results"),
        "paper_scale": (spec.get("paper_claims") or {}).get("benchmark_scale"),
        "paper_numbers": paper_rows,
        "settings": settings,
        "can_vary_seed": nb is not None and notebook_seed(nb) is not None,
        "can_use_own_data": _own_data_supported(run_dir, nb),
        "data_format": (spec.get("data_requirements") or {}).get("format"),
    }


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------

_LOWER_IS_BETTER = ("loss", "error", "mse", "mae", "rmse", "nll", "perplexity")


def _attention_count(run_dir: Path) -> int:
    path = run_layout.resolve_existing(run_dir, run_layout.ASSUMPTIONS_MD)
    try:
        match = re.search(r"_(\d+) need your attention", path.read_text(encoding="utf-8")) if path else None
    except OSError:
        match = None
    return int(match.group(1)) if match else 0


def _fit_to_user_data(exp: dict) -> dict:
    """How likely the method fits the user's data, judged only from runs we actually did."""
    metric = exp.get("default_metric")
    own = [r for r in exp["runs"] if r.get("kind") == "own_data"]
    demo = [r["metrics"][metric] for r in exp["runs"]
            if r.get("kind") != "own_data" and r.get("status") == "done" and metric in (r.get("metrics") or {})]
    if not own:
        return {"likelihood": "Unknown until you try",
                "reason": "No run on your data yet. Use Experiment, then 'Run the method on your own data'."}
    last = own[-1]
    if last.get("status") != "done":
        return {"likelihood": "Unlikely as-is", "reason": f"Running on your data failed: {last.get('error')}"}
    if not demo or metric not in last.get("metrics", {}):
        return {"likelihood": "Unclear", "reason": "The run on your data finished but did not report a comparable measure."}
    demo_mean, yours = sum(demo) / len(demo), last["metrics"][metric]
    lower_better = any(w in metric for w in _LOWER_IS_BETTER)
    ratio = (demo_mean / yours if yours else 0) if lower_better else (yours / demo_mean if demo_mean else 0)
    likelihood = "Likely" if ratio >= 0.9 else "Possible, needs tuning" if ratio >= 0.6 else "Unlikely without changes"
    return {"likelihood": likelihood,
            "reason": f"On your data, {metric} was {yours:.3f} versus {demo_mean:.3f} on the demo data "
                      f"({'lower' if lower_better else 'higher'} is better). This compares two small runs, not full-scale results."}


def build_decision(run_dir: Path) -> dict:
    spec = _require(_pipeline(run_dir, "method_spec.json"), "method analysis (method_spec.json)")
    gate = _pipeline(run_dir, "feasibility_gate.json") or {}
    replication = spec.get("replication_feasibility") or {}
    label = (_manifest(run_dir).get("delivery") or {}).get("label") or "no delivery"
    ledger = _pipeline(run_dir, "claims_ledger.json") or {}
    probes = (_pipeline(run_dir, "probe_report.json") or {}).get("counts") or {}
    params = (_pipeline(run_dir, "params.json") or {}).get("params") or {}
    tests = (_pipeline(run_dir, "element_tests.json") or {}).get("statuses") or {}

    counts = gate.get("blocker_counts") or {}
    feasibility = spec.get("feasibility")
    if feasibility == "infeasible" or replication.get("verdict") == "not_replicable" or counts.get("cannot_implement"):
        rebuild = ("No", "The paper text leaves out something the method cannot work without.")
    elif feasibility == "approximate" or replication.get("verdict") == "feasible_with_approved_approximations" or counts.get("can_approximate"):
        rebuild = ("Partly", "It can be rebuilt from the text, but some parts have to be approximated.")
    else:
        rebuild = ("Yes", "The paper text describes every required part clearly enough to rebuild it.")

    if rebuild[0] == "No" or label == "explanation_only":
        worth = ("Not yet", "The code could not be rebuilt reliably from this paper.")
    elif rebuild[0] == "Yes" and label == "verified":
        worth = ("Yes", "It rebuilds from the text and passed a behavioral check that a trivial baseline fails.")
    else:
        worth = ("With caution", f"It rebuilds, but the delivery is labeled '{label}', so review the findings first.")

    key = set((spec.get("core_method") or {}).get("key_elements") or [])
    parts = []
    for e in _elements(run_dir):
        role = e.get("code_role")
        priority = "Core, build first" if e["id"] in key else "Supporting" if role == "implement" else "Explain only, no code needed"
        strength = TEST_STRENGTH.get((tests.get(e["id"]) or {}).get("status"), ("No test",))[0]
        parts.append({"id": e["id"], "name": e.get("name"), "type": e.get("type"), "priority": priority,
                      "test": strength if role == "implement" else "—"})
    order = {"Core, build first": 0, "Supporting": 1, "Explain only, no code needed": 2}
    parts.sort(key=lambda p: order[p["priority"]])

    missing = []
    for b in gate.get("blockers") or []:
        if b.get("status") in ("cannot_implement", "can_approximate"):
            missing.append({"what": b.get("requirement"), "why": b.get("reason"),
                            "kind": "Cannot be built" if b["status"] == "cannot_implement" else "Approximated"})
    for b in replication.get("blockers") or []:
        missing.append({"what": b.get("technical_concept"), "why": b.get("reason"), "kind": "Not replicable"})
    unstated = [n for n, p in params.items() if isinstance(p, dict) and p.get("source") != "paper" and "paper_value" not in p]
    if unstated:
        missing.append({"what": f"{len(unstated)} setting(s) the paper does not state",
                        "why": "The system chose: " + ", ".join(unstated), "kind": "Guessed"})
    if not (spec.get("paper") or {}).get("repo_url"):
        missing.append({"what": "Official code", "why": "The paper links no code, so nothing could be cross-checked against the authors' version.", "kind": "Not available"})
    tally = ledger.get("tally") or {}
    if tally.get("untested_at_this_scale"):
        missing.append({"what": f"{tally['untested_at_this_scale']} paper claim(s) not checkable here",
                        "why": "They need the paper's full-scale experiments. See the Evidence Card.", "kind": "Untested"})
    if probes.get("unprobeable"):
        missing.append({"what": f"{probes['unprobeable']} automated check(s) could not run",
                        "why": "See 'Checks that could not run' in REPORT.md.", "kind": "Coverage gap"})
    attention = _attention_count(run_dir)
    if attention:
        missing.append({"what": f"{attention} decision(s) waiting for you",
                        "why": "Marked red in details/assumptions.md.", "kind": "Needs you"})

    exp = build_experiment(run_dir) if _load_notebook(run_dir) else {"runs": [], "default_metric": None}
    fit = _fit_to_user_data(exp)
    fit["requirements"] = (spec.get("data_requirements") or {}).get("format")
    fit["you_provide"] = [i.get("name") + ": " + (i.get("description") or "").rstrip(".")
                          for i in (spec.get("try_it_out") or {}).get("user_provides") or [] if isinstance(i, dict) and i.get("name")]

    if worth[0] == "Not yet":
        step = "Read METHOD.md for the idea, and look for the authors' code before building on this."
    elif label == "draft":
        step = "Open REPORT.md and fix the findings under 'Why this label' first. They are usually small."
    elif label.startswith("uncertified"):
        step = "Have someone review the core method code by hand, since no behavioral check covered it."
    elif fit["likelihood"] == "Unknown until you try":
        step = "Run the method on a sample of your own data in the Experiment tab."
    elif fit["likelihood"] == "Likely":
        step = "Scale up: move the settings marked 'System guess' in the Experiment tab toward the paper's values."
    else:
        step = "Check that your data matches the expected format, then tune the settings marked 'System guess'."

    return {
        "title": _paper_title(run_dir),
        "worth": {"answer": worth[0], "reason": worth[1]},
        "rebuild": {"answer": rebuild[0], "reason": rebuild[1], "feasibility": feasibility,
                    "replication": replication.get("verdict"), "label": label},
        "parts": parts,
        "missing": missing,
        "fit": fit,
        "next_step": step,
    }


# ---------------------------------------------------------------------------
# Teaching module
# ---------------------------------------------------------------------------

LABEL_WORDS = {
    "verified": "verified",
    "draft": "draft",
    "uncertified_new_territory": "uncertified, new territory",
    "explanation_only": "explanation only",
}
CLAIM_WORDS = {
    "verified_at_scale": "Verified at demo scale",
    "directionally_checked": "Checked in direction only",
    "untested_at_this_scale": "Untested at this scale",
    "suspect_our_implementation": "Needs a fix on our side",
    "contradicted": "Contradicted",
}


def _question(rng: random.Random, prompt: str, correct, wrong: list, explain: str) -> dict | None:
    """One multiple-choice question; None if there are not enough distinct wrong answers."""
    correct = str(correct)
    options = []
    for w in wrong:
        w = str(w)
        if w and w != correct and w not in options:
            options.append(w)
    if len(options) < 2:
        return None
    options = rng.sample(options, min(3, len(options))) + [correct]
    rng.shuffle(options)
    return {"prompt": prompt, "options": options, "answer": options.index(correct), "explain": explain}


def _short(text: str, n: int = 160) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0] + "…"


def build_teaching(run_dir: Path) -> dict:
    spec = _require(_pipeline(run_dir, "method_spec.json"), "method analysis (method_spec.json)")
    elements = _require(_elements(run_dir), "paper map (paper_map.json)")
    by_id = {e["id"]: e for e in elements}
    claims = (spec.get("paper_claims") or {})
    core = spec.get("core_method") or {}
    rng = random.Random(f"r2c-teaching-{run_dir.name}")

    concepts = [e for e in elements if e.get("type") == "concept"]
    problem = (concepts[0].get("description") if concepts else None) or core.get("summary")
    summary = {
        "problem": problem,
        "premise": claims.get("method_description") or core.get("summary"),
        "hypothesis": claims.get("claimed_results"),
    }

    def names(kind=None, exclude=()):
        return [e.get("name") for e in elements if (kind is None or e.get("type") == kind) and e["id"] not in exclude]

    quizzes = []

    # 1. Understand the paper (paper map + method analysis)
    qs = []
    key = set(core.get("key_elements") or [])
    qs.append(_question(rng, "What is the paper's core method?", core.get("name"),
                        names("concept") + names("hyperparameter") + names("experiment"),
                        f"The method analysis names it: {core.get('name')}."))
    with_deps = [e for e in elements if e.get("dependencies") and e["id"] in key] or [e for e in elements if e.get("dependencies")]
    if with_deps:
        target = with_deps[0]
        deps = [d for d in target["dependencies"] if d in by_id]
        if deps:
            unrelated = [e.get("name") for e in elements if e["id"] not in deps and e["id"] != target["id"]
                         and target["id"] not in (e.get("dependencies") or [])]
            qs.append(_question(rng, f"'{target.get('name')}' builds directly on which of these?",
                                by_id[deps[0]].get("name"), unrelated,
                                f"In the paper map, it depends on: {', '.join(by_id[d].get('name') for d in deps)}."))
    quizzes.append({"stage": "Understand the paper", "questions": qs})

    # 2. Explain the method (equations and where they come from)
    qs = []
    equations = [e for e in elements if e.get("type") == "equation" and e.get("description")]
    for eq in equations[:2]:
        qs.append(_question(rng, f"Which equation does this describe? \"{_short(eq['description'])}\"", eq.get("name"),
                            names("equation", exclude={eq["id"]}), f"That is {eq.get('name')} ({eq.get('section')})."))
    algs = [e for e in elements if e.get("type") == "algorithm" and e.get("section")]
    if algs:
        sections = sorted({e.get("section") for e in elements if e.get("section")})
        qs.append(_question(rng, f"Where in the paper is '{algs[0].get('name')}' described?", algs[0]["section"],
                            sections, f"The paper map points to {algs[0]['section']}."))
    quizzes.append({"stage": "Explain the method", "questions": qs})

    # 3. Write the code (entry point and settings)
    qs = []
    pluggable = ((spec.get("comparison") or {}).get("pluggable_component") or {}).get("name")
    if pluggable:
        try:
            helpers = re.findall(r"^def ([A-Za-z]\w*)\(", (run_dir / "method" / "method.py").read_text(encoding="utf-8"), re.MULTILINE)
        except OSError:
            helpers = []
        others = [i.get("symbol") for i in (spec.get("try_it_out") or {}).get("system_provides") or [] if isinstance(i, dict)]
        qs.append(_question(rng, "Which function do you call to use the method in your own code?", pluggable,
                            [h for h in helpers if h != pluggable] + [o for o in others if o],
                            f"`{pluggable}` is the method's entry point; the others are helpers it uses."))
    params = (_pipeline(run_dir, "params.json") or {}).get("params") or {}
    guessed = [n for n, p in params.items() if isinstance(p, dict) and p.get("source") != "paper"]
    from_paper = [n for n, p in params.items() if isinstance(p, dict) and p.get("source") == "paper"]
    if guessed:
        qs.append(_question(rng, "Which setting was chosen by the system rather than taken from the paper?", guessed[0],
                            from_paper, f"`{guessed[0]}` is marked as a system choice in the settings log."))
    quizzes.append({"stage": "Write the code", "questions": qs})

    # 4. Run the notebook (what is measured, what came out)
    qs = []
    nb = _load_notebook(run_dir)
    metrics = final_metrics(notebook_observations(nb)) if nb else {}
    primary = str((spec.get("comparison") or {}).get("primary_metric") or "")
    if primary:
        qs.append(_question(rng, "What does the demo measure to show the method working?", primary,
                            ["Wall-clock training time", "GPU memory used", "Number of model parameters", "Lines of code generated"],
                            f"The method analysis sets the primary measure: {primary}"))
    test_metric = next((m for m in metrics if "test" in m), None)
    if test_metric:
        v = metrics[test_metric]
        qs.append(_question(rng, f"Roughly what {test_metric} did the delivered demo reach at the end?", f"{v:.2f}",
                            [f"{v * f:.2f}" for f in (0.5, 0.75, 1.12) if 0 <= v * f <= 1 or "loss" in test_metric],
                            f"The notebook's last reported {test_metric} was {v:.3f}, on small demo data."))
    quizzes.append({"stage": "Run the notebook", "questions": qs})

    # 5. Verify and report
    qs = []
    label = (_manifest(run_dir).get("delivery") or {}).get("label")
    if label in LABEL_WORDS:
        qs.append(_question(rng, "What delivery label did this run get?", LABEL_WORDS[label], list(LABEL_WORDS.values()),
                            "The label is the first line of REPORT.md."))
    qs.append(_question(rng, "In R2C, what does the label 'verified' mean?",
                        "The code runs and passed a behavioral check that a trivial baseline fails",
                        ["The paper's headline numbers were reproduced", "The paper's authors reviewed the code",
                         "Every test passed on a GPU at full scale"],
                        "Verified never means the paper's full-scale numbers were reproduced."))
    for claim in ((_pipeline(run_dir, "claims_ledger.json") or {}).get("claims") or [])[:1]:
        if claim.get("status") in CLAIM_WORDS:
            qs.append(_question(rng, f"What verdict did the claim '{claim.get('name')}' get?", CLAIM_WORDS[claim["status"]],
                                list(CLAIM_WORDS.values()), _short(claim.get("reasoning") or claim.get("status_note"), 240)))
    quizzes.append({"stage": "Verify and report", "questions": qs})

    for quiz in quizzes:
        quiz["questions"] = [q for q in quiz["questions"] if q]
    return {"title": _paper_title(run_dir), "summary": summary,
            "quizzes": [q for q in quizzes if q["questions"]]}


# ---------------------------------------------------------------------------
# Knowledge graph
# ---------------------------------------------------------------------------

NODE_KIND = {
    "concept": "Premise",
    "property": "Hypothesis",
    "equation": "Equation",
    "algorithm": "Algorithm",
    "hyperparameter": "Setting",
    "experiment": "Claim",
}
SELECTION_FILE = "build_selection.json"


def _dataset_tokens(name: str) -> list[str]:
    """Words that identify a dataset in prose, e.g. 'OpenML #6' also matches 'OpenML'."""
    tokens = [name.lower()]
    if _OPENML_RE.search(name):
        tokens.append("openml")
    known = _match_known(name)
    if known:
        tokens.append(known)
    return tokens


def build_graph(run_dir: Path) -> dict:
    elements = _require(_elements(run_dir), "paper map (paper_map.json)")
    spec = _pipeline(run_dir, "method_spec.json") or {}
    ids = {e["id"] for e in elements}
    key = set((spec.get("core_method") or {}).get("key_elements") or [])

    nodes, edges = [], []
    for e in elements:
        nodes.append({"id": e["id"], "kind": NODE_KIND.get(e.get("type"), "Premise"),
                      "label": e.get("name") or e["id"], "section": e.get("section"),
                      "description": e.get("description"), "source_text": _short(e.get("source_text"), 400),
                      "code_role": e.get("code_role"), "core": e["id"] in key})
        for dep in e.get("dependencies") or []:
            if dep in ids:
                edges.append({"from": e["id"], "to": dep, "kind": "depends on"})
        if e.get("type") == "algorithm":
            for eq in e.get("related_equations") or []:
                if eq in ids and eq not in (e.get("dependencies") or []):
                    edges.append({"from": e["id"], "to": eq, "kind": "implements"})

    # "tested on" only where the paper's own experiment text names the dataset.
    benchmark = str((spec.get("paper_claims") or {}).get("benchmark_scale") or "")
    experiments = [e for e in elements if e.get("type") == "experiment"]
    for raw in (spec.get("data_requirements") or {}).get("example_datasets") or []:
        name = str(raw).strip()
        if not name:
            continue
        did = "dataset-" + _slugify(name)
        linked = False
        for exp in experiments:
            text = f"{exp.get('source_text', '')} {exp.get('description', '')} {benchmark}".lower()
            if any(tok in text for tok in _dataset_tokens(name)):
                edges.append({"from": exp["id"], "to": did, "kind": "tested on"})
                linked = True
        nodes.append({"id": did, "kind": "Dataset", "label": name, "section": None,
                      "description": "A dataset the paper names." + ("" if linked else " The paper map does not tie it to a specific experiment."),
                      "source_text": benchmark or None, "code_role": None, "core": False})

    saved = _load_json(ui_dir(run_dir) / SELECTION_FILE) or {}
    return {"title": _paper_title(run_dir), "nodes": nodes, "edges": edges,
            "selection": saved.get("selected") or [], "saved_at": saved.get("saved_at")}


def save_graph_selection(run_dir: Path, body: dict) -> dict:
    """Save which paper parts the user wants built, for a later build step to read."""
    valid = {n["id"] for n in build_graph(run_dir)["nodes"]}
    selected = [i for i in body.get("selected") or [] if i in valid]
    record = {"selected": selected, "saved_at": _now_iso(),
              "note": "Paper-map element ids chosen in the Knowledge Graph tab."}
    path = ui_dir(run_dir) / SELECTION_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return {**record, "path": str(path)}


# ---------------------------------------------------------------------------
# Evidence Card
# ---------------------------------------------------------------------------

# A contradicted claim is shown as "Not supported" rather than folded into
# "Not checkable", which would hide a real negative result.
EVIDENCE_RATING = {
    "verified_at_scale": "Supported",
    "directionally_checked": "Partly supported",
    "untested_at_this_scale": "Not checkable",
    "suspect_our_implementation": "Not checkable",
    "contradicted": "Not supported",
}
SOURCE_WORDS = {"paper": "From the paper", "system_default": "System default", "system_inferred": "System inferred"}
_ASSUMPTION_RE = re.compile(r"^## (A\d+) — (.+?)\n(.*?)(?=^## A\d+ — |\Z)", re.MULTILINE | re.DOTALL)
_ASSUMPTION_PART_RE = re.compile(r"\*\*(.+?)\.\*\*\s*(.*?)(?=\n\*\*|\n---|\Z)", re.DOTALL)


def _side_text(side) -> str:
    if not side:
        return ""
    if isinstance(side, dict):
        return ", ".join(f"{k}: {v}" for k, v in side.items() if v not in (None, "", []))
    return str(side)


def _claim_limits(claim: dict) -> list[str]:
    limits = []
    status = claim.get("status")
    if status == "verified_at_scale" and claim.get("kind") != "lifted":
        limits.append("Checked on a small demo run. It does not confirm the paper's full-scale numbers.")
    elif status == "verified_at_scale":
        limits.append("Checked at demo scale, not at the paper's full scale.")
    if status == "suspect_our_implementation":
        limits.append("The rebuilt code may be at fault, so this says nothing yet about the paper.")
    if claim.get("suspected_cause"):
        limits.append(f"Suspected cause: {claim['suspected_cause']}")
    if claim.get("what_would_verify"):
        limits.append(f"To check it fully: {claim['what_would_verify'].rstrip('.')}.")
    if not limits and status != "verified_at_scale":
        limits.append("No further check is defined for this claim.")
    return limits


def _assumption_entries(run_dir: Path) -> list[dict]:
    path = run_layout.resolve_existing(run_dir, run_layout.ASSUMPTIONS_MD)
    try:
        text = path.read_text(encoding="utf-8") if path else ""
    except OSError:
        return []
    entries = []
    for aid, title, body in _ASSUMPTION_RE.findall(text):
        parts = {k.strip().lower(): " ".join(v.split()) for k, v in _ASSUMPTION_PART_RE.findall(body)}
        entries.append({
            "id": aid,
            "title": title.replace("NEEDS USER ATTENTION — ", "").strip(),
            "needs_you": "NEEDS USER ATTENTION" in title,
            "detected": parts.get("detected", ""),
            "action": parts.get("action taken", ""),
            "reasoning": parts.get("reasoning", ""),
            "override": parts.get("to override", ""),
        })
    return sorted(entries, key=lambda e: e["id"])


def build_evidence(run_dir: Path) -> dict:
    ledger = _require(_pipeline(run_dir, "claims_ledger.json"), "claims ledger (made by the verification stage)")
    claims = []
    for c in ledger.get("claims") or []:
        status = c.get("status") or ""
        claims.append({
            "id": c.get("claim_id"),
            "name": c.get("name") or c.get("claim_id"),
            "text": c.get("claim_text") or "",
            "section": c.get("section") or "",
            # "lifted" claims are quoted from the paper; the rest are checks R2C added.
            "from_paper": c.get("kind") == "lifted",
            "rating": EVIDENCE_RATING.get(status, "Not checkable"),
            "status_words": CLAIM_WORDS.get(status, status.replace("_", " ")),
            "evidence": c.get("reasoning") or c.get("status_note") or "",
            "paper_side": _side_text(c.get("paper_side")),
            "executed_side": _side_text(c.get("executed_side")),
            "seeds": c.get("seed_set"),
            "trace": [{"step": k, "text": str(v)} for k, v in (c.get("verdict_trace") or {}).items()],
            "limits": _claim_limits(c),
            "override": c.get("researcher_override"),
        })
    counts = {r: sum(1 for c in claims if c["rating"] == r)
              for r in ("Supported", "Partly supported", "Not checkable", "Not supported")}

    params = (_pipeline(run_dir, "params.json") or {}).get("params") or {}
    settings = []
    for name, p in params.items():
        if not isinstance(p, dict):
            continue
        source = p.get("source") or ""
        paper_value = p.get("paper_value", p.get("value") if source == "paper" else None)
        settings.append({
            "name": name,
            "value": p.get("value"),
            "source": SOURCE_WORDS.get(source, source.replace("_", " ") or "Unknown"),
            "guessed": source != "paper",
            "paper_value": paper_value,
            "paper_says": p.get("paper_says") or "",
            "section": p.get("paper_section") or "",
            "why": p.get("reasoning") or p.get("note") or "",
        })
    settings.sort(key=lambda s: (not s["guessed"], s["name"]))
    return {
        "title": _paper_title(run_dir),
        "label": (_manifest(run_dir).get("delivery") or {}).get("label"),
        "claims": claims,
        "counts": counts,
        "settings": settings,
        "assumptions": _assumption_entries(run_dir),
    }


_UPLOAD_EXTS = {".pt", ".csv", ".json", ".npz", ".npy", ".tsv", ".txt", ".parquet"}


def save_upload(run_dir: Path, batch: str, name: str, body: bytes) -> dict:
    """Store one user data file for an own-data run (never inside the package)."""
    if not re.fullmatch(r"[a-z0-9-]{1,40}", batch or ""):
        raise ValueError("Bad upload batch id.")
    clean = Path(name or "").name
    if not clean or Path(clean).suffix.lower() not in _UPLOAD_EXTS:
        raise ValueError(f"Unsupported file type. Use one of: {', '.join(sorted(_UPLOAD_EXTS))}")
    dest = ui_dir(run_dir) / "uploads" / batch
    dest.mkdir(parents=True, exist_ok=True)
    (dest / clean).write_bytes(body)
    return {"batch": batch, "files": sorted(p.name for p in dest.iterdir())}
