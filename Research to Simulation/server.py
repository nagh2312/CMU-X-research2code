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
  <div class="app">
    <header class="topbar">
      <div class="topbar-left">
        <span class="brand">Research to Simulation</span>
        <span class="proj-name" id="proj-name">Simulation Project</span>
        <span class="badge-private">PRIVATE</span>
      </div>
      <div class="topbar-right">
        <button type="button" class="tb-link" id="connectors-btn" aria-expanded="false" aria-controls="connectors-panel">Connectors</button>
        <a class="tb-link" href="https://github.com/nagh2312/CMU-X-research2code/tree/research-to-simulation/Research%20to%20Simulation" target="_blank" rel="noopener">Docs</a>
        <span class="tb-muted">Workbench</span>
      </div>
    </header>

    <div class="toolbar" role="toolbar" aria-label="Viewport tools">
      <div class="tool-group">
        <span class="tool-label">Filters</span>
        <button type="button" class="tool" title="Grid" data-tool="grid"><span class="ticon">▦</span><span>Grid</span></button>
        <button type="button" class="tool" title="Path" data-tool="path"><span class="ticon">↗</span><span>Path</span></button>
        <button type="button" class="tool" title="Expanded" data-tool="expanded"><span class="ticon">◉</span><span>Expanded</span></button>
        <button type="button" class="tool" title="Obstacles" data-tool="obstacles"><span class="ticon">■</span><span>Obstacles</span></button>
      </div>
      <div class="tool-group">
        <span class="tool-label">View</span>
        <button type="button" class="tool" title="Legend" id="toggle-legend"><span class="ticon">▤</span><span>Legend</span></button>
        <button type="button" class="tool" title="Statistics" id="toggle-stats"><span class="ticon">∑</span><span>Statistics</span></button>
        <button type="button" class="tool" title="Inspect" data-tool="inspect"><span class="ticon">⌖</span><span>Inspect</span></button>
      </div>
      <div class="tool-group">
        <span class="tool-label">Result</span>
        <button type="button" class="tool primary-tool" id="run" title="Run scenario"><span class="ticon">▶</span><span>Run</span></button>
        <button type="button" class="tool" id="reset" title="Reset scene"><span class="ticon">↺</span><span>Reset</span></button>
        <button type="button" class="tool" data-go="results" title="Results"><span class="ticon">▣</span><span>Results</span></button>
      </div>
    </div>

    <div class="workbench">
      <aside class="tree" aria-label="Project tree">
        <div class="tree-section">
          <button type="button" class="tree-h">Geometries</button>
          <ul class="tree-list">
            <li class="tree-item muted-item">Grid world <span class="count">1</span></li>
          </ul>
        </div>
        <div class="tree-section">
          <button type="button" class="tree-h">Workflow</button>
          <ul class="tree-list" id="steps">
            <li><button type="button" class="tree-item step active" data-step="upload">Paper upload</button></li>
            <li><button type="button" class="tree-item step" data-step="understand" disabled>Method analysis</button></li>
            <li><button type="button" class="tree-item step" data-step="simulate" disabled>Simulation</button></li>
            <li><button type="button" class="tree-item step" data-step="results" disabled>Result control</button></li>
          </ul>
        </div>
        <div class="tree-section">
          <button type="button" class="tree-h">Simulation</button>
          <ul class="tree-list" id="sim-tree">
            <li class="tree-item nest">Scene
              <ul>
                <li>Start / goal</li>
                <li>Obstacles</li>
                <li>Move model <span class="pill-mini assume">assumption</span></li>
              </ul>
            </li>
            <li class="tree-item nest">Numerics
              <ul>
                <li>Heuristic</li>
                <li>Step cost</li>
              </ul>
            </li>
            <li class="tree-item nest">Simulation runs
              <ul id="run-tree">
                <li class="muted-item">No runs yet</li>
              </ul>
            </li>
          </ul>
        </div>
        <div class="job-status">
          <div class="job-title">Job status</div>
          <div class="job-line" id="job-status">Idle — load a paper to begin</div>
        </div>
      </aside>

      <main class="viewport">
        <section id="panel-upload" class="panel panel-doc">
          <div class="doc-card">
            <h2>Upload research paper</h2>
            <p class="muted">Drop a PDF that describes a model, algorithm, equations, or experimental setup. This prototype ships with a path-planning demo.</p>
            <div class="drop" id="drop">
              <p><b>Drop a PDF here</b> or choose a file</p>
              <p class="muted">File is not sent to a server; the demo method pack is loaded.</p>
              <input type="file" id="file" accept=".pdf,application/pdf">
            </div>
            <div class="row">
              <button type="button" class="btn primary" id="use-demo">Use path-planning demo</button>
              <span class="muted" id="upload-status">No paper loaded yet.</span>
            </div>
          </div>
        </section>

        <section id="panel-understand" class="panel panel-doc" hidden>
          <div class="doc-card">
            <h2 id="method-title">Method</h2>
            <p id="method-line"></p>
            <p class="muted" id="method-paper"></p>
          </div>
          <div class="doc-grid3">
            <div class="doc-card">
              <h3>Can simulate</h3>
              <ul id="list-yes"></ul>
            </div>
            <div class="doc-card warn">
              <h3>Partial / ambiguous</h3>
              <ul id="list-partial"></ul>
            </div>
            <div class="doc-card danger">
              <h3>Missing from the paper</h3>
              <ul id="list-missing"></ul>
            </div>
          </div>
          <div class="doc-grid2">
            <div class="doc-card">
              <h3>Supported by the paper</h3>
              <ul id="list-supported"></ul>
            </div>
            <div class="doc-card warn">
              <h3>Assumptions for this simulation</h3>
              <ul id="list-assumptions"></ul>
            </div>
          </div>
          <div class="row">
            <button type="button" class="btn primary" data-go="simulate">Open workbench simulation</button>
          </div>
        </section>

        <section id="panel-simulate" class="panel panel-sim" hidden>
          <div class="canvas-stage">
            <div class="canvas-hint" id="sim-hint">Click free cell = start · Shift-click = goal · Alt-click = obstacle</div>
            <canvas id="world" width="960" height="640" aria-label="Simulation grid"></canvas>
            <div class="legend" id="legend">
              <span><i class="sw start"></i> Start</span>
              <span><i class="sw goal"></i> Goal</span>
              <span><i class="sw obstacle"></i> Obstacle</span>
              <span><i class="sw path"></i> Path</span>
              <span><i class="sw expanded"></i> Expanded</span>
            </div>
            <div class="gizmo" aria-hidden="true">
              <span class="gx">X</span><span class="gy">Y</span><span class="gz">grid</span>
            </div>
          </div>
          <aside class="float-panels" id="float-panels">
            <details class="fpanel" open>
              <summary>Scene</summary>
              <div class="fpanel-body">
                <label>Heuristic
                  <select id="heuristic">
                    <option value="manhattan">Manhattan</option>
                    <option value="euclidean">Euclidean</option>
                    <option value="none">None (Dijkstra)</option>
                  </select>
                </label>
                <label class="check"><input type="checkbox" id="diagonal"> Diagonal moves <span class="pill-mini assume">assumption</span></label>
              </div>
            </details>
            <details class="fpanel" open id="stats-panel">
              <summary>Statistics</summary>
              <div class="fpanel-body">
                <dl class="kv" id="run-stats">
                  <dt>Status</dt><dd>—</dd>
                </dl>
              </div>
            </details>
          </aside>
        </section>

        <section id="panel-results" class="panel panel-doc" hidden>
          <div class="doc-card">
            <h2>Result interpretation</h2>
            <p id="result-story"></p>
          </div>
          <div class="doc-grid2">
            <div class="doc-card">
              <h3>Tied to the paper</h3>
              <ul id="result-supported"></ul>
            </div>
            <div class="doc-card warn">
              <h3>Still assumptions</h3>
              <ul id="result-assumptions"></ul>
            </div>
          </div>
          <div class="doc-card">
            <h3>Scenario history</h3>
            <div class="table-wrap">
              <table>
                <thead><tr><th>#</th><th>Status</th><th>Path length</th><th>Expanded</th><th>Heuristic</th></tr></thead>
                <tbody id="history"></tbody>
              </table>
            </div>
          </div>
          <div class="row">
            <button type="button" class="btn primary" data-go="simulate">Return to viewport</button>
          </div>
        </section>
      </main>
    </div>
  </div>

  <div class="connectors-panel" id="connectors-panel" hidden>
    <div class="connectors-card">
      <div class="connectors-head">
        <h2>Third-party connectors</h2>
        <button type="button" class="btn" id="connectors-close">Close</button>
      </div>
      <p class="muted">Future scope: connect out to external simulation environments. Listing only — APIs not wired yet.</p>
      <ul class="connector-list" id="connector-list"></ul>
    </div>
  </div>

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
