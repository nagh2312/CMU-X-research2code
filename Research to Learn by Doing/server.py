#!/usr/bin/env python3
"""Research to Learn by Doing — local prototype viewer (stdlib only). Default port 8803."""

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
<title>Research to Learn by Doing</title>
<link rel="stylesheet" href="/static/app.css">
</head>
<body>
  <header class="top shell">
    <div>
      <p class="eyebrow">Paper → guided practice</p>
      <h1>Research to Learn by Doing</h1>
      <p class="lede">Turn a paper’s method into a hands-on exercise: try it, see what happens, and understand how it works.</p>
    </div>
    <div class="top-actions">
      <button type="button" class="ghost connectors-btn" id="connectors-btn" aria-expanded="false" aria-controls="connectors-panel" title="Online study and course platforms">
        <svg class="plug-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M8 2v4M16 2v4M7 6h10v4a5 5 0 0 1-5 5h0a5 5 0 0 1-5-5V6z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M12 15v7M9 22h6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
        </svg>
        Connectors
      </button>
      <a class="ghost" href="https://github.com/nagh2312/CMU-X-research2code/tree/research-to-learn-by-doing/Research%20to%20Learn%20by%20Doing" target="_blank" rel="noopener">Prototype notes</a>
    </div>
  </header>

  <div class="connectors-panel" id="connectors-panel" hidden>
    <div class="connectors-card">
      <div class="connectors-head">
        <h2>Course &amp; study connectors</h2>
        <button type="button" class="btn" id="connectors-close">Close</button>
      </div>
      <p class="muted">Future scope: open related courses and study material on these platforms. Listing only for now — live APIs are not wired yet.</p>
      <ul class="connector-list" id="connector-list"></ul>
      <p class="muted">We can offer options like this so learners jump from a paper exercise to a matching online course.</p>
    </div>
  </div>

  <div class="shell">
    <nav class="steps" id="steps" aria-label="Workflow steps">
      <button type="button" class="step active" data-step="upload">1. Upload</button>
      <button type="button" class="step" data-step="method">2. Method</button>
      <button type="button" class="step" data-step="exercise">3. Exercise</button>
      <button type="button" class="step" data-step="try">4. Try it</button>
      <button type="button" class="step" data-step="explain">5. Explain</button>
      <button type="button" class="step" data-step="challenge">6. Challenge</button>
    </nav>
  </div>

  <main class="shell">
    <section id="panel-upload" class="panel">
      <div class="card highlight">
        <h2>Upload a research paper</h2>
        <p>Provide a paper with a method you want to understand. This prototype loads a ready-made lesson so you can practice without live PDF ingest.</p>
        <div class="drop" id="drop">
          <p><b>Drop a PDF here</b> or choose a file</p>
          <p class="muted">Prototype: file is not uploaded; we load the image-classification lesson pack.</p>
          <input type="file" id="file" accept=".pdf,application/pdf">
        </div>
        <div class="row">
          <button type="button" class="btn primary" id="use-demo">Use image-classification lesson</button>
          <span class="muted" id="upload-status">No paper loaded yet.</span>
        </div>
      </div>
      <div class="card">
        <h3>How this differs</h3>
        <ul class="diff-list">
          <li><b>Simulation</b> — explore what happens when you change the method.</li>
          <li><b>Research Gap</b> — decide what to investigate next.</li>
          <li><b>Learn by Doing</b> — practice the method yourself until it clicks.</li>
        </ul>
      </div>
    </section>

    <section id="panel-method" class="panel" hidden>
      <div class="card highlight">
        <h2 id="lesson-title">Method</h2>
        <p id="lesson-line"></p>
        <p class="muted" id="lesson-paper"></p>
      </div>
      <div class="card">
        <h3>What the researcher did</h3>
        <p id="core-did"></p>
        <h3>Inputs</h3>
        <p id="core-inputs"></p>
        <h3>How results were produced</h3>
        <p id="core-how"></p>
        <h3>From the paper</h3>
        <ul id="core-from"></ul>
      </div>
      <div class="card warn">
        <h3>Simplified for teaching</h3>
        <ul id="simplifications"></ul>
      </div>
      <div class="row">
        <button type="button" class="btn primary" data-go="exercise">See the exercise</button>
      </div>
    </section>

    <section id="panel-exercise" class="panel" hidden>
      <div class="card highlight">
        <h2>Hands-on exercise</h2>
        <p id="ex-goal"></p>
      </div>
      <div class="card">
        <h3>Steps</h3>
        <ol id="ex-steps"></ol>
      </div>
      <div class="card">
        <h3>Class prototypes</h3>
        <div class="proto-row" id="prototypes"></div>
      </div>
      <div class="row">
        <button type="button" class="btn primary" data-go="try">Try it yourself</button>
      </div>
    </section>

    <section id="panel-try" class="panel" hidden>
      <div class="card highlight">
        <h2>Try the classifier</h2>
        <p class="muted">Each card is a toy “image” with two features. Click <b>Run classification</b> to assign the nearest prototype. Correct / incorrect badges appear after you run.</p>
      </div>
      <div class="map-wrap card">
        <h3>Feature map</h3>
        <canvas id="fmap" width="520" height="360" aria-label="2D feature map"></canvas>
        <p class="muted">X = brightness · Y = edge-ness · large dots = class centers · small dots = samples</p>
      </div>
      <div class="sample-grid" id="samples"></div>
      <div class="row">
        <button type="button" class="btn primary" id="run-cls">Run classification</button>
        <button type="button" class="btn" id="reset-samples">Reset features</button>
        <span class="muted" id="score-line">Not run yet.</span>
      </div>
      <div class="row">
        <button type="button" class="btn" data-go="explain">Explain the results</button>
      </div>
    </section>

    <section id="panel-explain" class="panel" hidden>
      <div class="card highlight">
        <h2>What just happened</h2>
        <p id="explain-after"></p>
      </div>
      <div class="grid2">
        <div class="card">
          <h3>About mistakes</h3>
          <p id="explain-mistakes"></p>
        </div>
        <div class="card">
          <h3>Link to the paper</h3>
          <p id="explain-paper"></p>
        </div>
      </div>
      <div class="card">
        <h3>Evidence boundaries</h3>
        <div class="grid2">
          <div>
            <h4>From the paper</h4>
            <ul id="bound-paper"></ul>
          </div>
          <div>
            <h4>Simplified for teaching</h4>
            <ul id="bound-simple"></ul>
          </div>
        </div>
      </div>
      <div class="row">
        <button type="button" class="btn primary" data-go="challenge">Take the challenge</button>
      </div>
    </section>

    <section id="panel-challenge" class="panel" hidden>
      <div class="card highlight">
        <h2 id="chal-title">Challenge</h2>
        <p id="chal-prompt"></p>
      </div>
      <div class="card" id="chal-controls"></div>
      <div class="row">
        <button type="button" class="btn primary" id="chal-run">Run on this sample</button>
        <span class="muted" id="chal-status"></span>
      </div>
      <div class="card ok" id="chal-success" hidden>
        <p id="chal-success-text"></p>
      </div>
      <div class="row">
        <button type="button" class="btn" data-go="try">Back to all samples</button>
      </div>
    </section>
  </main>

  <footer class="foot shell">
    <p>Server port <b>8803</b> — separate from Simulation (8801) and Research Gap (8802). Prototype only.</p>
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
    ap = argparse.ArgumentParser(description="Research to Learn by Doing prototype viewer")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8803)
    args = ap.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Research to Learn by Doing at http://{args.host}:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
