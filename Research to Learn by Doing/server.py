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
  <div class="app">
    <header class="topbar">
      <div class="topbar-left">
        <span class="brand">Research to Learn by Doing</span>
        <span class="proj-name" id="proj-name">Learning project</span>
        <span class="badge-private">PRIVATE</span>
      </div>
      <div class="topbar-right">
        <button type="button" class="tb-link" id="connectors-btn" aria-expanded="false" aria-controls="connectors-panel">Connectors</button>
        <a class="tb-link" href="https://github.com/nagh2312/CMU-X-research2code/tree/research-to-learn-by-doing/Research%20to%20Learn%20by%20Doing" target="_blank" rel="noopener">Docs</a>
        <span class="tb-muted">Workbench · :8803</span>
      </div>
    </header>

    <div class="toolbar" role="toolbar" aria-label="Lesson tools">
      <div class="tool-group">
        <span class="tool-label">Paper</span>
        <button type="button" class="tool" data-go="upload" title="Upload"><span class="ticon">⬆</span><span>Upload</span></button>
        <button type="button" class="tool" data-go="method" title="Method"><span class="ticon">☰</span><span>Method</span></button>
      </div>
      <div class="tool-group">
        <span class="tool-label">Practice</span>
        <button type="button" class="tool" data-go="exercise" title="Exercise"><span class="ticon">▦</span><span>Exercise</span></button>
        <button type="button" class="tool primary-tool" id="run-cls" title="Run classification"><span class="ticon">▶</span><span>Run</span></button>
        <button type="button" class="tool" id="reset-samples" title="Reset"><span class="ticon">↺</span><span>Reset</span></button>
      </div>
      <div class="tool-group">
        <span class="tool-label">Learn</span>
        <button type="button" class="tool" data-go="explain" title="Explain"><span class="ticon">◉</span><span>Explain</span></button>
        <button type="button" class="tool" data-go="challenge" title="Challenge"><span class="ticon">◇</span><span>Challenge</span></button>
        <button type="button" class="tool" id="open-coursera-tool" title="Open Coursera demo"><span class="ticon">▣</span><span>Coursera</span></button>
      </div>
    </div>

    <div class="workbench">
      <aside class="tree" aria-label="Project tree">
        <div class="tree-section">
          <button type="button" class="tree-h">Lesson</button>
          <ul class="tree-list">
            <li class="tree-item muted-item" id="tree-paper">No paper loaded</li>
          </ul>
        </div>
        <div class="tree-section">
          <button type="button" class="tree-h">Workflow</button>
          <ul class="tree-list" id="steps">
            <li><button type="button" class="tree-item step active" data-step="upload">Paper upload</button></li>
            <li><button type="button" class="tree-item step" data-step="method" disabled>Method</button></li>
            <li><button type="button" class="tree-item step" data-step="exercise" disabled>Exercise</button></li>
            <li><button type="button" class="tree-item step" data-step="try" disabled>Try it</button></li>
            <li><button type="button" class="tree-item step" data-step="explain" disabled>Explain</button></li>
            <li><button type="button" class="tree-item step" data-step="challenge" disabled>Challenge</button></li>
          </ul>
        </div>
        <div class="tree-section">
          <button type="button" class="tree-h">Connectors</button>
          <ul class="tree-list">
            <li class="tree-item nest">Learning platforms
              <ul>
                <li><button type="button" class="tree-link" id="tree-coursera">Coursera</button></li>
                <li class="muted-item">edX <span class="pill-mini">soon</span></li>
                <li class="muted-item">Udacity <span class="pill-mini">soon</span></li>
                <li class="muted-item">Khan Academy <span class="pill-mini">soon</span></li>
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

        <section id="panel-method" class="panel panel-doc" hidden>
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

        <section id="panel-exercise" class="panel panel-doc" hidden>
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

        <section id="panel-try" class="panel panel-doc" hidden>
          <div class="card highlight">
            <h2>Try the classifier</h2>
            <p class="muted">Each card is a toy “image” with two features. Click <b>Run</b> (toolbar or below) to assign the nearest prototype.</p>
          </div>
          <div class="map-wrap card">
            <h3>Feature map</h3>
            <canvas id="fmap" width="520" height="360" aria-label="2D feature map"></canvas>
            <p class="muted">X = brightness · Y = edge-ness · large dots = class centers · small dots = samples</p>
          </div>
          <div class="sample-grid" id="samples"></div>
          <div class="row">
            <button type="button" class="btn primary" id="run-cls-panel">Run classification</button>
            <span class="muted" id="score-line">Not run yet.</span>
          </div>
          <div class="row">
            <button type="button" class="btn" data-go="explain">Explain the results</button>
          </div>
        </section>

        <section id="panel-explain" class="panel panel-doc" hidden>
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

        <section id="panel-challenge" class="panel panel-doc" hidden>
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
    </div>
  </div>

  <div class="connectors-panel" id="connectors-panel" hidden>
    <div class="connectors-card">
      <div class="connectors-head">
        <h2>Course &amp; study connectors</h2>
        <button type="button" class="btn" id="connectors-close">Close</button>
      </div>
      <p class="muted">Hierarchical learning platforms. Select <b>Coursera</b> to open a Coursera-style study page for this lesson’s topic.</p>
      <ul class="connector-tree" id="connector-list"></ul>
    </div>
  </div>

  <script src="/static/app.js"></script>
