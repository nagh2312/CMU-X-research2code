// Research to Learn by Doing — guided exercise UI + course connectors.
(function () {
  const state = {
    pack: null,
    unlocked: { method: false, exercise: false, try: false, explain: false, challenge: false },
    features: {}, // sampleId -> [brightness, edges]
    lastRun: null,
  };

  const $ = (id) => document.getElementById(id);
  const panels = {
    upload: $("panel-upload"),
    method: $("panel-method"),
    exercise: $("panel-exercise"),
    try: $("panel-try"),
    explain: $("panel-explain"),
    challenge: $("panel-challenge"),
  };

  function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
  function list(el, items) {
    el.innerHTML = (items || []).map((t) => `<li>${esc(t)}</li>`).join("")
      || "<li class='muted'>None listed</li>";
  }

  function showStep(name) {
    Object.entries(panels).forEach(([k, el]) => { el.hidden = k !== name; });
    document.querySelectorAll(".step").forEach((btn) => {
      const s = btn.dataset.step;
      btn.classList.toggle("active", s === name);
      btn.disabled = s !== "upload" && !state.unlocked[s];
    });
    if (name === "try") {
      renderSamples();
      drawMap();
    }
  }

  function dist(a, b) {
    const dx = a[0] - b[0], dy = a[1] - b[1];
    return Math.hypot(dx, dy);
  }

  function predict(features, classes) {
    let best = null, bestD = Infinity;
    const detail = classes.map((c) => {
      const d = dist(features, c.prototype);
      if (d < bestD) { bestD = d; best = c; }
      return { id: c.id, name: c.name, distance: d };
    }).sort((a, b) => a.distance - b.distance);
    return { predicted: best?.id, name: best?.name, distance: bestD, detail };
  }

  async function loadPack(filename, label) {
    const res = await fetch(`/demo/${filename}`);
    if (!res.ok) throw new Error("Could not load lesson");
    const pack = await res.json();
    state.pack = pack;
    state.unlocked = { method: true, exercise: true, try: true, explain: true, challenge: true };
    state.features = {};
    pack.exercise.samples.forEach((s) => { state.features[s.id] = s.features.slice(); });
    state.lastRun = null;
    $("upload-status").textContent = `Loaded: ${label || pack.paper.name}`;
    fillMethod(pack);
    fillExercise(pack);
    fillExplain(pack);
    fillChallenge(pack);
    showStep("method");
  }

  function fillMethod(pack) {
    $("lesson-title").textContent = pack.title;
    $("lesson-line").textContent = pack.paper.one_line;
    $("lesson-paper").textContent = `${pack.paper.name} · ${pack.paper.domain || ""}`;
    $("core-did").textContent = pack.core_method.what_they_did;
    $("core-inputs").textContent = pack.core_method.inputs;
    $("core-how").textContent = pack.core_method.how_results;
    list($("core-from"), pack.core_method.from_paper);
    list($("simplifications"), pack.teaching_simplifications);
  }

  function fillExercise(pack) {
    $("ex-goal").textContent = pack.exercise.goal;
    $("ex-steps").innerHTML = (pack.exercise.steps || [])
      .map((s) => `<li>${esc(s)}</li>`).join("");
    $("prototypes").innerHTML = pack.exercise.classes.map((c) => `
      <div class="proto">
        <div class="swatch" style="background:${esc(c.color)}"></div>
        <b>${esc(c.id)}: ${esc(c.name)}</b>
        <p class="muted">Prototype [${c.prototype[0]}, ${c.prototype[1]}]</p>
      </div>`).join("");
  }

  function fillExplain(pack) {
    $("explain-after").textContent = pack.explanations.after_run;
    $("explain-mistakes").textContent = pack.explanations.mistakes;
    $("explain-paper").textContent = pack.explanations.paper_link;
    list($("bound-paper"), pack.evidence_boundaries.from_paper);
    list($("bound-simple"), pack.evidence_boundaries.simplified_for_teaching);
  }

  function fillChallenge(pack) {
    const ch = pack.challenge;
    $("chal-title").textContent = ch.title;
    $("chal-prompt").textContent = ch.prompt;
    $("chal-success-text").textContent = ch.success;
    $("chal-success").hidden = true;
    $("chal-status").textContent = "";
    const s = pack.exercise.samples.find((x) => x.id === ch.sample_id);
    const feats = state.features[ch.sample_id] || (s ? s.features.slice() : [5, 5]);
    $("chal-controls").innerHTML = `
      <p class="muted">Sample <b>${esc(ch.sample_id)}</b> · true label <b>${esc(s?.label || "?")}</b></p>
      <div class="chal-sliders">
        <label>Brightness <span id="chal-b-val">${feats[0].toFixed(1)}</span>
          <input type="range" id="chal-b" min="0" max="10" step="0.1" value="${feats[0]}">
        </label>
        <label>Edge-ness <span id="chal-e-val">${feats[1].toFixed(1)}</span>
          <input type="range" id="chal-e" min="0" max="10" step="0.1" value="${feats[1]}">
        </label>
      </div>`;
    const sync = () => {
      const b = Number($("chal-b").value), e = Number($("chal-e").value);
      $("chal-b-val").textContent = b.toFixed(1);
      $("chal-e-val").textContent = e.toFixed(1);
      state.features[ch.sample_id] = [b, e];
    };
    $("chal-b").oninput = sync;
    $("chal-e").oninput = sync;
  }

  function renderSamples() {
    const pack = state.pack;
    if (!pack) return;
    const run = state.lastRun;
    $("samples").innerHTML = pack.exercise.samples.map((s) => {
      const feats = state.features[s.id] || s.features;
      const row = run?.rows?.find((r) => r.id === s.id);
      let badge = `<span class="badge wait">Not run</span>`;
      let cls = "sample";
      if (row) {
        cls += row.correct ? " hit" : " miss";
        badge = row.correct
          ? `<span class="badge ok">Correct → ${esc(row.predicted)}</span>`
          : `<span class="badge bad">Miss: predicted ${esc(row.predicted)}, true ${esc(row.true_label)}</span>`;
      }
      return `<div class="${cls}" data-sid="${esc(s.id)}">
        <b>${esc(s.id)}</b> <span class="muted">true: ${esc(s.label)}</span>
        <label>Brightness
          <input type="number" min="0" max="10" step="0.1" data-f="0" value="${feats[0]}">
        </label>
        <label>Edge-ness
          <input type="number" min="0" max="10" step="0.1" data-f="1" value="${feats[1]}">
        </label>
        ${badge}
        <p class="muted">${esc(s.hint || "")}</p>
      </div>`;
    }).join("");
    $("samples").querySelectorAll("input").forEach((inp) => {
      inp.addEventListener("change", () => {
        const card = inp.closest("[data-sid]");
        const id = card.dataset.sid;
        const i = Number(inp.dataset.f);
        const v = Math.min(10, Math.max(0, Number(inp.value) || 0));
        inp.value = v;
        state.features[id] = state.features[id] || [0, 0];
        state.features[id][i] = v;
        state.lastRun = null;
        $("score-line").textContent = "Features changed — run again.";
        drawMap();
      });
    });
  }

  function runClassification() {
    const pack = state.pack;
    if (!pack) return;
    const classes = pack.exercise.classes;
    const rows = pack.exercise.samples.map((s) => {
      const feats = state.features[s.id] || s.features;
      const pred = predict(feats, classes);
      return {
        id: s.id,
        true_label: s.label,
        features: feats.slice(),
        predicted: pred.predicted,
        correct: pred.predicted === s.label,
      };
    });
    const correct = rows.filter((r) => r.correct).length;
    state.lastRun = { rows, correct, total: rows.length, accuracy: correct / rows.length };
    $("score-line").textContent =
      `${correct} / ${rows.length} correct (${(100 * state.lastRun.accuracy).toFixed(0)}%)`;
    renderSamples();
    drawMap();
  }

  function drawMap() {
    const canvas = $("fmap");
    const pack = state.pack;
    if (!canvas || !pack) return;
    const ctx = canvas.getContext("2d");
    const W = canvas.width, H = canvas.height, pad = 28;
    ctx.fillStyle = "#0b1220";
    ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = "#374151";
    ctx.beginPath();
    ctx.moveTo(pad, H - pad); ctx.lineTo(W - pad, H - pad);
    ctx.moveTo(pad, pad); ctx.lineTo(pad, H - pad);
    ctx.stroke();
    ctx.fillStyle = "#9ca3af";
    ctx.font = "11px sans-serif";
    ctx.fillText("brightness →", W / 2 - 30, H - 8);
    ctx.save();
    ctx.translate(12, H / 2 + 30);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText("edge-ness →", 0, 0);
    ctx.restore();

    const toXY = (f) => [
      pad + (f[0] / 10) * (W - 2 * pad),
      H - pad - (f[1] / 10) * (H - 2 * pad),
    ];

    pack.exercise.classes.forEach((c) => {
      const [x, y] = toXY(c.prototype);
      ctx.fillStyle = c.color;
      ctx.beginPath();
      ctx.arc(x, y, 10, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#e5e7eb";
      ctx.fillText(c.id, x + 12, y + 4);
    });

    pack.exercise.samples.forEach((s) => {
      const feats = state.features[s.id] || s.features;
      const [x, y] = toXY(feats);
      const row = state.lastRun?.rows?.find((r) => r.id === s.id);
      ctx.fillStyle = row ? (row.correct ? "#22c55e" : "#ef4444") : "#93c5fd";
      ctx.beginPath();
      ctx.arc(x, y, 5, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  // --- Connectors (course platforms) ---
  const CONNECTORS = [
    { name: "Coursera", kind: "University & industry courses" },
    { name: "edX", kind: "University MOOCs" },
    { name: "Udacity", kind: "Nanodegrees & tech skills" },
    { name: "Khan Academy", kind: "Free foundations" },
    { name: "DeepLearning.AI", kind: "ML / DL specializations" },
    { name: "Udemy", kind: "Practical skill courses" },
    { name: "LinkedIn Learning", kind: "Professional skills" },
    { name: "MIT OpenCourseWare", kind: "Free MIT course materials" },
    { name: "YouTube Learning", kind: "Video lectures & playlists" },
    { name: "Fast.ai", kind: "Practical deep learning" },
    { name: "Kaggle Learn", kind: "Short ML micro-courses" },
    { name: "Google Skills / Cloud Skills Boost", kind: "Cloud & ML labs" },
  ];

  const connectorsPanel = $("connectors-panel");
  const connectorList = $("connector-list");
  if (connectorList) {
    connectorList.innerHTML = CONNECTORS.map((c) => `
      <li>
        <div>
          <div class="name">${esc(c.name)}</div>
          <span class="soon">Coming later</span>
        </div>
        <div class="kind">${esc(c.kind)}</div>
      </li>`).join("");
  }

  function openConnectors(open) {
    if (!connectorsPanel) return;
    connectorsPanel.hidden = !open;
    connectorsPanel.setAttribute("aria-hidden", open ? "false" : "true");
    $("connectors-btn")?.setAttribute("aria-expanded", open ? "true" : "false");
  }

  document.querySelectorAll(".step").forEach((btn) => {
    btn.addEventListener("click", () => { if (!btn.disabled) showStep(btn.dataset.step); });
  });
  document.querySelectorAll("[data-go]").forEach((btn) => {
    btn.addEventListener("click", () => showStep(btn.dataset.go));
  });

  $("use-demo").addEventListener("click", () =>
    loadPack("image_classification_lesson.json", "image-classification lesson")
      .catch((e) => { $("upload-status").textContent = e.message; }));

  $("run-cls")?.addEventListener("click", runClassification);
  $("reset-samples")?.addEventListener("click", () => {
    if (!state.pack) return;
    state.pack.exercise.samples.forEach((s) => { state.features[s.id] = s.features.slice(); });
    state.lastRun = null;
    $("score-line").textContent = "Reset. Run classification again.";
    renderSamples();
    drawMap();
  });

  $("chal-run")?.addEventListener("click", () => {
    const pack = state.pack;
    if (!pack) return;
    const id = pack.challenge.sample_id;
    const s = pack.exercise.samples.find((x) => x.id === id);
    const feats = state.features[id] || s.features;
    const pred = predict(feats, pack.exercise.classes);
    const flipped = pred.predicted !== s.label;
    $("chal-status").textContent =
      `Predicted ${pred.predicted} (${pred.name}) · distance ${pred.distance.toFixed(2)}`
      + (flipped ? " · boundary crossed!" : " · still same as true label — keep moving.");
    $("chal-success").hidden = !flipped;
  });

  $("connectors-btn")?.addEventListener("click", () => openConnectors(connectorsPanel.hidden));
  $("connectors-close")?.addEventListener("click", () => openConnectors(false));
  connectorsPanel?.addEventListener("click", (e) => {
    if (e.target === connectorsPanel) openConnectors(false);
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && connectorsPanel && !connectorsPanel.hidden) openConnectors(false);
  });

  const drop = $("drop");
  const file = $("file");
  function handleFile(f) {
    if (!f) return;
    $("upload-status").textContent = `Selected “${f.name}” — loading image-classification lesson.`;
    loadPack("image_classification_lesson.json").catch((e) => {
      $("upload-status").textContent = e.message;
    });
  }
  file?.addEventListener("change", () => handleFile(file.files[0]));
  drop?.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("drag"); });
  drop?.addEventListener("dragleave", () => drop.classList.remove("drag"));
  drop?.addEventListener("drop", (e) => {
    e.preventDefault();
    drop.classList.remove("drag");
    handleFile(e.dataTransfer.files[0]);
  });

  showStep("upload");
})();
