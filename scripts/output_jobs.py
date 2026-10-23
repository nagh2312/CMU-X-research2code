"""Background jobs started from the output screen.

A job runs in a thread inside the viewer and records its state in
`<run>/.pipeline/ui/jobs/<kind>.json`, so a page reload shows the last result.
Jobs never edit the delivered package or notebook; they work on copies or in
new folders (`<run>/data/`, `<run>/.pipeline/ui/`).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import traceback
from pathlib import Path

import output_tabs

NOTEBOOK_RUN_TIMEOUT_S = 45 * 60
CELL_TIMEOUT_S = 900
MAX_SEEDS = 5

_LOCK = threading.Lock()
_LIVE: dict[str, threading.Thread] = {}


def _job_path(run_dir: Path, kind: str) -> Path:
    return output_tabs.ui_dir(run_dir) / "jobs" / f"{kind}.json"


def _write(run_dir: Path, kind: str, state: dict) -> None:
    path = _job_path(run_dir, kind)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(path)


def job_status(run_dir: Path, kind: str) -> dict:
    state = output_tabs._load_json(_job_path(run_dir, kind)) or {"kind": kind, "status": "idle"}
    key = f"{run_dir}:{kind}"
    # A "running" record with no live thread means the viewer restarted mid-job.
    if state.get("status") == "running" and not (key in _LIVE and _LIVE[key].is_alive()):
        state.update(status="failed", message="Interrupted because the viewer restarted. Try again.")
    return state


def start_job(run_dir: Path, kind: str, params: dict) -> dict:
    runner = RUNNERS.get(kind)
    if runner is None:
        raise KeyError(kind)
    key = f"{run_dir}:{kind}"
    with _LOCK:
        if key in _LIVE and _LIVE[key].is_alive():
            return job_status(run_dir, kind)
        state = {"kind": kind, "status": "running", "params": params,
                 "message": "Starting...", "started_at": output_tabs._now_iso()}
        _write(run_dir, kind, state)

        def target() -> None:
            def progress(message: str) -> None:
                state["message"] = message
                _write(run_dir, kind, state)
            try:
                state["result"] = runner(run_dir, params, progress)
                state.update(status="done", message="Finished.")
            except Exception as exc:  # surfaced to the page with a Retry button
                state.update(status="failed", message=str(exc) or exc.__class__.__name__,
                             detail=traceback.format_exc(limit=3))
            state["finished_at"] = output_tabs._now_iso()
            _write(run_dir, kind, state)

        thread = threading.Thread(target=target, name=f"r2c-{kind}", daemon=True)
        _LIVE[key] = thread
        thread.start()
    return state


# ---------------------------------------------------------------------------
# Dataset fetch
# ---------------------------------------------------------------------------

def _run_dataset_fetch(run_dir: Path, params: dict, progress) -> dict:
    from dataset_acquisition import DatasetSource, fetch_source

    dataset_id = str(params.get("dataset_id") or "")
    entry = next((e for e in output_tabs.dataset_entries(run_dir) if e["id"] == dataset_id), None)
    if entry is None:
        raise ValueError(f"Unknown dataset: {dataset_id}")
    if not entry.get("fetchable"):
        raise ValueError(entry.get("fetch_note") or "This dataset cannot be fetched automatically.")

    dest = run_dir / "data" / dataset_id
    files = []
    for i, url in enumerate(entry["download_urls"], start=1):
        progress(f"Downloading file {i} of {len(entry['download_urls'])}: {url.rsplit('/', 1)[-1]}")
        source = DatasetSource(host=url.split("/")[2], cited_url=url, download_url=url, credentialed=False)
        got = fetch_source(source, dest)
        path = got.path
        url_name = url.rsplit("/", 1)[-1]
        if url_name and path.name != url_name:
            path = path.replace(dest / url_name)
        files.append({"file": path.name, "bytes": got.bytes_written,
                      "sha256": got.sha256, "truncated": got.truncated, "url": url})
    record = {"dataset": entry["name"], "label": "Public", "source": entry["source"],
              "fetched_at": output_tabs._now_iso(), "folder": str(dest), "files": files}
    (dest / "provenance.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


# ---------------------------------------------------------------------------
# Experiment: seeded re-runs, own-data runs, module tests
# ---------------------------------------------------------------------------

def _python() -> str:
    # Same interpreter the pipeline driver is launched with (`python3` on PATH).
    return os.environ.get("R2C_PYTHON") or shutil.which("python3") or sys.executable


def _patched_notebook(run_dir: Path, *, seed: int | None = None, data_path: Path | None = None) -> dict:
    nb = output_tabs._load_notebook(run_dir)
    if nb is None:
        raise FileNotFoundError("The delivered notebook.ipynb is missing.")
    seed_done = data_done = False
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        cell["outputs"], cell["execution_count"] = [], None
        src = output_tabs._cell_source(cell)
        if seed is not None and not seed_done:
            src, n = output_tabs._SEED_LINE_RE.subn(lambda m: f"{m.group(1)}SEED = {seed}", src, count=1)
            seed_done = n > 0
        if data_path is not None:
            src, n = _point_load_data_at(src, data_path)
            data_done = data_done or n > 0
        cell["source"] = src
    if seed is not None and not seed_done:
        raise ValueError("The notebook has no `SEED = <number>` line, so the seed cannot be changed.")
    if data_path is not None and not data_done:
        raise ValueError("The notebook never calls load_data(), so it cannot be pointed at your data.")
    return nb


def _point_load_data_at(src: str, data_path: Path) -> tuple[str, int]:
    """Make every load_data(...) call in a code cell read `data_path`."""
    lines, count = [], 0
    for line in src.splitlines(keepends=True):
        stripped = line.lstrip()
        if "load_data(" in line and not stripped.startswith(("from ", "import ", "def ", "#")):
            positional = re.compile(r"load_data\(\s*([\"'])[^\"']*\1")
            if positional.search(line):
                line = positional.sub(lambda m: f"load_data({str(data_path)!r}", line, count=1)
            else:
                line = line.replace("load_data(", f"load_data(path={str(data_path)!r}, ", 1)
                line = line.replace(", )", ")")
            count += 1
        lines.append(line)
    return "".join(lines), count


def _execute(run_dir: Path, nb: dict, name: str) -> dict:
    """Run a notebook copy in a separate process (cwd = run dir); return it executed."""
    work = output_tabs.ui_dir(run_dir) / "exec"
    work.mkdir(parents=True, exist_ok=True)
    src, out = work / f"{name}.ipynb", work / f"{name}.executed.ipynb"
    src.write_text(json.dumps(nb), encoding="utf-8")
    out.unlink(missing_ok=True)
    proc = subprocess.run(
        [_python(), str(Path(__file__).resolve()), "--execute", str(src), str(out), str(run_dir)],
        capture_output=True, text=True, timeout=NOTEBOOK_RUN_TIMEOUT_S, cwd=str(run_dir))
    if proc.returncode != 0 or not out.is_file():
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-1:]
        raise RuntimeError("The notebook failed: " + (" ".join(tail) or f"exit code {proc.returncode}"))
    return json.loads(out.read_text(encoding="utf-8"))


def _save_run(run_dir: Path, record: dict) -> None:
    runs = [r for r in output_tabs.experiment_runs(run_dir) if r.get("id") != record["id"]]
    runs.append(record)
    path = output_tabs.ui_dir(run_dir) / output_tabs.RUNS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(runs, indent=2), encoding="utf-8")


def _run_seeds(run_dir: Path, params: dict, progress) -> dict:
    try:
        seeds = [int(s) for s in params.get("seeds") or []]
    except (TypeError, ValueError):
        raise ValueError("Seeds must be whole numbers.")
    if not seeds:
        raise ValueError("Give at least one seed.")
    if len(seeds) > MAX_SEEDS:
        raise ValueError(f"Use at most {MAX_SEEDS} seeds at a time; each one re-runs the whole notebook.")
    finished = []
    for i, seed in enumerate(seeds, start=1):
        progress(f"Running seed {seed} ({i} of {len(seeds)}). Each run re-trains from scratch and can take several minutes.")
        record = {"id": f"seed-{seed}", "kind": "seed", "seed": seed, "label": f"Seed {seed}",
                  "finished_at": output_tabs._now_iso()}
        try:
            executed = _execute(run_dir, _patched_notebook(run_dir, seed=seed), f"seed-{seed}")
            record.update(status="done", metrics=output_tabs.final_metrics(output_tabs.notebook_observations(executed)))
        except Exception as exc:
            record.update(status="failed", error=str(exc), metrics={})
        _save_run(run_dir, record)
        finished.append(record)
    failed = [r for r in finished if r["status"] == "failed"]
    if len(failed) == len(finished):
        raise RuntimeError(failed[0]["error"])
    return {"runs": finished}


def _run_own_data(run_dir: Path, params: dict, progress) -> dict:
    batch = str(params.get("batch") or "")
    folder = output_tabs.ui_dir(run_dir) / "uploads" / batch
    if not re.fullmatch(r"[a-z0-9-]{1,40}", batch) or not folder.is_dir():
        raise ValueError("Upload your data file(s) first.")
    files = sorted(folder.iterdir())
    target = files[0] if len(files) == 1 else folder
    progress(f"Running the method on your data ({', '.join(f.name for f in files)}).")
    executed = _execute(run_dir, _patched_notebook(run_dir, data_path=target), f"own-{batch}")
    record = {"id": f"own-{batch}", "kind": "own_data", "seed": None, "status": "done",
              "label": f"Your data ({', '.join(f.name for f in files)})",
              "metrics": output_tabs.final_metrics(output_tabs.notebook_observations(executed)),
              "finished_at": output_tabs._now_iso()}
    _save_run(run_dir, record)
    return record


def _run_module_tests(run_dir: Path, params: dict, progress) -> dict:
    tests_dir = run_dir / "method" / "tests"
    if not tests_dir.is_dir():
        raise FileNotFoundError("This run has no method/tests folder.")
    progress("Running the per-module tests...")
    proc = subprocess.run([_python(), "-m", "pytest", str(tests_dir), "-q", "-rA", "-p", "no:cacheprovider"],
                          capture_output=True, text=True, timeout=NOTEBOOK_RUN_TIMEOUT_S, cwd=str(run_dir))
    results = {}
    for line in proc.stdout.splitlines():
        m = re.match(r"(PASSED|FAILED|ERROR|SKIPPED)\s+(\S+?)(?:::(\S+))?(?:\s|$)", line)
        if m:
            file_name = Path(m.group(2)).name
            results.setdefault(file_name, []).append(m.group(1))
    if not results:
        tail = (proc.stdout + proc.stderr).strip().splitlines()[-6:]
        raise RuntimeError("The tests could not run: " + " ".join(tail))
    return {"files": [{"file": f, "passed": r.count("PASSED"), "failed": r.count("FAILED") + r.count("ERROR"),
                       "skipped": r.count("SKIPPED")} for f, r in sorted(results.items())]}


RUNNERS = {
    "dataset_fetch": _run_dataset_fetch,
    "experiment_seeds": _run_seeds,
    "own_data": _run_own_data,
    "module_tests": _run_module_tests,
}


def _execute_main(src: str, out: str, run_dir: str) -> int:
    """Subprocess entry: execute a notebook with the smoke stage's kernel choice."""
    try:
        import nbformat
        from nbclient import NotebookClient
        from smoke_run_notebook import _resolve_kernel
    except ImportError as exc:
        print(f"{sys.executable} is missing the package '{exc.name}'. Install the run's "
              "requirements.txt plus nbclient and ipykernel into it, or set R2C_PYTHON to "
              "the Python that ran the pipeline.", file=sys.stderr)
        return 1

    nb = nbformat.read(src, as_version=4)
    client = NotebookClient(nb, timeout=CELL_TIMEOUT_S, kernel_name=_resolve_kernel("python3"),
                            resources={"metadata": {"path": run_dir}}, allow_errors=False)
    try:
        client.execute()
    except Exception as exc:
        print(str(exc).strip().splitlines()[-1] if str(exc).strip() else repr(exc), file=sys.stderr)
        return 1
    nbformat.write(nb, out)
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "--execute":
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        raise SystemExit(_execute_main(*sys.argv[2:]))
    raise SystemExit("usage: output_jobs.py --execute <notebook> <out> <run_dir>")
