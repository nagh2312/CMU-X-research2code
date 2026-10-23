// Research to Research Gap — interactive demo UI.
(function () {
  const state = {
    pack: null,
    unlocked: { understand: false, gaps: false, next: false },
  };

  const $ = (id) => document.getElementById(id);
  const panels = {
    upload: $("panel-upload"),
    understand: $("panel-understand"),
    gaps: $("panel-gaps"),
    next: $("panel-next"),
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
    state.unlocked = { understand: true, gaps: true, next: true };
    $("upload-status").textContent = `Loaded: ${label || pack.paper.name}`;
    fillUnderstand(pack);
    fillGaps(pack);
    fillNext(pack);
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

  document.querySelectorAll(".step").forEach((btn) => {
    btn.addEventListener("click", () => { if (!btn.disabled) showStep(btn.dataset.step); });
  });
  document.querySelectorAll("[data-go]").forEach((btn) => {
    btn.addEventListener("click", () => showStep(btn.dataset.go));
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
