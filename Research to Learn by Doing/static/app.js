// Research to Learn by Doing — SimScale-style workbench + Coursera connector.
(function () {
  const state = {
    pack: null,
    unlocked: { method: false, exercise: false, try: false, explain: false, challenge: false },
    features: {},
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
  function setText(id, text) {
    const el = $(id);
    if (el) el.textContent = text;
  }
  function list(el, items) {
    if (!el) return;
    el.innerHTML = (items || []).map((t) => `<li>${esc(t)}</li>`).join("")
      || "<li class='muted'>None listed</li>";
  }

  function jobStatusForStep(name) {
    if (name === "upload") {
      return state.pack ? "Paper loaded — open Method" : "Idle — load a paper to begin";
    }
    if (name === "method") return "Method ready — see the exercise";
    if (name === "exercise") return "Exercise defined — try it yourself";
    if (name === "try") {
      if (state.lastRun) {
        return `Run done — ${state.lastRun.correct}/${state.lastRun.total} correct`;
      }
      return "Ready to classify samples";
    }
    if (name === "explain") return "Results explained — take the challenge";
    if (name === "challenge") return "Challenge open — flip a boundary";
    return "Idle — load a paper to begin";
  }

  function showStep(name) {
    Object.entries(panels).forEach(([k, el]) => {
      if (el) el.hidden = k !== name;
    });
    document.querySelectorAll(".step").forEach((btn) => {
      const s = btn.dataset.step;
      btn.classList.toggle("active", s === name);
      btn.disabled = s !== "upload" && !state.unlocked[s];
    });
    setText("job-status", jobStatusForStep(name));
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
    setText("upload-status", `Loaded: ${label || pack.paper.name}`);
    setText("proj-name", pack.title || pack.paper?.name || "Learning project");
    setText("tree-paper", pack.paper?.name || "Paper loaded");
    fillMethod(pack);
    fillExercise(pack);
    fillExplain(pack);
    fillChallenge(pack);
    showStep("method");
  }

  function fillMethod(pack) {
    setText("lesson-title", pack.title);
    setText("lesson-line", pack.paper.one_line);
    setText("lesson-paper", `${pack.paper.name} · ${pack.paper.domain || ""}`);
    setText("core-did", pack.core_method.what_they_did);
    setText("core-inputs", pack.core_method.inputs);
    setText("core-how", pack.core_method.how_results);
    list($("core-from"), pack.core_method.from_paper);
    list($("simplifications"), pack.teaching_simplifications);
  }

  function fillExercise(pack) {
    setText("ex-goal", pack.exercise.goal);
    const steps = $("ex-steps");
    if (steps) {
      steps.innerHTML = (pack.exercise.steps || []).map((s) => `<li>${esc(s)}</li>`).join("");
    }
    const proto = $("prototypes");
    if (proto) {
      proto.innerHTML = pack.exercise.classes.map((c) => `
      <div class="proto">
        <div class="swatch" style="background:${esc(c.color)}"></div>
        <b>${esc(c.id)}: ${esc(c.name)}</b>
        <p class="muted">Prototype [${c.prototype[0]}, ${c.prototype[1]}]</p>
      </div>`).join("");
    }
  }

  function fillExplain(pack) {
    setText("explain-after", pack.explanations.after_run);
    setText("explain-mistakes", pack.explanations.mistakes);
    setText("explain-paper", pack.explanations.paper_link);
    list($("bound-paper"), pack.evidence_boundaries.from_paper);
    list($("bound-simple"), pack.evidence_boundaries.simplified_for_teaching);
  }

  function fillChallenge(pack) {
    const ch = pack.challenge;
    setText("chal-title", ch.title);
    setText("chal-prompt", ch.prompt);
    setText("chal-success-text", ch.success);
    const success = $("chal-success");
    if (success) success.hidden = true;
    setText("chal-status", "");
    const s = pack.exercise.samples.find((x) => x.id === ch.sample_id);
    const feats = state.features[ch.sample_id] || (s ? s.features.slice() : [5, 5]);
    const controls = $("chal-controls");
    if (!controls) return;
    controls.innerHTML = `
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
      setText("chal-b-val", b.toFixed(1));
      setText("chal-e-val", e.toFixed(1));
      state.features[ch.sample_id] = [b, e];
    };
    $("chal-b").oninput = sync;
    $("chal-e").oninput = sync;
  }

  function renderSamples() {
    const pack = state.pack;
    if (!pack) return;
    const run = state.lastRun;
    const samples = $("samples");
    if (!samples) return;
    samples.innerHTML = pack.exercise.samples.map((s) => {
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
    samples.querySelectorAll("input").forEach((inp) => {
      inp.addEventListener("change", () => {
        const card = inp.closest("[data-sid]");
        const id = card.dataset.sid;
        const i = Number(inp.dataset.f);
        const v = Math.min(10, Math.max(0, Number(inp.value) || 0));
        inp.value = v;
        state.features[id] = state.features[id] || [0, 0];
        state.features[id][i] = v;
        state.lastRun = null;
        setText("score-line", "Features changed — run again.");
        setText("job-status", "Ready to classify samples");
        drawMap();
      });
    });
  }

  function runClassification() {
    const pack = state.pack;
    if (!pack) {
      setText("job-status", "Load a paper first — then Run");
      showStep("upload");
      return;
    }
    showStep("try");
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
    setText("score-line",
      `${correct} / ${rows.length} correct (${(100 * state.lastRun.accuracy).toFixed(0)}%)`);
    setText("job-status", `Run done — ${correct}/${rows.length} correct`);
    renderSamples();
    drawMap();
  }

  function drawMap() {
    const canvas = $("fmap");
    const pack = state.pack;
    if (!canvas || !pack) return;
    const ctx = canvas.getContext("2d");
    const W = canvas.width, H = canvas.height, pad = 28;
    ctx.fillStyle = "#1f2428";
    ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = "#667085";
    ctx.beginPath();
    ctx.moveTo(pad, H - pad); ctx.lineTo(W - pad, H - pad);
    ctx.moveTo(pad, pad); ctx.lineTo(pad, H - pad);
    ctx.stroke();
    ctx.fillStyle = "#98a2b3";
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
      ctx.fillStyle = row ? (row.correct ? "#12b76a" : "#f04438") : "#2e90fa";
      ctx.beginPath();
      ctx.arc(x, y, 5, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  // --- Hierarchical connectors (Coursera opens demo page) ---
  const CONNECTORS = [
    {
      group: "Learning platforms",
      items: [
        { name: "Coursera", kind: "University & industry courses", id: "coursera", live: true },
        { name: "edX", kind: "University MOOCs", soon: true },
        { name: "Udacity", kind: "Nanodegrees & tech skills", soon: true },
        { name: "Khan Academy", kind: "Free foundations", soon: true },
        { name: "DeepLearning.AI", kind: "ML / DL specializations", soon: true },
        { name: "Udemy", kind: "Practical skill courses", soon: true },
        { name: "LinkedIn Learning", kind: "Professional skills", soon: true },
        { name: "MIT OpenCourseWare", kind: "Free MIT course materials", soon: true },
        { name: "YouTube Learning", kind: "Video lectures & playlists", soon: true },
        { name: "Fast.ai", kind: "Practical deep learning", soon: true },
        { name: "Kaggle Learn", kind: "Short ML micro-courses", soon: true },
        { name: "Google Skills / Cloud Skills Boost", kind: "Cloud & ML labs", soon: true },
      ],
    },
  ];

  const connectorsPanel = $("connectors-panel");
  const connectorList = $("connector-list");
  if (connectorList) {
    connectorList.innerHTML = CONNECTORS.map((g) => `
      <li>
        <div class="connector-group">${esc(g.group)}</div>
        <ul>
          ${g.items.map((c) => `
            <li>
              <button type="button" class="open-platform" data-platform="${esc(c.id || "")}" ${c.soon ? "disabled" : ""}>
                <div class="name">${esc(c.name)}</div>
                ${c.live ? '<span class="live">Open demo</span>' : '<span class="soon">Coming later</span>'}
              </button>
              <div class="kind">${esc(c.kind)}</div>
            </li>`).join("")}
        </ul>
      </li>`).join("");
    connectorList.querySelectorAll(".open-platform").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.dataset.platform;
        if (id === "coursera") {
          openConnectors(false);
          window.location.href = "/coursera";
        }
      });
    });
  }

  function openConnectors(open) {
    if (!connectorsPanel) return;
    connectorsPanel.hidden = !open;
    connectorsPanel.setAttribute("aria-hidden", open ? "false" : "true");
    $("connectors-btn")?.setAttribute("aria-expanded", open ? "true" : "false");
  }

  function goCoursera() {
    window.location.href = "/coursera";
  }

  document.querySelectorAll(".step").forEach((btn) => {
    btn.addEventListener("click", () => { if (!btn.disabled) showStep(btn.dataset.step); });
  });
  document.querySelectorAll("[data-go]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const step = btn.dataset.go;
      if (step !== "upload" && !state.unlocked[step]) return;
      showStep(step);
    });
  });

  $("use-demo")?.addEventListener("click", () =>
    loadPack("image_classification_lesson.json", "image-classification lesson")
      .catch((e) => { setText("upload-status", e.message); }));

  $("run-cls")?.addEventListener("click", runClassification);
  $("run-cls-panel")?.addEventListener("click", runClassification);
  $("reset-samples")?.addEventListener("click", () => {
    if (!state.pack) return;
    state.pack.exercise.samples.forEach((s) => { state.features[s.id] = s.features.slice(); });
    state.lastRun = null;
    setText("score-line", "Reset. Run classification again.");
    setText("job-status", "Ready to classify samples");
    showStep("try");
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
    setText("chal-status",
      `Predicted ${pred.predicted} (${pred.name}) · distance ${pred.distance.toFixed(2)}`
      + (flipped ? " · boundary crossed!" : " · still same as true label — keep moving."));
    const success = $("chal-success");
    if (success) success.hidden = !flipped;
  });

  $("connectors-btn")?.addEventListener("click", () => openConnectors(connectorsPanel.hidden));
  $("connectors-close")?.addEventListener("click", () => openConnectors(false));
  connectorsPanel?.addEventListener("click", (e) => {
    if (e.target === connectorsPanel) openConnectors(false);
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && connectorsPanel && !connectorsPanel.hidden) openConnectors(false);
  });
  $("tree-coursera")?.addEventListener("click", goCoursera);
  $("open-coursera-tool")?.addEventListener("click", goCoursera);

  const drop = $("drop");
  const file = $("file");
  function handleFile(f) {
    if (!f) return;
    setText("upload-status", `Selected “${f.name}” — loading image-classification lesson.`);
    loadPack("image_classification_lesson.json").catch((e) => {
      setText("upload-status", e.message);
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
