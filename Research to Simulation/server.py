#!/usr/bin/env python3
"""Research to Simulation — local prototype viewer (stdlib only)."""

from __future__ import annotations

import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DEMOS = ROOT / "demos"

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Research to Simulation</title>
<link rel="stylesheet" href="/static/app.css">
</head>
<body>
  <header class="top">
    <div>
      <p class="eyebrow">Research to Simulation</p>
      <h1>Paper → interactive method</h1>
      <p class="lede">Upload a paper, see what can be simulated, then experiment with the method — not just read it.</p>
    </div>
    <a class="ghost" href="https://github.com/nagh2312/research2code/tree/research-to-simulation/Research%20to%20Simulation" target="_blank" rel="noopener">Prototype notes</a>
  </header>

  <nav class="steps" id="steps">
    <button type="button" class="step active" data-step="upload">1. Upload</button>
    <button type="button" class="step" data-step="understand">2. Understand</button>
    <button type="button" class="step" data-step="simulate">3. Simulate</button>
    <button type="button" class="step" data-step="results">4. Results</button>
  </nav>

  <main>
    <section id="panel-upload" class="panel">
      <div class="card highlight">
        <h2>Upload a research paper</h2>
        <p>Drop a PDF that describes a model, algorithm, equations, or experimental setup. This prototype ships with a path-planning demo so you can try the full loop without a live paper-ingest pipeline.</p>
        <div class="drop" id="drop">
          <p><b>Drop a PDF here</b> or choose a file</p>
          <p class="muted">Prototype: file is not sent to a server; we load the demo method pack.</p>
          <input type="file" id="file" accept=".pdf,application/pdf">
        </div>
        <div class="row">
          <button type="button" class="btn primary" id="use-demo">Use path-planning demo</button>
          <span class="muted" id="upload-status">No paper loaded yet.</span>
        </div>
      </div>
    </section>

    <section id="panel-understand" class="panel" hidden>
      <div class="card highlight">
        <h2 id="method-title">Method</h2>
        <p id="method-line"></p>
        <p class="muted" id="method-paper"></p>
      </div>
      <div class="grid3">
        <div class="card">
          <h3>Can simulate</h3>
          <ul id="list-yes"></ul>
        </div>
        <div class="card warn">
          <h3>Partial / ambiguous</h3>
          <ul id="list-partial"></ul>
        </div>
        <div class="card danger">
          <h3>Missing from the paper</h3>
          <ul id="list-missing"></ul>
        </div>
      </div>
      <div class="grid2">
        <div class="card">
          <h3>Supported by the paper</h3>
          <ul id="list-supported"></ul>
        </div>
        <div class="card warn">
          <h3>Assumptions for this simulation</h3>
          <ul id="list-assumptions"></ul>
        </div>
      </div>
      <div class="row">
        <button type="button" class="btn primary" data-go="simulate">Open simulation environment</button>
      </div>
    </section>

    <section id="panel-simulate" class="panel" hidden>
      <div class="sim-layout">
        <div class="card">
          <h2>Interactive environment</h2>
          <p class="muted">Click a free cell for <b>start</b>, Shift-click for <b>goal</b>, Alt-click to toggle an <b>obstacle</b>. Then run the planner.</p>
          <canvas id="world" width="640" height="448" aria-label="Simulation grid"></canvas>
          <div class="legend">
            <span><i class="sw start"></i> Start</span>
            <span><i class="sw goal"></i> Goal</span>
            <span><i class="sw obstacle"></i> Obstacle</span>
            <span><i class="sw path"></i> Path</span>
            <span><i class="sw expanded"></i> Expanded</span>
          </div>
        </div>
        <div class="side">
          <div class="card">
            <h3>Controls</h3>
            <label>Heuristic
              <select id="heuristic">
                <option value="manhattan">Manhattan (paper-typical for grids)</option>
                <option value="euclidean">Euclidean</option>
                <option value="none">None (Dijkstra-style)</option>
              </select>
            </label>
            <label class="check"><input type="checkbox" id="diagonal"> Allow diagonal moves <span class="pill assume">assumption</span></label>
            <div class="row">
              <button type="button" class="btn primary" id="run">Run scenario</button>
              <button type="button" class="btn" id="reset">Reset scene</button>
            </div>
            <p class="muted" id="sim-hint"></p>
          </div>
          <div class="card">
            <h3>Last run</h3>
            <dl class="kv" id="run-stats">
              <dt>Status</dt><dd>—</dd>
            </dl>
            <button type="button" class="btn" data-go="results">View explanation</button>
          </div>
        </div>
      </div>
    </section>

    <section id="panel-results" class="panel" hidden>
      <div class="card highlight">
        <h2>What the results mean</h2>
        <p id="result-story"></p>
      </div>
      <div class="grid2">
        <div class="card">
          <h3>Tied to the paper</h3>
          <ul id="result-supported"></ul>
        </div>
        <div class="card warn">
          <h3>Still assumptions</h3>
          <ul id="result-assumptions"></ul>
        </div>
      </div>
      <div class="card">
        <h3>Scenario history</h3>
        <table>
          <thead><tr><th>#</th><th>Status</th><th>Path length</th><th>Expanded</th><th>Heuristic</th></tr></thead>
          <tbody id="history"></tbody>
        </table>
      </div>
      <div class="row">
        <button type="button" class="btn primary" data-go="simulate">Try another scenario</button>
      </div>
    </section>
  </main>

  <footer class="foot">
    <p>Prototype only. Faithful simulation needs enough detail in the paper; missing pieces are listed under assumptions.</p>
  </footer>
  <script src="/static/app.js"></script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            return self._send(200, HTML.encode("utf-8"), "text/html; charset=utf-8")
        if path.startswith("/static/"):
            name = path[len("/static/") :]
            if "/" in name or name.startswith("."):
                return self._send(404, b"not found", "text/plain")
            file = STATIC / name
            if not file.is_file():
                return self._send(404, b"not found", "text/plain")
            ctype = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
            return self._send(200, file.read_bytes(), ctype)
        if path.startswith("/demo/"):
            name = path[len("/demo/") :]
            if not name.endswith(".json") or "/" in name:
                return self._send(404, b'{"error":"unknown demo"}', "application/json")
            file = DEMOS / name
            if not file.is_file():
                return self._send(404, b'{"error":"unknown demo"}', "application/json")
            return self._send(200, file.read_bytes(), "application/json; charset=utf-8")
        if path == "/demos":
            demos = sorted(p.name for p in DEMOS.glob("*.json"))
            return self._send(200, json.dumps({"demos": demos}).encode(), "application/json")
        self._send(404, b"not found", "text/plain")


def main() -> None:
    ap = argparse.ArgumentParser(description="Research to Simulation prototype viewer")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8801)
    args = ap.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Research to Simulation at http://{args.host}:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
