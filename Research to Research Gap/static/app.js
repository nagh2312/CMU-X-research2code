// Research to Research Gap — interactive demo UI.
(function () {
  const state = {
    pack: null,
    unlocked: { understand: false, gaps: false, next: false, adjacency: false },
  };

  const $ = (id) => document.getElementById(id);
  const panels = {
    upload: $("panel-upload"),
    understand: $("panel-understand"),
    gaps: $("panel-gaps"),
    next: $("panel-next"),
    adjacency: $("panel-adjacency"),
  };

  function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
  function list(el, items) {
    el.innerHTML = (items || []).map((t) => `<li>${esc(t)}</li>`).join("") || "<li class='muted'>None listed</li>";
  }

  function showStep(name) {
    Object.entries(panels).forEach(([k, el]) => { el.hidden = k !== name; });
    document.querySelectorAll(".step").forEach((btn) => {
      const s = btn.dataset.step;
      btn.classList.toggle("active", s === name);
      btn.disabled = s !== "upload" && !state.unlocked[s];
    });
  }

  async function loadPack(filename, label) {
    const res = await fetch(`/demo/${filename}`);
    if (!res.ok) throw new Error("Could not load demo");
    const pack = await res.json();
    state.pack = pack;
    state.unlocked = { understand: true, gaps: true, next: true, adjacency: true };
    $("upload-status").textContent = `Loaded: ${label || pack.paper.name}`;
    fillUnderstand(pack);
    fillGaps(pack);
    fillNext(pack);
    fillAdjacency(pack);
    showStep("understand");
  }

  function fillUnderstand(pack) {
    $("paper-title").textContent = pack.title;
    $("paper-line").textContent = pack.paper.one_line;
    $("paper-meta").textContent = `${pack.paper.name} · ${pack.paper.domain || ""}`;
    $("rq").textContent = pack.established.research_question;
    $("method").textContent = pack.established.methodology;
    list($("findings"), pack.established.findings);
    list($("limitations"), pack.established.limitations);
    list($("conclusions"), pack.established.conclusions);
  }

  function renderGap(g) {
    const quotes = (g.support_passages || []).map((q) => `<div class="quote">“${esc(q)}”</div>`).join("");
    const pill = g.kind === "author_acknowledged"
      ? '<span class="pill author">Author-acknowledged</span>'
      : '<span class="pill inferred">Inferred from paper</span>';
    return `<div class="gap-item">
      <h4>${esc(g.title)} ${pill}</h4>
      <p>${esc(g.why_it_matters)}</p>
      ${quotes}
      <p class="muted"><b>Could help establish:</b> ${esc(g.what_it_could_establish)}</p>
    </div>`;
  }

  function fillGaps(pack) {
    const ga = pack.gap_assessment;
    const verdict = $("gap-verdict");
    if (ga.has_clear_gap) {
      verdict.className = "card highlight";
      verdict.innerHTML = `<h2>Clear gap supported by this paper</h2><p>${esc(ga.summary)}</p>`;
    } else {
      verdict.className = "card ok";
      verdict.innerHTML = `<h2>No clear research gap to invent</h2>
        <p>${esc(ga.summary)}</p>
        ${ga.invented_gap_warning ? `<p><b>Do not invent:</b> ${esc(ga.invented_gap_warning)}</p>` : ""}`;
    }

    const author = (ga.gaps || []).filter((g) => g.kind === "author_acknowledged");
    const inferred = (ga.gaps || []).filter((g) => g.kind !== "author_acknowledged");
    $("gaps-author").innerHTML = author.length
      ? author.map(renderGap).join("")
      : "<p class='muted'>None marked as explicitly acknowledged.</p>";
    $("gaps-inferred").innerHTML = inferred.length
      ? inferred.map(renderGap).join("")
      : "<p class='muted'>None inferred — and we will not force one.</p>";

    $("future-work").innerHTML = (pack.author_future_work || []).map((fw) => `
      <div class="fw-item">
        <p><b>${esc(fw.text)}</b></p>
        <p class="muted">In practice: ${esc(fw.practical_meaning)}</p>
      </div>`).join("") || "<p class='muted'>No future-work statements in this pack.</p>";

    list($("bound-paper"), pack.evidence_boundaries.from_uploaded_paper);
    list($("bound-lit"), pack.evidence_boundaries.would_need_related_literature);
  }

  function fillNext(pack) {
    const steps = [...(pack.next_steps || [])].sort((a, b) => a.priority - b.priority);
    $("next-steps").innerHTML = steps.map((s) => {
      const src = s.source === "author_acknowledged" ? '<span class="pill author">From acknowledged gap</span>'
        : s.source === "author_future_work" ? '<span class="pill author">Author future work</span>'
        : s.source === "inferred_from_paper" ? '<span class="pill inferred">Inferred</span>'
        : '<span class="pill ext">Extension (not a forced gap)</span>';
      const involves = (s.involves || []).map((x) => `<li>${esc(x)}</li>`).join("");
      const exps = (s.suggested_experiments || []).map((x) => `<li>${esc(x)}</li>`).join("");
      return `<div class="card step-item">
        <p class="priority">Priority ${esc(s.priority)}</p>
        <h3>${esc(s.title)} ${src}</h3>
        <p><b>What it involves</b></p><ul>${involves}</ul>
        <p><b>Could help establish:</b> ${esc(s.would_help_establish)}</p>
        ${exps ? `<p><b>Suggested experiments</b></p><ul>${exps}</ul>` : ""}
        ${s.needs_literature ? `<p class="muted"><b>Literature needed:</b> ${esc(s.literature_note || "Related work beyond this paper.")}</p>` : ""}
      </div>`;
    }).join("");

    const alt = pack.no_gap_alternative;
    const box = $("no-gap-box");
    if (!pack.gap_assessment.has_clear_gap && alt) {
      box.hidden = false;
      $("no-gap-when").textContent = alt.when_to_use || "";
      list($("no-gap-suggestions"), alt.suggestions);
    } else {
      box.hidden = true;
    }
  }

  function fillAdjacency(pack) {
    const adj = pack.adjacency || {};
    $("adj-anchor").textContent = adj.topic_anchor
      ? `Topic anchor: ${adj.topic_anchor}` : "";
    $("adj-rule").textContent = adj.stay_close_rule || "";
    $("adj-list").innerHTML = (adj.opportunities || []).map((o) => {
      const dist = o.distance === "very_close" ? "Very close"
        : o.distance === "close" ? "Close"
        : o.distance === "far" ? "Far / out of scope" : esc(o.distance || "");
      const pillCls = o.distance === "far" ? "ext" : "author";
      const explore = (o.explore || []).map((x) => `<li>${esc(x)}</li>`).join("");
      return `<div class="card">
        <h3>${esc(o.title)} <span class="pill ${pillCls}">${esc(dist)}</span></h3>
        <p>${esc(o.why_adjacent)}</p>
        ${explore ? `<p class="muted"><b>Explore</b></p><ul>${explore}</ul>` : ""}
      </div>`;
    }).join("") || "<p class='muted'>No adjacency opportunities in this pack.</p>";

    const m = adj.market || {};
    $("market-context").textContent = m.context || "";
    const defs = m.definitions || {};
    $("market-defs").innerHTML = ["TAM", "SAM", "SOM"].map((k) => `
      <div class="card def-card">
        <h3>${k}</h3>
        <p>${esc(defs[k] || "")}</p>
      </div>`).join("");
    list($("market-how"), m.how_calculated);
    state.marketDefaults = m.demo_defaults || null;
    $("m-result").hidden = true;
  }

  // Client-side mirror of analyze.check_market_credibility (keeps UI offline).
  function checkMarketCredibility(data) {
    const issues = [];
    const notes = [];
    const num = (k) => {
      const raw = data[k];
      if (raw === null || raw === undefined || raw === "") return null;
      const n = Number(raw);
      if (Number.isNaN(n)) {
        issues.push({ level: "error", msg: `${k.toUpperCase()} is not a number.` });
        return null;
      }
      return n;
    };
    const tam = num("tam"), sam = num("sam"), som = num("som");
    const currency = (data.currency || "").trim();
    const method = (data.method || "").trim();
    let y = data.year;
    if (y !== null && y !== undefined && y !== "") {
      y = parseInt(y, 10);
      if (Number.isNaN(y)) issues.push({ level: "error", msg: "Year must be an integer." });
      else if (y < 1990 || y > 2100) issues.push({ level: "warn", msg: `Year ${y} looks unusual.` });
    }
    if (tam == null || sam == null || som == null) {
      issues.push({ level: "error", msg: "Enter TAM, SAM, and SOM (all three)." });
    }
    if (!currency) issues.push({ level: "warn", msg: "Currency is empty — figures may be incomparable." });
    if (tam != null && tam < 0) issues.push({ level: "error", msg: "TAM cannot be negative." });
    if (sam != null && sam < 0) issues.push({ level: "error", msg: "SAM cannot be negative." });
    if (som != null && som < 0) issues.push({ level: "error", msg: "SOM cannot be negative." });
    if (tam != null && sam != null && som != null && tam >= 0 && sam >= 0 && som >= 0) {
      if (!(som <= sam && sam <= tam)) {
        issues.push({ level: "error", msg: "Ordering broken: require SOM ≤ SAM ≤ TAM (same units and year)." });
      } else notes.push("Ordering OK: SOM ≤ SAM ≤ TAM.");
      if (tam > 0) {
        const samPct = 100 * sam / tam;
        const somPctSam = sam > 0 ? 100 * som / sam : 0;
        const somPctTam = 100 * som / tam;
        notes.push(`SAM is ${samPct.toFixed(1)}% of TAM; SOM is ${somPctSam.toFixed(1)}% of SAM (${somPctTam.toFixed(2)}% of TAM).`);
        if (samPct > 95) issues.push({ level: "warn", msg: "SAM is almost equal to TAM — filters may be missing." });
        if (samPct < 0.1 && sam > 0) issues.push({ level: "warn", msg: "SAM is a tiny fraction of TAM — confirm the filters." });
        if (somPctSam > 50) issues.push({ level: "warn", msg: "SOM > 50% of SAM is aggressive — explain capacity/share assumptions." });
      }
    }
    [["TAM", "tam_source"], ["SAM", "sam_source"], ["SOM", "som_source"]].forEach(([label, key]) => {
      const src = (data[key] || "").trim();
      if (!src) issues.push({ level: "warn", msg: `${label} has no source note — credibility is weak without a citation.` });
      else if (src.length < 8) issues.push({ level: "warn", msg: `${label} source is very short — add report name, year, or URL.` });
    });
    if (method === "top_down") notes.push("Top-down: industry TAM → filters → SAM → share/capacity → SOM.");
    if (method === "bottom_up") notes.push("Bottom-up: units × attach rate × price; sanity-check against TAM.");
    if (method === "mixed") notes.push("Mixed: reconcile top-down and bottom-up; large gaps reduce credibility.");
    const errors = issues.filter((i) => i.level === "error").length;
    const warnings = issues.filter((i) => i.level === "warn").length;
    let verdict, detail;
    if (errors) {
      verdict = "Not credible yet";
      detail = "Fix the errors before treating these figures as a working estimate.";
    } else if (warnings) {
      verdict = "Partly credible";
      detail = "Numbers may be usable, but address the warnings (sources, aggressive shares, missing filters).";
    } else {
      verdict = "Internally credible";
      detail = "Passed consistency checks. Still verify sources outside this tool.";
    }
    return { verdict, detail, errors, warnings, issues, notes };
  }

  function readMarketForm() {
    return {
      currency: $("m-currency").value,
      year: $("m-year").value,
      method: $("m-method").value,
      tam: $("m-tam").value,
      sam: $("m-sam").value,
      som: $("m-som").value,
      tam_source: $("m-tam-src").value,
      sam_source: $("m-sam-src").value,
      som_source: $("m-som-src").value,
    };
  }

  function fillMarketDefaults() {
    const d = state.marketDefaults;
    if (!d) return;
    $("m-currency").value = d.currency || "USD";
    $("m-year").value = d.year || 2024;
    $("m-method").value = d.method || "top_down";
    $("m-tam").value = d.tam ?? "";
    $("m-sam").value = d.sam ?? "";
    $("m-som").value = d.som ?? "";
    $("m-tam-src").value = d.tam_source || "";
    $("m-sam-src").value = d.sam_source || "";
    $("m-som-src").value = d.som_source || "";
  }

  function showCredibility(result) {
    const el = $("m-result");
    el.hidden = false;
    const cls = result.errors ? "cred-bad" : result.warnings ? "cred-warn" : "cred-ok";
    el.className = `cred-result ${cls}`;
    const issues = (result.issues || []).map((i) =>
      `<li><b>${i.level === "error" ? "Error" : "Warning"}:</b> ${esc(i.msg)}</li>`).join("");
    const notes = (result.notes || []).map((n) => `<li>${esc(n)}</li>`).join("");
    el.innerHTML = `<h3>${esc(result.verdict)}</h3><p>${esc(result.detail)}</p>
      ${issues ? `<ul>${issues}</ul>` : ""}
      ${notes ? `<p class="muted"><b>Notes</b></p><ul>${notes}</ul>` : ""}`;
  }

  document.querySelectorAll(".step").forEach((btn) => {
    btn.addEventListener("click", () => { if (!btn.disabled) showStep(btn.dataset.step); });
  });
  document.querySelectorAll("[data-go]").forEach((btn) => {
    btn.addEventListener("click", () => showStep(btn.dataset.go));
  });
  $("m-check").addEventListener("click", () => showCredibility(checkMarketCredibility(readMarketForm())));
  $("m-fill-demo").addEventListener("click", () => {
    fillMarketDefaults();
    showCredibility(checkMarketCredibility(readMarketForm()));
  });

  $("use-demo").addEventListener("click", () =>
    loadPack("autonomous_driving_detection.json", "autonomous-driving demo")
      .catch((e) => { $("upload-status").textContent = e.message; }));
  $("use-closed").addEventListener("click", () =>
    loadPack("paper_already_closed.json", "no-clear-gap demo")
      .catch((e) => { $("upload-status").textContent = e.message; }));

  const drop = $("drop");
  const file = $("file");
  function handleFile(f) {
    if (!f) return;
    $("upload-status").textContent = `Selected “${f.name}” — loading autonomous-driving demo pack.`;
    loadPack("autonomous_driving_detection.json").catch((e) => {
      $("upload-status").textContent = e.message;
    });
  }
  file.addEventListener("change", () => handleFile(file.files[0]));
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("drag"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("drag"));
  drop.addEventListener("drop", (e) => {
    e.preventDefault();
    drop.classList.remove("drag");
    handleFile(e.dataTransfer.files[0]);
  });

  showStep("upload");
})();