</body>
</html>
"""

COURSERA_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Coursera — Image classification (demo)</title>
<link rel="stylesheet" href="/static/coursera.css">
</head>
<body class="cr-body">
  <a class="cr-skip" href="#main">Skip to content</a>
  <header class="cr-top">
    <div class="cr-top-inner">
      <a class="cr-logo" href="/coursera" aria-label="Coursera home">coursera</a>
      <button type="button" class="cr-explore" id="cr-explore">Explore</button>
      <form class="cr-search" role="search" onsubmit="return false;">
        <input type="search" id="cr-q" placeholder="What do you want to learn?" aria-label="Search">
        <button type="submit" class="cr-search-btn" aria-label="Search">⌕</button>
      </form>
      <nav class="cr-nav">
        <a href="#courses">Degrees</a>
        <a href="#videos">Videos</a>
        <a href="#articles">Articles</a>
        <a href="/">← Learn by Doing</a>
      </nav>
    </div>
  </header>

  <div class="cr-banner">
    <div class="cr-banner-inner">
      <p class="cr-eyebrow">Demo catalog · matched to your lesson</p>
      <h1 id="cr-hero-title">Learn image classification by doing</h1>
      <p id="cr-hero-sub" class="cr-hero-sub"></p>
      <p class="cr-disclaimer">Illustrative Coursera-style UI for this prototype — not affiliated with or operated by Coursera, Inc.</p>
    </div>
  </div>

  <main id="main" class="cr-main">
    <section class="cr-section" id="courses">
      <div class="cr-section-head">
        <h2>Courses</h2>
        <p class="cr-muted">University &amp; industry courses for this topic</p>
      </div>
      <div class="cr-course-grid" id="cr-courses"></div>
    </section>

    <section class="cr-section" id="videos">
      <div class="cr-section-head">
        <h2>Videos to watch</h2>
        <p class="cr-muted">Short lessons that mirror the hands-on exercise</p>
      </div>
      <div class="cr-list" id="cr-videos"></div>
    </section>

    <section class="cr-section" id="articles">
      <div class="cr-section-head">
        <h2>Articles &amp; reading</h2>
        <p class="cr-muted">Guides and notes to read alongside practice</p>
      </div>
      <div class="cr-list" id="cr-articles"></div>
    </section>

    <section class="cr-section" id="news">
      <div class="cr-section-head">
        <h2>Latest &amp; published news</h2>
        <p class="cr-muted">What is happening in vision &amp; classification</p>
      </div>
      <div class="cr-list" id="cr-news"></div>
    </section>

    <section class="cr-section" id="journals">
      <div class="cr-section-head">
        <h2>Journals &amp; papers</h2>
        <p class="cr-muted">Foundational publications for deeper study</p>
      </div>
      <div class="cr-list" id="cr-journals"></div>
    </section>
  </main>

  <footer class="cr-foot">
    <div class="cr-foot-inner">
      <p><b>coursera</b> demo page · Research to Learn by Doing</p>
      <p><a href="/">Back to workbench</a> · Port 8803</p>
    </div>
  </footer>
  <script src="/static/coursera.js"></script>
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
        if path in ("/coursera", "/coursera/"):
            return self._send(200, COURSERA_HTML.encode("utf-8"), "text/html; charset=utf-8")
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
    print(f"Coursera demo page at http://{args.host}:{args.port}/coursera")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
