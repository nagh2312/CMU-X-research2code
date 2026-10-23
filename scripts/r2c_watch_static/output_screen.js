// Output screen: a tab row shown on the run page once a run has finished.
// "Code" is the existing page content (#panel-code), untouched. Every other
// tab loads /tab/<name> once, caches it, and renders into #panel-tab, so
// switching tabs never reloads the page or restarts anything.
(function () {
  const TABS = [
    ["code", "Code"],
    ["dataset", "Dataset"],
    ["experiment", "Experiment"],
    ["decision", "Decision"],
    ["teaching", "Teaching Module"],
    ["graph", "Knowledge Graph"],
    ["evidence", "Evidence Card"],
  ];
  const QS = RUN_SLUG ? `?run=${encodeURIComponent(RUN_SLUG)}` : "";
  const cache = {};
  const renderers = {};
  let active = "code";
  let shown = false;

  const esc = (v) => (v === null || v === undefined ? "" : String(v)).replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[ch]));
  const panel = () => document.getElementById("panel-tab");

  function table(headers, rows) {
    return `<table><thead><tr>${headers.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead>
      <tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
  }
  const pill = (text, cls) => `<span class="pill ${cls}">${esc(text)}</span>`;
  const fmtBytes = (n) => n >= 1e6 ? `${(n / 1e6).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1e3))} KB`;
  const link = (url, text) => url ? `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(text || url)}</a>` : "";

  function buildTabs() {
    const nav = document.getElementById("output-tabs");
    nav.innerHTML = TABS.map(([id, label]) =>
      `<button type="button" class="out-tab" data-tab="${id}">${esc(label)}</button>`).join("");
    nav.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-tab]");
      if (btn) select(btn.dataset.tab);
    });
  }

  function select(name) {
    if (!TABS.some(([id]) => id === name)) name = "code";
    active = name;
    document.querySelectorAll(".out-tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
    document.getElementById("panel-code").hidden = name !== "code";
    panel().hidden = name === "code";
    history.replaceState(null, "", name === "code" ? location.pathname : `#tab=${name}`);
    if (name !== "code") load(name, false);
  }

  async function load(name, force) {
    if (cache[name] && !force) return draw(name);
    panel().innerHTML = `<div class="out-state"><span class="out-spinner"></span>Building the ${esc(label(name))} view...</div>`;
    try {
      const res = await fetch(`/tab/${name}${QS}`, { cache: "no-store" });
      const body = await res.json();
      if (!res.ok) throw new Error(body.error || `HTTP ${res.status}`);
      cache[name] = body;
      if (active === name) draw(name);
    } catch (err) {
      if (active !== name) return;
      panel().innerHTML = `<div class="out-state error">
        <p>The ${esc(label(name))} view could not be built: ${esc(err.message)}</p>
        <button type="button" class="out-btn primary" id="out-retry">Retry</button></div>`;
      document.getElementById("out-retry").onclick = () => load(name, true);
    }
  }

  function draw(name) {
    const fn = renderers[name];
    panel().innerHTML = fn ? fn(cache[name]) : `<div class="out-state">This view is not available yet.</div>`;
    if (fn && fn.after) fn.after(cache[name]);
  }

  const label = (name) => (TABS.find(([id]) => id === name) || [name, name])[1];

  function onState(data) {
    const finished = data && data.run_status && !["running", "waiting"].includes(data.run_status);
    if (!finished || shown) return;
    shown = true;
    document.getElementById("output-tabs").hidden = false;
    const fromHash = (location.hash.match(/tab=([a-z]+)/) || [])[1];
    select(fromHash || "code");
  }

  // Background jobs (dataset fetch, seed runs, ...). The server keeps state
  // per run+kind, so the status line survives a page reload.
  async function startJob(kind, params) {
    const res = await fetch(`/action/${kind}${QS}`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(params || {}),
    });
    const body = await res.json();
    if (!res.ok) throw new Error(body.error || `HTTP ${res.status}`);
    return body;
  }
  async function jobStatus(kind) {
    const res = await fetch(`/job/${kind}${QS}`, { cache: "no-store" });
    return res.json();
  }
  // Paints a job's status into `el` and polls until it ends; `onDone` gets the final state.
  function watchJob(kind, el, onDone) {
    const paint = (s) => {
      if (!el) return;
      if (s.status === "running") el.innerHTML = `<span class="out-spinner"></span>${esc(s.message || "Working...")}`;
      else if (s.status === "failed") el.innerHTML = `Failed: ${esc(s.message)} <button type="button" class="out-btn" data-retry-job="${kind}">Retry</button>`;
      else if (s.status === "done") el.textContent = s.message || "Finished.";
      else el.textContent = "";
      el.className = `out-job is-${s.status || "idle"}`;
    };
    const tick = async () => {
      let s;
      try { s = await jobStatus(kind); } catch (e) { s = { status: "failed", message: e.message }; }
      paint(s);
      if (s.status === "running") setTimeout(tick, 1500);
      else if (onDone) onDone(s);
    };
    tick();
  }
  async function runJob(kind, params, el, onDone) {
    try {
      await startJob(kind, params);
    } catch (err) {
      if (el) { el.className = "out-job is-failed"; el.textContent = `Could not start: ${err.message}`; }
      return;
    }
    watchJob(kind, el, onDone);
  }
  // Retry buttons inside job status lines re-run the job with its last params.
  document.addEventListener("click", async (e) => {
    const btn = e.target.closest("[data-retry-job]");
    if (!btn) return;
    const kind = btn.dataset.retryJob;
    const s = await jobStatus(kind);
    runJob(kind, s.params || {}, btn.parentElement, () => load(active, true));
  });

  function downloadCsv(filename, columns, rows) {
    const cell = (v) => /[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v);
    const text = [columns, ...rows].map((r) => r.map(cell).join(",")).join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type: "text/csv" }));
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  // ---------------------------------------------------------------- Dataset
  const AVAILABILITY = {
    public: ["Public", "completed"],
    needs_login: ["Needs a login", "degraded"],
    not_found: ["Not found online", "halted"],
  };

  function syntheticBlock(s) {
    return `<div class="out-card out-warn">
      <h2>${pill("Synthetic", "degraded")} Small synthetic sample</h2>
      <p>${esc(s.warning)}</p>
      <p class="out-muted">${esc(s.note)}</p>
      ${table(s.columns, s.rows.map((r) => r.map(esc)))}
      <div class="out-row"><button type="button" class="out-btn" id="out-synth-dl">Download synthetic CSV</button></div>
    </div>`;
  }

  renderers.dataset = (d) => {
    const cards = d.datasets.map((ds) => {
      const [avail, cls] = AVAILABILITY[ds.availability] || ["Unknown", "pending"];
      const schema = ds.schema
        ? `<h3>Schema <span class="out-muted">(${esc(ds.schema_origin)})</span></h3>${table(["Field", "What it means"], ds.schema.map((r) => [esc(r.field), esc(r.meaning)]))}`
        : "";
      const fetched = ds.fetched
        ? `<p>${pill("Public", "completed")} Fetched into <code>${esc(ds.fetched.folder)}</code>: ${ds.fetched.files.map((f) => `${esc(f.file)} (${fmtBytes(f.bytes)}${f.truncated ? ", cut off at the size limit" : ""})`).join(", ")}</p>`
        : "";
      const actions = ds.availability === "not_found" ? "" : `<div class="out-row">
          ${ds.download_urls[0] ? `<a class="out-btn" href="${esc(ds.download_urls[0])}" target="_blank" rel="noopener">Download from source</a>` : ""}
          ${ds.fetchable ? `<button type="button" class="out-btn primary" data-fetch="${esc(ds.id)}">${ds.fetched ? "Fetch again" : "Fetch into project"}</button>` : ""}
        </div>
        ${ds.fetch_note ? `<p class="out-muted">${esc(ds.fetch_note)}</p>` : ""}
        <div class="out-job" data-fetch-status="${esc(ds.id)}"></div>`;
      const missing = ds.availability === "not_found"
        ? `<p>We could not find a public copy of this dataset. It may be private or not available online. The schema below is built from the paper text instead.</p>`
        : "";
      return `<div class="out-card">
        <h2>${esc(ds.name)} ${pill(avail, cls)}</h2>
        ${missing}
        <dl class="out-kv">
          <dt>Source</dt><dd>${link(ds.source) || "Not available"}</dd>
          <dt>Size</dt><dd>${esc(ds.size || "Unknown")}</dd>
          <dt>Format</dt><dd>${esc(ds.format || "Unknown")}</dd>
        </dl>
        ${schema}${fetched}${actions}
      </div>`;
    }).join("");

    const noPublic = !d.any_public;
    return `
      <div class="out-card out-highlight">
        <h2>Datasets used by the paper</h2>
        <p>${d.datasets.length ? `The paper names ${d.datasets.length} dataset(s) or data link(s).` : "The paper does not name a dataset."}
          ${d.demo_data ? `Note on the demo data: ${esc(d.demo_data)}` : ""}</p>
      </div>
      ${noPublic ? `<div class="out-card out-warn"><h2>The paper's data is not publicly available</h2>
        <p>We could not find a public source for the data this paper used. The schema below is built from the paper text, and the sample further down is synthetic.</p></div>` : ""}
      ${cards}
      <div class="out-card">
        <h2>Schema from the paper text</h2>
        <p class="out-muted">${esc(d.paper_schema_origin)}. Use this when the real data is not available.</p>
        ${d.paper_schema.length ? table(["Field", "What it means"], d.paper_schema.map((r) => [esc(r.field), esc(r.meaning)])) : "<p>The paper text does not describe the data format.</p>"}
      </div>
      ${noPublic ? syntheticBlock(d.synthetic) : `<div class="out-row"><button type="button" class="out-btn" id="out-synth-show">Show a synthetic sample (not the paper's data)</button></div><div id="out-synth"></div>`}`;
  };
  renderers.dataset.after = (d) => {
    const wireDownload = () => {
      const btn = document.getElementById("out-synth-dl");
      if (btn) btn.onclick = () => downloadCsv(`${RUN_SLUG}-SYNTHETIC-sample.csv`, d.synthetic.columns, d.synthetic.rows);
    };
    wireDownload();
    const show = document.getElementById("out-synth-show");
    if (show) show.onclick = () => { document.getElementById("out-synth").innerHTML = syntheticBlock(d.synthetic); show.remove(); wireDownload(); };
    panel().querySelectorAll("[data-fetch]").forEach((btn) => {
      btn.onclick = () => {
        const statusEl = panel().querySelector(`[data-fetch-status="${btn.dataset.fetch}"]`);
        runJob("dataset_fetch", { dataset_id: btn.dataset.fetch }, statusEl, (s) => { if (s.status === "done") load("dataset", true); });
      };
    });
    // Resume showing an in-flight fetch after a tab switch or reload.
    jobStatus("dataset_fetch").then((s) => {
      if (s.status !== "running" && s.status !== "failed") return;
      const id = (s.params || {}).dataset_id;
      const statusEl = panel().querySelector(`[data-fetch-status="${id}"]`);
      if (statusEl) watchJob("dataset_fetch", statusEl, (f) => { if (f.status === "done") load("dataset", true); });
    });
  };

  // ------------------------------------------------------------- Experiment
  const RESULT_PILL = { pass: "completed", fail: "halted", warn: "degraded", flag_for_researcher: "degraded", unprobeable: "pending", not_applicable: "pending" };
  const STRENGTH_PILL = { Strong: "completed", Weak: "degraded", Unchecked: "pending", "No test": "halted" };
  const num = (v) => typeof v === "number" ? (Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(3)) : esc(v);

  function rangeOf(values) {
    if (!values.length) return null;
    const min = Math.min(...values), max = Math.max(...values);
    return { min, max, mean: values.reduce((a, b) => a + b, 0) / values.length, n: values.length };
  }
  const rangeText = (r) => !r ? "No result yet" : r.n === 1 ? `${num(r.min)} (1 run)` : `${num(r.min)} to ${num(r.max)} (mean ${num(r.mean)}, ${r.n} runs)`;

  function experimentResults(d, metric) {
    const seeded = d.runs.filter((r) => r.kind !== "own_data");
    const values = seeded.filter((r) => r.status === "done" && metric in (r.metrics || {})).map((r) => r.metrics[metric]);
    const rows = d.runs.map((r) => [
      esc(r.label) + (r.seed !== null && r.seed !== undefined && r.kind !== "seed" ? ` <span class="out-muted">(seed ${esc(r.seed)})</span>` : ""),
      r.kind === "own_data" ? pill("Your data", "running") : pill("Demo data", "pending"),
      r.status === "failed" ? `<span class="out-muted">Failed: ${esc(r.error)}</span>` : (metric in (r.metrics || {}) ? num(r.metrics[metric]) : `<span class="out-muted">not reported</span>`),
    ]);
    const paperRows = d.paper_numbers.filter((p) => metric.includes(String(p.metric || "").toLowerCase()));
    const r = rangeOf(values);
    const gapRows = paperRows.map((p) => [esc(p.claim), num(p.paper_value), rangeText(r),
      r ? `${r.mean - p.paper_value >= 0 ? "+" : ""}${num(r.mean - p.paper_value)} (mean minus paper)` : "—"]);
    return `
      <p><b>${esc(metric)}</b> across seeded runs on the demo data: ${rangeText(r)}</p>
      ${table(["Run", "Data", esc(metric)], rows)}
      <h3>Paper number vs rebuilt number</h3>
      ${gapRows.length ? table(["Paper claim", "Paper", "Rebuilt (range)", "Gap"], gapRows)
        : `<p class="out-muted">The paper does not state a single ${esc(metric)} number we could line up with this run, so no gap is shown.
            What the paper reports: ${esc(d.paper_claimed_results || "not stated")}</p>`}
      <p class="out-muted">The rebuilt numbers come from a small demo-scale run${d.paper_scale ? `; the paper used ${esc(String(d.paper_scale).replace(/\.+$/, ""))}` : ""}.
        A gap is expected, and a small gap does not mean the paper's result was reproduced.</p>`;
  }

  renderers.experiment = (d) => {
    const works = d.works.verdict === "succeeded"
      ? `<p><b>Yes, at demo scale.</b> ${esc(d.works.evidence || "")}</p>`
      : d.works.verdict ? `<p><b>Not shown.</b> The demo did not show the method working (${esc(d.works.verdict)}). ${esc(d.works.evidence || "")}</p>`
      : `<p>The run did not record a demo verdict.</p>`;
    const options = d.metric_names.map((m) => `<option value="${esc(m)}" ${m === d.default_metric ? "selected" : ""}>${esc(m)}</option>`).join("");
    return `
      <div class="out-card out-highlight">
        <h2>Does the rebuilt method work?</h2>
        ${works}
        ${d.works.decided_by ? `<p class="out-muted">How this was decided: ${esc(d.works.decided_by)}.</p>` : ""}
        ${d.label ? `<p class="out-muted">Delivery label: <b>${esc(d.label)}</b>. This is a demo-scale check, not a reproduction of the paper's numbers.</p>` : ""}
      </div>

      <div class="out-card">
        <h2>Results by measure</h2>
        ${d.metric_names.length ? `<div class="out-row"><label class="out-muted" for="out-metric">Measure that matters to you</label>
          <select class="out-btn" id="out-metric">${options}</select></div><div id="out-results"></div>`
          : "<p>The notebook did not print any measures we could read.</p>"}
        <h3>Run with different random seeds</h3>
        ${d.can_vary_seed ? `<div class="out-row">
            <input class="out-btn" id="out-seeds" value="1, 2, 3" size="14" aria-label="Seeds">
            <button type="button" class="out-btn primary" id="out-run-seeds">Run these seeds</button>
          </div>
          <p class="out-muted">Each seed re-runs the full notebook on a copy (the delivered notebook is not changed). Up to 5 seeds; each can take several minutes.</p>
          <div class="out-job" id="out-seed-status"></div>`
          : "<p class='out-muted'>The notebook has no SEED setting, so seeded re-runs are not available.</p>"}
      </div>

      <div class="out-card">
        <h2>Run the method on your own data</h2>
        ${d.can_use_own_data ? `<p class="out-muted">Expected format: ${esc(d.data_format || "see method/README.md")}</p>
          <p class="out-muted">Upload one <code>.pt</code> file, or a <code>pool.csv</code> + <code>test.csv</code> pair (last column is the label). Files are stored under <code>.pipeline/ui/uploads/</code>, not in the package.</p>
          <div class="out-row"><input type="file" class="out-btn" id="out-own-files" multiple>
            <button type="button" class="out-btn primary" id="out-own-run">Upload and run</button></div>
          <div class="out-job" id="out-own-status"></div>`
          : "<p>This package's data loader does not accept a custom file, so running on your own data is not available here.</p>"}
      </div>

      <div class="out-card">
        <h2>Test result for each module</h2>
        <p class="out-muted">Strength comes from planting a small bug and checking whether the test notices.</p>
        ${d.modules.length ? table(["Module", "Test file", "Strength", "What it means"], d.modules.map((m) =>
          [esc(m.name), m.test_file ? `<code>${esc(m.test_file)}</code>` : "—", pill(m.strength, STRENGTH_PILL[m.strength] || "pending"), esc(m.meaning)]))
          : "<p>No per-module tests were recorded.</p>"}
        <div class="out-row"><button type="button" class="out-btn" id="out-run-tests">Run the module tests now</button></div>
        <div class="out-job" id="out-tests-status"></div><div id="out-tests-result"></div>
      </div>

      <div class="out-card">
        <h2>Behavioral checks</h2>
        ${table(["Check", "Result", "Details"], d.checks.map((c) =>
          [esc(c.id), pill(c.result, RESULT_PILL[c.result] || "pending"), esc(c.message)]))}
      </div>

      <div class="out-card">
        <h2>Settings: paper vs this run</h2>
        ${table(["Setting", "Paper", "This run", "Who set it", "Why"], d.settings.map((s) => [
          `<code>${esc(s.name)}</code>`, s.paper === null || s.paper === undefined ? "not stated" : esc(s.paper), esc(s.rebuilt),
          s.source === "paper" ? pill("Paper", "completed") : pill("System guess", "degraded"), `<span class="note">${esc(s.why)}</span>`]))}
      </div>`;
  };
  renderers.experiment.after = (d) => {
    const metricSel = document.getElementById("out-metric");
    const showResults = () => { document.getElementById("out-results").innerHTML = experimentResults(d, metricSel.value); };
    if (metricSel) { metricSel.onchange = showResults; showResults(); }
    const reload = (s) => { if (s.status === "done" || s.status === "failed") load("experiment", true); };

    const seedBtn = document.getElementById("out-run-seeds");
    if (seedBtn) seedBtn.onclick = () => {
      const seeds = document.getElementById("out-seeds").value.split(/[\s,]+/).filter(Boolean).map(Number);
      runJob("experiment_seeds", { seeds }, document.getElementById("out-seed-status"), reload);
    };
    const ownBtn = document.getElementById("out-own-run");
    if (ownBtn) ownBtn.onclick = async () => {
      const files = [...document.getElementById("out-own-files").files];
      const statusEl = document.getElementById("out-own-status");
      if (!files.length) { statusEl.className = "out-job is-failed"; statusEl.textContent = "Choose a file first."; return; }
      const batch = `u${Date.now().toString(36)}`;
      statusEl.className = "out-job is-running";
      statusEl.innerHTML = `<span class="out-spinner"></span>Uploading...`;
      for (const f of files) {
        const res = await fetch(`/action/upload${QS}&batch=${batch}&name=${encodeURIComponent(f.name)}`, { method: "POST", body: f });
        if (!res.ok) { statusEl.className = "out-job is-failed"; statusEl.textContent = (await res.json()).error; return; }
      }
      runJob("own_data", { batch }, statusEl, reload);
    };
    const testsBtn = document.getElementById("out-run-tests");
    const showTests = (s) => {
      if (s.status !== "done" || !s.result) return;
      document.getElementById("out-tests-result").innerHTML = table(["Test file", "Passed", "Failed", "Skipped"],
        s.result.files.map((f) => [`<code>${esc(f.file)}</code>`, f.passed, f.failed ? `<b>${f.failed}</b>` : 0, f.skipped]));
    };
    testsBtn.onclick = () => runJob("module_tests", {}, document.getElementById("out-tests-status"), showTests);
    // Re-attach to jobs that are still running (or just finished) after a tab switch.
    [["experiment_seeds", "out-seed-status", reload], ["own_data", "out-own-status", reload], ["module_tests", "out-tests-status", showTests]].forEach(([kind, id, done]) => {
      jobStatus(kind).then((s) => {
        const el = document.getElementById(id);
        if (!el) return;
        if (s.status === "running") watchJob(kind, el, done);
        else if (s.status === "failed") watchJob(kind, el);
        else if (kind === "module_tests") showTests(s);
      });
    });
  };

  // --------------------------------------------------------------- Decision
  const ANSWER_PILL = { Yes: "completed", Likely: "completed", Partly: "degraded", "With caution": "degraded",
    "Possible, needs tuning": "degraded", No: "halted", "Not yet": "halted", "Unlikely as-is": "halted",
    "Unlikely without changes": "halted" };
  const answer = (a) => pill(a, ANSWER_PILL[a] || "pending");

  renderers.decision = (d) => `
    <div class="out-card out-highlight">
      <h2>Is this paper worth building? ${answer(d.worth.answer)}</h2>
      <p>${esc(d.worth.reason)}</p>
    </div>
    <div class="out-grid">
      <div class="out-card">
        <h2>Can it be rebuilt from the paper text alone? ${answer(d.rebuild.answer)}</h2>
        <p>${esc(d.rebuild.reason)}</p>
        <p class="out-muted">Feasibility from the method analysis: ${esc(d.rebuild.feasibility || "not recorded")}.
          Replication check: ${esc(d.rebuild.replication || "not recorded")}. Delivery label: ${esc(d.rebuild.label)}.</p>
      </div>
      <div class="out-card">
        <h2>Will it fit your data? ${answer(d.fit.likelihood)}</h2>
        <p>${esc(d.fit.reason)}</p>
        ${d.fit.requirements ? `<p class="out-muted">Your data needs to look like: ${esc(d.fit.requirements)}</p>` : ""}
        ${d.fit.you_provide.length ? `<p class="out-muted">You provide: ${d.fit.you_provide.map(esc).join("; ")}</p>` : ""}
      </div>
    </div>
    <div class="out-card">
      <h2>Which parts are worth building</h2>
      ${table(["Part", "Type", "Priority", "Test strength"], d.parts.map((p) =>
        [esc(p.name), esc(p.type), p.priority.startsWith("Core") ? `<b>${esc(p.priority)}</b>` : esc(p.priority), esc(p.test)]))}
    </div>
    <div class="out-card">
      <h2>What is missing</h2>
      ${d.missing.length ? table(["What", "Kind", "Details"], d.missing.map((m) => [esc(m.what), esc(m.kind), `<span class="note">${esc(m.why)}</span>`]))
        : "<p>Nothing is recorded as missing.</p>"}
    </div>
    <div class="out-card out-highlight">
      <h2>Recommended next step</h2>
      <p>${esc(d.next_step)}</p>
    </div>`;

  // -------------------------------------------------------- Teaching Module
  // Scores live in memory so they survive tab switches within the page.
  const quizScores = {};
  const quizPicks = {};

  renderers.teaching = (d) => {
    const s = d.summary;
    const quizzes = d.quizzes.map((quiz, qi) => `
      <div class="out-card" data-quiz="${qi}">
        <h2>Quiz ${qi + 1}: ${esc(quiz.stage)}</h2>
        ${quiz.questions.map((q, i) => `
          <div class="out-quiz-q">${i + 1}. ${esc(q.prompt)}</div>
          ${q.options.map((o, oi) => `<label class="out-option" data-q="${i}" data-o="${oi}">
            <input type="radio" name="quiz-${qi}-${i}" value="${oi}">${esc(o)}</label>`).join("")}
          <p class="out-muted" data-explain="${i}" hidden>${esc(q.explain)}</p>`).join("")}
        <div class="out-row"><button type="button" class="out-btn primary" data-check="${qi}">Check my answers</button>
          <span data-score="${qi}"></span></div>
      </div>`).join("");
    const total = d.quizzes.reduce((n, q) => n + q.questions.length, 0);
    return `
      <div class="out-card out-highlight">
        <h2>The paper in three parts</h2>
        <h3>Problem</h3><p>${esc(s.problem || "Not recorded.")}</p>
        <h3>Premise</h3><p>${esc(s.premise || "Not recorded.")}</p>
        <h3>Hypothesis</h3><p>${esc(s.hypothesis || "Not recorded.")}</p>
      </div>
      ${quizzes || "<div class='out-state'>Not enough recorded detail to build quizzes for this run.</div>"}
      <div class="out-card"><h2>Total score</h2><p id="out-quiz-total" data-total="${total}"></p></div>`;
  };
  renderers.teaching.after = (d) => {
    const totalEl = document.getElementById("out-quiz-total");
    const paintTotal = () => {
      const done = Object.keys(quizScores);
      const right = done.reduce((n, k) => n + quizScores[k], 0);
      const possible = done.reduce((n, k) => n + d.quizzes[k].questions.length, 0);
      totalEl.textContent = done.length
        ? `${right} of ${possible} correct across ${done.length} of ${d.quizzes.length} quizzes (${Math.round((100 * right) / possible)}%).`
        : `Answer a quiz and press "Check my answers" to see your score. ${totalEl.dataset.total} questions in total.`;
    };
    panel().querySelectorAll("[data-check]").forEach((btn) => {
      btn.onclick = () => {
        const qi = Number(btn.dataset.check);
        const card = panel().querySelector(`[data-quiz="${qi}"]`);
        let right = 0;
        quizPicks[qi] = {};
        d.quizzes[qi].questions.forEach((q, i) => {
          const picked = card.querySelector(`input[name="quiz-${qi}-${i}"]:checked`);
          if (picked) quizPicks[qi][i] = picked.value;
          card.querySelectorAll(`[data-q="${i}"]`).forEach((opt) => {
            const oi = Number(opt.dataset.o);
            opt.classList.toggle("right", oi === q.answer);
            opt.classList.toggle("wrong", picked && Number(picked.value) === oi && oi !== q.answer);
          });
          card.querySelector(`[data-explain="${i}"]`).hidden = false;
          if (picked && Number(picked.value) === q.answer) right += 1;
        });
        quizScores[qi] = right;
        card.querySelector(`[data-score="${qi}"]`).textContent = `Score: ${right} of ${d.quizzes[qi].questions.length}`;
        paintTotal();
      };
    });
    // Restore checked quizzes after switching back to this tab.
    Object.entries(quizPicks).forEach(([qi, picks]) => {
      Object.entries(picks).forEach(([i, v]) => {
        const input = panel().querySelector(`input[name="quiz-${qi}-${i}"][value="${v}"]`);
        if (input) input.checked = true;
      });
      panel().querySelector(`[data-check="${qi}"]`).click();
    });
    paintTotal();
  };

  // -------------------------------------------------------- Knowledge Graph
  const KIND_COLOR = { Premise: "#14532d", Hypothesis: "#854d0e", Equation: "#5b21b6", Algorithm: "#1d4ed8",
    Setting: "#374151", Claim: "#7f1d1d", Dataset: "#155e75" };
  const EDGE_COLOR = { "depends on": "#9ca3af", implements: "#93c5fd", "tested on": "#6ee7b7" };
  const NODE_W = 180, NODE_H = 36, COL_GAP = 70, ROW_GAP = 14, PAD = 16;
  const graphState = { selected: null, focus: null };

  // Columns by dependency depth: a node sits right of everything it depends on,
  // implements, or (for datasets) is tested by.
  function layoutGraph(d) {
    const before = {};
    d.nodes.forEach((n) => { before[n.id] = []; });
    d.edges.forEach((e) => {
      if (e.kind === "tested on") before[e.to].push(e.from);
      else before[e.from].push(e.to);
    });
    const depth = {};
    const visit = (id, seen) => {
      if (depth[id] !== undefined) return depth[id];
      if (seen.has(id)) return 0;
      seen.add(id);
      depth[id] = before[id].length ? 1 + Math.max(...before[id].map((p) => visit(p, seen))) : 0;
      return depth[id];
    };
    d.nodes.forEach((n) => visit(n.id, new Set()));
    const cols = {};
    d.nodes.forEach((n) => { (cols[depth[n.id]] = cols[depth[n.id]] || []).push(n); });
    const kinds = Object.keys(KIND_COLOR);
    const pos = {};
    Object.entries(cols).forEach(([c, list]) => {
      list.sort((a, b) => kinds.indexOf(a.kind) - kinds.indexOf(b.kind) || a.label.localeCompare(b.label));
      list.forEach((n, r) => { pos[n.id] = { x: PAD + c * (NODE_W + COL_GAP), y: PAD + r * (NODE_H + ROW_GAP) }; });
    });
    const nCols = Object.keys(cols).length, nRows = Math.max(...Object.values(cols).map((l) => l.length));
    return { pos, width: PAD * 2 + nCols * NODE_W + (nCols - 1) * COL_GAP, height: PAD * 2 + nRows * (NODE_H + ROW_GAP) };
  }

  function graphSvg(d) {
    const { pos, width, height } = layoutGraph(d);
    const sel = graphState.selected, focus = graphState.focus;
    const near = (e) => focus && (e.from === focus || e.to === focus);
    const edges = d.edges.map((e) => {
      const a = pos[e.from], b = pos[e.to];
      // Draw from the earlier (left) node to the later one.
      const [s, t] = a.x <= b.x ? [b, a] : [a, b];
      const x1 = t.x + NODE_W, y1 = t.y + NODE_H / 2, x2 = s.x, y2 = s.y + NODE_H / 2;
      const path = x1 < x2
        ? `M${x1},${y1} C${x1 + COL_GAP / 2},${y1} ${x2 - COL_GAP / 2},${y2} ${x2},${y2}`
        : `M${t.x + NODE_W},${y1} C${t.x + NODE_W + 40},${y1} ${s.x + NODE_W + 40},${y2} ${s.x + NODE_W},${y2}`;
      return `<path class="out-edge" d="${path}" stroke="${EDGE_COLOR[e.kind]}" ${near(e) ? 'style="opacity:1;stroke-width:2.5"' : ""}><title>${esc(d.nodes.find((n) => n.id === e.from).label)} ${e.kind} ${esc(d.nodes.find((n) => n.id === e.to).label)}</title></path>`;
    }).join("");
    const nodes = d.nodes.map((n) => {
      const p = pos[n.id];
      const text = n.label.length > 26 ? n.label.slice(0, 25) + "…" : n.label;
      return `<g class="out-node${sel.has(n.id) ? " selected" : ""}${focus === n.id ? " focused" : ""}" data-node="${esc(n.id)}" transform="translate(${p.x},${p.y})">
        <rect width="${NODE_W}" height="${NODE_H}" rx="6" fill="${KIND_COLOR[n.kind]}"></rect>
        <text x="10" y="15">${esc(text)}</text>
        <text x="10" y="29" style="fill:#d1d5db;font-size:10px">${esc(n.kind)}${n.core ? " · core" : ""}${sel.has(n.id) ? " · selected" : ""}</text>
        <title>${esc(n.label)}</title></g>`;
    }).join("");
    return `<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">${edges}${nodes}</svg>`;
  }

  function nodeDetails(d, id) {
    const n = d.nodes.find((x) => x.id === id);
    if (!n) return `<p class="out-muted">Click a node to see what it is and to add it to the parts you want built.</p>`;
    const label = (nid) => esc((d.nodes.find((x) => x.id === nid) || {}).label || nid);
    const out = d.edges.filter((e) => e.from === id).map((e) => `${esc(e.kind)} ${label(e.to)}`);
    const inc = d.edges.filter((e) => e.to === id).map((e) => `${label(e.from)} ${esc(e.kind)} this`);
    return `<h3>${esc(n.label)} ${pill(n.kind, "pending")}${n.core ? " " + pill("Core", "running") : ""}</h3>
      ${n.section ? `<p class="out-muted">${esc(n.section)}</p>` : ""}
      <p>${esc(n.description || "")}</p>
      ${n.source_text ? `<p class="out-muted">From the paper: “${esc(n.source_text)}”</p>` : ""}
      ${out.length || inc.length ? `<p class="out-muted">Links: ${[...out, ...inc].join("; ")}</p>` : ""}`;
  }

  renderers.graph = (d) => {
    if (!graphState.selected) graphState.selected = new Set(d.selection);
    const legend = Object.entries(KIND_COLOR).map(([k, c]) => `<span><span class="out-swatch" style="background:${c}"></span>${k}</span>`).join("")
      + Object.entries(EDGE_COLOR).map(([k, c]) => `<span><span class="out-swatch" style="background:${c};height:3px"></span>${k}</span>`).join("");
    return `
      <div class="out-card out-highlight">
        <h2>Map of the paper</h2>
        <p>Built from the paper map the first stage produced (${d.nodes.length} parts, ${d.edges.length} links).
          Click parts to select the ones you want built. Links only show what the paper states; no link claims a contradiction.</p>
      </div>
      <div class="out-legend">${legend}</div>
      <div class="out-graph-wrap" id="out-graph">${graphSvg(d)}</div>
      <div class="out-card" style="margin-top:14px">
        <div class="out-row" style="margin-top:0">
          <b id="out-sel-count"></b>
          <button type="button" class="out-btn" id="out-sel-core">Select core parts</button>
          <button type="button" class="out-btn" id="out-sel-clear">Clear</button>
          <button type="button" class="out-btn primary" id="out-sel-save">Save selection</button>
          <span class="out-job" id="out-sel-status" style="margin-top:0">${d.saved_at ? `Last saved ${esc(d.saved_at)}` : "Not saved yet"}</span>
        </div>
        <div id="out-node-details">${nodeDetails(d, graphState.focus)}</div>
      </div>`;
  };
  renderers.graph.after = (d) => {
    const redraw = () => {
      document.getElementById("out-graph").innerHTML = graphSvg(d);
      document.getElementById("out-node-details").innerHTML = nodeDetails(d, graphState.focus);
      document.getElementById("out-sel-count").textContent = `${graphState.selected.size} part(s) selected`;
    };
    document.getElementById("out-graph").onclick = (e) => {
      const g = e.target.closest("[data-node]");
      if (!g) return;
      const id = g.dataset.node;
      if (graphState.selected.has(id)) graphState.selected.delete(id); else graphState.selected.add(id);
      graphState.focus = id;
      document.getElementById("out-sel-status").textContent = "Unsaved changes";
      redraw();
    };
    document.getElementById("out-sel-core").onclick = () => {
      d.nodes.filter((n) => n.core).forEach((n) => graphState.selected.add(n.id));
      document.getElementById("out-sel-status").textContent = "Unsaved changes";
      redraw();
    };
    document.getElementById("out-sel-clear").onclick = () => {
      graphState.selected.clear();
      document.getElementById("out-sel-status").textContent = "Unsaved changes";
      redraw();
    };
    document.getElementById("out-sel-save").onclick = async () => {
      const statusEl = document.getElementById("out-sel-status");
      try {
        const res = await fetch(`/action/graph_selection${QS}`, { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ selected: [...graphState.selected] }) });
        const body = await res.json();
        if (!res.ok) throw new Error(body.error || `HTTP ${res.status}`);
        d.selection = body.selected; d.saved_at = body.saved_at;
        statusEl.className = "out-job is-done";
        statusEl.textContent = `Saved ${body.selected.length} part(s) to ${body.path}`;
      } catch (err) {
        statusEl.className = "out-job is-failed";
        statusEl.textContent = `Could not save: ${err.message}`;
      }
    };
    redraw();
  };

  // -------------------------------------------------------- Evidence Card
  const RATING_PILL = { Supported: "completed", "Partly supported": "degraded", "Not checkable": "pending",
    "Not supported": "halted" };

  function claimRow(c) {
    const evidence = [
      `<p>${esc(c.evidence)}</p>`,
      c.paper_side ? `<p class="out-muted">Paper: ${esc(c.paper_side)}</p>` : "",
      c.executed_side ? `<p class="out-muted">Rebuilt: ${esc(c.executed_side)}</p>` : "",
      c.seeds ? `<p class="out-muted">Seeds: ${esc([].concat(c.seeds).join(", "))}</p>` : "",
      c.trace.length ? `<details><summary class="out-muted">How the rating was reached</summary>
        <ul>${c.trace.map((t) => `<li><b>${esc(t.step)}</b>: ${esc(t.text)}</li>`).join("")}</ul></details>` : "",
      c.override ? `<p class="out-muted">Researcher override: ${esc(JSON.stringify(c.override))}</p>` : "",
    ].join("");
    return [
      `<b>${esc(c.name)}</b>${c.section ? `<br><span class="out-muted">${esc(c.section)}</span>` : ""}
        ${c.text && c.text !== c.name ? `<p class="note">“${esc(c.text)}”</p>` : ""}`,
      `${pill(c.rating, RATING_PILL[c.rating] || "pending")}<br><span class="out-muted">${esc(c.status_words)}</span>`,
      evidence,
      c.limits.length ? `<ul>${c.limits.map((l) => `<li>${esc(l)}</li>`).join("")}</ul>` : `<span class="out-muted">None recorded</span>`,
    ];
  }

  renderers.evidence = (d) => {
    const fromPaper = d.claims.filter((c) => c.from_paper);
    const added = d.claims.filter((c) => !c.from_paper);
    const headers = ["Claim", "Rating", "Evidence", "Limits"];
    const counts = Object.entries(d.counts).filter(([, n]) => n).map(([r, n]) => `${pill(r, RATING_PILL[r])} ${n}`).join(" &nbsp; ");
    const guessed = d.settings.filter((s) => s.guessed).length;
    return `
      <div class="out-card out-highlight">
        <h2>Evidence for each claim</h2>
        <p>${counts || "No claims were recorded."}</p>
        <p class="out-muted">Ratings come from the verification stage's claims ledger. “Supported” means the rebuilt code
          passed a check for the claim; it is not proof that the paper's full-scale numbers were reproduced.</p>
      </div>
      <div class="out-card">
        <h2>Claims from the paper</h2>
        ${fromPaper.length ? table(headers, fromPaper.map(claimRow)) : "<p>No claims were lifted from the paper text.</p>"}
      </div>
      ${added.length ? `<div class="out-card">
        <h2>Checks R2C added</h2>
        <p class="out-muted">Behavior checks the system wrote to test the rebuilt method. They are not quotes from the paper.</p>
        ${table(headers, added.map(claimRow))}
      </div>` : ""}
      <div class="out-card">
        <h2>What the paper says vs what the system guessed</h2>
        <p class="out-muted">${d.settings.length - guessed} setting(s) come from the paper and ${guessed} were chosen by the system.</p>
        ${d.settings.length ? table(["Setting", "Used", "Source", "Paper says", "Why"], d.settings.map((s) => [
          `<b>${esc(s.name)}</b>`,
          esc(JSON.stringify(s.value)),
          pill(s.source, s.guessed ? "degraded" : "completed"),
          esc(s.paper_says || (s.paper_value !== null && s.paper_value !== undefined ? JSON.stringify(s.paper_value) : "Not stated"))
            + (s.section ? `<br><span class="out-muted">${esc(s.section)}</span>` : ""),
          `<span class="note">${esc(s.why)}</span>`,
        ])) : "<p>No settings log was recorded for this run.</p>"}
      </div>
      ${d.assumptions.length ? `<div class="out-card">
        <h2>Decisions the system made</h2>
        ${d.assumptions.map((a) => `
          <div class="out-card${a.needs_you ? " out-warn" : ""}">
            <h3>${esc(a.id)}: ${esc(a.title)} ${a.needs_you ? pill("Needs you", "halted") : pill("Applied", "completed")}</h3>
            ${a.detected ? `<p><b>Found:</b> ${esc(a.detected)}</p>` : ""}
            ${a.action ? `<p><b>Done:</b> ${esc(a.action)}</p>` : ""}
            ${a.reasoning ? `<p class="out-muted">${esc(a.reasoning)}</p>` : ""}
            ${a.override ? `<p class="out-muted">To change it: ${esc(a.override)}</p>` : ""}
          </div>`).join("")}
      </div>` : ""}`;
  };

  buildTabs();
  window.R2COutput = { onState, renderers, helpers: { esc, table, pill, link, runJob, watchJob, jobStatus, downloadCsv, load: (n) => load(n, true), panel } };
})();
