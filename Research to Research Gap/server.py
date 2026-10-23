#!/usr/bin/env python3
"""Research to Research Gap — local prototype viewer (stdlib only). Default port 8802."""

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
<title>Research to Research Gap</title>
<link rel="stylesheet" href="/static/app.css">
</head>
<body>
  <div class="app">
    <header class="topbar">
      <div class="topbar-left">
        <span class="brand">Research to Research Gap</span>
        <span class="proj-name" id="proj-name">Gap analysis project</span>
        <span class="badge-private">PRIVATE</span>
      </div>
      <div class="topbar-right">
        <a class="tb-link" href="https://github.com/nagh2312/CMU-X-research2code/tree/research-to-research-gap/Research%20to%20Research%20Gap" target="_blank" rel="noopener">Docs</a>
        <span class="tb-muted">Workbench · :8802</span>
      </div>
    </header>

    <div class="toolbar" role="toolbar" aria-label="Analysis tools">
      <div class="tool-group">
        <span class="tool-label">Paper</span>
        <button type="button" class="tool" data-go="upload" title="Upload"><span class="ticon">⬆</span><span>Upload</span></button>
        <button type="button" class="tool" data-go="understand" title="Understand"><span class="ticon">☰</span><span>Understand</span></button>
      </div>
      <div class="tool-group">
        <span class="tool-label">Analysis</span>
        <button type="button" class="tool" data-go="gaps" title="Gaps"><span class="ticon">◇</span><span>Gaps</span></button>
        <button type="button" class="tool" data-go="next" title="Next steps"><span class="ticon">⇢</span><span>Next</span></button>
      </div>
      <div class="tool-group">
        <span class="tool-label">Opportunity</span>
        <button type="button" class="tool primary-tool" data-go="adjacency" title="Adjacency &amp; market"><span class="ticon">▣</span><span>Adjacency</span></button>
        <button type="button" class="tool" id="m-check-toolbar" title="Check market credibility"><span class="ticon">✓</span><span>Check market</span></button>
      </div>
    </div>

    <div class="workbench">
      <aside class="tree" aria-label="Project tree">
        <div class="tree-section">
          <button type="button" class="tree-h">Paper</button>
          <ul class="tree-list">
            <li class="tree-item muted-item" id="tree-paper">No paper loaded</li>
          </ul>
        </div>
        <div class="tree-section">
          <button type="button" class="tree-h">Workflow</button>
          <ul class="tree-list" id="steps">
            <li><button type="button" class="tree-item step active" data-step="upload">Paper upload</button></li>
            <li><button type="button" class="tree-item step" data-step="understand" disabled>Understand findings</button></li>
            <li><button type="button" class="tree-item step" data-step="gaps" disabled>Gap assessment</button></li>
            <li><button type="button" class="tree-item step" data-step="next" disabled>Next steps</button></li>
            <li><button type="button" class="tree-item step" data-step="adjacency" disabled>Adjacency &amp; market</button></li>
          </ul>
        </div>
        <div class="tree-section">
          <button type="button" class="tree-h">Assessment</button>
          <ul class="tree-list">
            <li class="tree-item nest">Gap status
              <ul id="gap-tree">
                <li class="muted-item">Not assessed yet</li>
              </ul>
            </li>
            <li class="tree-item nest">Market check
              <ul id="market-tree">
                <li class="muted-item">No check yet</li>
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
            <p>Provide the paper you want to build on. This prototype ships with demos so you can try the full loop without live PDF ingest.</p>
            <div class="drop" id="drop">
              <p><b>Drop a PDF here</b> or choose a file</p>
              <p class="muted">Prototype: file is not uploaded to a backend; we load a demo pack.</p>
              <input type="file" id="file" accept=".pdf,application/pdf">
            </div>
            <div class="row">
              <button type="button" class="btn primary" id="use-demo">Use autonomous-driving demo</button>
              <button type="button" class="btn" id="use-closed">Demo: no clear gap</button>
              <span class="muted" id="upload-status">No paper loaded yet.</span>
            </div>
          </div>
        </section>

        <section id="panel-understand" class="panel panel-doc" hidden>
          <div class="card highlight">
            <h2 id="paper-title">Paper</h2>
            <p id="paper-line"></p>
            <p class="muted" id="paper-meta"></p>
          </div>
          <div class="card">
            <h3>Research question</h3>
            <p id="rq"></p>
            <h3>Methodology</h3>
            <p id="method"></p>
          </div>
          <div class="grid2">
            <div class="card">
              <h3>Main findings</h3>
              <ul id="findings"></ul>
            </div>
            <div class="card warn">
              <h3>Limitations</h3>
              <ul id="limitations"></ul>
            </div>
          </div>
          <div class="card">
            <h3>Conclusions</h3>
            <ul id="conclusions"></ul>
          </div>
          <div class="row">
            <button type="button" class="btn primary" data-go="gaps">Check for a research gap</button>
          </div>
        </section>

        <section id="panel-gaps" class="panel panel-doc" hidden>
          <div class="card" id="gap-verdict"></div>
          <div class="grid2">
            <div class="card">
              <h3>Author-acknowledged gaps</h3>
              <p class="muted">Explicitly left open or stated as limitation / future need in the paper.</p>
              <div id="gaps-author"></div>
            </div>
            <div class="card warn">
              <h3>Inferred from the paper</h3>
              <p class="muted">Suggested by what the paper did <em>not</em> measure — not proof the gap is new in the whole field.</p>
              <div id="gaps-inferred"></div>
            </div>
          </div>
          <div class="card">
            <h3>Authors’ stated future work</h3>
            <div id="future-work"></div>
          </div>
          <div class="card danger">
            <h3>Evidence boundaries</h3>
            <div class="grid2">
              <div>
                <h4>From the uploaded paper</h4>
                <ul id="bound-paper"></ul>
              </div>
              <div>
                <h4>Would need related literature</h4>
                <ul id="bound-lit"></ul>
              </div>
            </div>
          </div>
          <div class="row">
            <button type="button" class="btn primary" data-go="next">See prioritized next steps</button>
          </div>
        </section>

        <section id="panel-next" class="panel panel-doc" hidden>
          <div class="card highlight">
            <h2>Prioritized next steps</h2>
            <p class="muted">What each step involves and what it could help establish. Extensions that are not paper-supported gaps are labeled clearly.</p>
          </div>
          <div id="next-steps"></div>
          <div class="card" id="no-gap-box" hidden>
            <h3>When no clear gap exists</h3>
            <p id="no-gap-when" class="muted"></p>
            <ul id="no-gap-suggestions"></ul>
          </div>
          <div class="row">
            <button type="button" class="btn primary" data-go="adjacency">Adjacency opportunity &amp; market sizing</button>
          </div>
        </section>

        <section id="panel-adjacency" class="panel panel-doc" hidden>
          <div class="card highlight">
            <h2>Adjacency opportunity</h2>
            <p>What else can be explored <b>without going far</b> from the main topic.</p>
            <p class="muted" id="adj-anchor"></p>
            <p class="muted" id="adj-rule"></p>
          </div>
          <div id="adj-list"></div>

          <div class="card">
            <h2>TAM, SAM, and SOM</h2>
            <p class="muted" id="market-context"></p>
            <div class="grid3" id="market-defs"></div>
            <h3>How these are calculated</h3>
            <ul id="market-how"></ul>
            <div class="funnel" aria-hidden="true">
              <div class="funnel-tier tam">TAM — broadest</div>
              <div class="funnel-tier sam">SAM — filtered</div>
              <div class="funnel-tier som">SOM — obtainable</div>
            </div>
          </div>

          <div class="card">
            <h2>Enter known market figures &amp; check credibility</h2>
            <p class="muted">Paste numbers you already have (reports, bottom-up models). We only check internal consistency and basic plausibility — not whether a source is “true.”</p>
            <div class="market-form">
              <label>Currency <input id="m-currency" type="text" value="USD"></label>
              <label>Year <input id="m-year" type="number" min="1990" max="2100" value="2024"></label>
              <label>Method
                <select id="m-method">
                  <option value="top_down">Top-down (report → filters)</option>
                  <option value="bottom_up">Bottom-up (units × price)</option>
                  <option value="mixed">Mixed</option>
                </select>
              </label>
              <label>TAM <input id="m-tam" type="number" min="0" step="any" placeholder="e.g. 42000000000"></label>
              <label>TAM source <input id="m-tam-src" type="text" placeholder="Report name / URL / note"></label>
              <label>SAM <input id="m-sam" type="number" min="0" step="any"></label>
              <label>SAM source <input id="m-sam-src" type="text"></label>
              <label>SOM <input id="m-som" type="number" min="0" step="any"></label>
              <label>SOM source <input id="m-som-src" type="text"></label>
            </div>
            <div class="row">
              <button type="button" class="btn primary" id="m-check">Check credibility</button>
              <button type="button" class="btn" id="m-fill-demo">Fill demo defaults</button>
            </div>
            <div id="m-result" class="cred-result" hidden></div>
          </div>
        </section>
      </main>
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
    ap = argparse.ArgumentParser(description="Research to Research Gap prototype viewer")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8802)
    args = ap.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Research to Research Gap at http://{args.host}:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
