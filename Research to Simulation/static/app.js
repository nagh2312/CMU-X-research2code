// Research to Simulation — interactive path-planning demo.
(function () {
  const state = {
    demo: null,
    unlocked: { understand: false, simulate: false, results: false },
    scene: null,
    lastRun: null,
    history: [],
  };

  const $ = (id) => document.getElementById(id);
  const panels = {
    upload: $("panel-upload"),
    understand: $("panel-understand"),
    simulate: $("panel-simulate"),
    results: $("panel-results"),
  };

  function showStep(name) {
    Object.entries(panels).forEach(([k, el]) => { el.hidden = k !== name; });
    document.querySelectorAll(".step").forEach((btn) => {
      const s = btn.dataset.step;
      btn.classList.toggle("active", s === name);
      const locked = s !== "upload" && !state.unlocked[s];
      btn.disabled = locked;
    });
  }

  function list(el, items) {
    el.innerHTML = (items || []).map((t) => `<li>${esc(t)}</li>`).join("") || "<li class='muted'>None listed</li>";
  }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  async function loadDemo() {
    const res = await fetch("/demo/path_planning.json");
    if (!res.ok) throw new Error("Could not load demo");
    const demo = await res.json();
    state.demo = demo;
    state.scene = {
      start: demo.default_scene.start.slice(),
      goal: demo.default_scene.goal.slice(),
      obstacles: new Set(demo.default_scene.obstacles.map(([x, y]) => key(x, y))),
    };
    state.unlocked.understand = true;
    state.unlocked.simulate = true;
    fillUnderstand(demo);
    $("upload-status").textContent = `Loaded: ${demo.paper.name}`;
    $("heuristic").value = demo.controls.heuristic || "manhattan";
    $("diagonal").checked = !!demo.controls.allow_diagonal;
    showStep("understand");
    draw();
  }

  function fillUnderstand(demo) {
    $("method-title").textContent = demo.title;
    $("method-line").textContent = demo.paper.one_line;
    $("method-paper").textContent = `From: ${demo.paper.name}`;
    list($("list-yes"), demo.simulatable.yes);
    list($("list-partial"), demo.simulatable.partial);
    list($("list-missing"), demo.simulatable.missing);
    list($("list-supported"), demo.supported_by_paper);
    list($("list-assumptions"), demo.assumptions);
  }

  function key(x, y) { return `${x},${y}`; }
  function parseKey(k) { return k.split(",").map(Number); }

  function neighbors(x, y, w, h, diagonal) {
    const dirs = [[1, 0], [-1, 0], [0, 1], [0, -1]];
    if (diagonal) dirs.push([1, 1], [1, -1], [-1, 1], [-1, -1]);
    return dirs
      .map(([dx, dy]) => [x + dx, y + dy])
      .filter(([nx, ny]) => nx >= 0 && ny >= 0 && nx < w && ny < h);
  }

  function hCost(a, b, mode) {
    const dx = Math.abs(a[0] - b[0]), dy = Math.abs(a[1] - b[1]);
    if (mode === "none") return 0;
    if (mode === "euclidean") return Math.hypot(dx, dy);
    return dx + dy;
  }

  function plan(scene, opts) {
    const w = opts.w, h = opts.h;
    const start = scene.start, goal = scene.goal;
    if (start[0] === goal[0] && start[1] === goal[1]) {
      return { status: "trivial", path: [start], expanded: [], cost: 0 };
    }
    const blocked = scene.obstacles;
    if (blocked.has(key(...start)) || blocked.has(key(...goal))) {
      return { status: "blocked", path: [], expanded: [], cost: null, note: "Start or goal sits on an obstacle." };
    }

    const open = new Map();
    const gScore = new Map();
    const came = new Map();
    const sk = key(...start);
    gScore.set(sk, 0);
    open.set(sk, hCost(start, goal, opts.heuristic));
    const expanded = [];

    while (open.size) {
      let curKey = null, best = Infinity;
      for (const [k, f] of open) if (f < best) { best = f; curKey = k; }
      open.delete(curKey);
      const [cx, cy] = parseKey(curKey);
      expanded.push([cx, cy]);
      if (cx === goal[0] && cy === goal[1]) {
        const path = [];
        let k = curKey;
        while (k) { path.push(parseKey(k)); k = came.get(k); }
        path.reverse();
        return { status: "found", path, expanded, cost: gScore.get(curKey) };
      }
      for (const [nx, ny] of neighbors(cx, cy, w, h, opts.diagonal)) {
        const nk = key(nx, ny);
        if (blocked.has(nk)) continue;
        const step = (opts.diagonal && nx !== cx && ny !== cy) ? Math.SQRT2 : opts.stepCost;
        const tentative = gScore.get(curKey) + step;
        if (tentative < (gScore.get(nk) ?? Infinity)) {
          came.set(nk, curKey);
          gScore.set(nk, tentative);
          open.set(nk, tentative + hCost([nx, ny], goal, opts.heuristic));
        }
      }
    }
    return { status: "blocked", path: [], expanded, cost: null };
  }

  function runScenario() {
    if (!state.demo || !state.scene) return;
    const opts = {
      w: state.demo.controls.grid_w,
      h: state.demo.controls.grid_h,
      heuristic: $("heuristic").value,
      diagonal: $("diagonal").checked,
      stepCost: state.demo.controls.step_cost || 1,
    };
    const result = plan(state.scene, opts);
    result.heuristic = opts.heuristic;
    result.diagonal = opts.diagonal;
    state.lastRun = result;
    state.history.unshift({
      n: state.history.length + 1,
      status: result.status,
      length: result.path.length ? result.path.length - 1 : 0,
      expanded: result.expanded.length,
      heuristic: result.heuristic,
    });
    state.unlocked.results = true;
    fillRunStats(result);
    fillResults(result);
    draw();
    $("sim-hint").textContent = result.status === "found"
      ? "Path drawn in blue. Open Results for the paper-linked explanation."
      : "No path under current rules. Try clearing obstacles or moving start/goal.";
  }

  function fillRunStats(result) {
    const length = result.path.length ? result.path.length - 1 : 0;
    $("run-stats").innerHTML = `
      <dt>Status</dt><dd>${esc(result.status)}${result.note ? " — " + esc(result.note) : ""}</dd>
      <dt>Path length</dt><dd>${result.status === "found" || result.status === "trivial" ? length : "—"}</dd>
      <dt>Cost</dt><dd>${result.cost == null ? "—" : Number(result.cost).toFixed(2)}</dd>
      <dt>Expanded</dt><dd>${result.expanded.length} cells</dd>
      <dt>Heuristic</dt><dd>${esc(result.heuristic || "—")}</dd>`;
  }

  function fillResults(result) {
    const demo = state.demo;
    const length = result.path.length ? result.path.length - 1 : 0;
    let story;
    if (result.status === "found") {
      story = demo.explain_templates.found
        .replace("{length}", String(length))
        .replace("{cost}", Number(result.cost).toFixed(2));
    } else if (result.status === "trivial") {
      story = demo.explain_templates.trivial;
    } else {
      story = demo.explain_templates.blocked;
      if (result.note) story += " " + result.note;
    }
    if ($("diagonal").checked) {
      story += " Diagonal moves were enabled for this run — that choice is marked as an assumption, not a paper claim.";
    }
    $("result-story").textContent = story;
    list($("result-supported"), demo.supported_by_paper);
    list($("result-assumptions"), demo.assumptions);
    $("history").innerHTML = state.history.map((h) =>
      `<tr><td>${h.n}</td><td>${esc(h.status)}</td><td>${h.length}</td><td>${h.expanded}</td><td>${esc(h.heuristic)}</td></tr>`
    ).join("");
  }

  function draw() {
    const canvas = $("world");
    if (!canvas || !state.demo) return;
    const ctx = canvas.getContext("2d");
    const w = state.demo.controls.grid_w;
    const h = state.demo.controls.grid_h;
    const cw = canvas.width / w;
    const ch = canvas.height / h;
    ctx.fillStyle = "#0b1220";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const expanded = new Set((state.lastRun?.expanded || []).map(([x, y]) => key(x, y)));
    const onPath = new Set((state.lastRun?.path || []).map(([x, y]) => key(x, y)));

    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const k = key(x, y);
        let fill = "#111827";
        if (expanded.has(k)) fill = "#1e3a8a";
        if (onPath.has(k)) fill = "#2563eb";
        if (state.scene.obstacles.has(k)) fill = "#4b5563";
        if (x === state.scene.start[0] && y === state.scene.start[1]) fill = "#16a34a";
        if (x === state.scene.goal[0] && y === state.scene.goal[1]) fill = "#d97706";
        ctx.fillStyle = fill;
        ctx.fillRect(x * cw + 1, y * ch + 1, cw - 2, ch - 2);
      }
    }
  }

  function cellFromEvent(e) {
    const canvas = $("world");
    const rect = canvas.getBoundingClientRect();
    const w = state.demo.controls.grid_w;
    const h = state.demo.controls.grid_h;
    const x = Math.floor((e.clientX - rect.left) / rect.width * w);
    const y = Math.floor((e.clientY - rect.top) / rect.height * h);
    if (x < 0 || y < 0 || x >= w || y >= h) return null;
    return [x, y];
  }

  function onCanvasClick(e) {
    if (!state.scene) return;
    const cell = cellFromEvent(e);
    if (!cell) return;
    const [x, y] = cell;
    const k = key(x, y);
    if (e.altKey) {
      if (state.scene.obstacles.has(k)) state.scene.obstacles.delete(k);
      else {
        if ((x === state.scene.start[0] && y === state.scene.start[1]) ||
            (x === state.scene.goal[0] && y === state.scene.goal[1])) return;
        state.scene.obstacles.add(k);
      }
    } else if (e.shiftKey) {
      if (state.scene.obstacles.has(k)) return;
      state.scene.goal = [x, y];
    } else {
      if (state.scene.obstacles.has(k)) return;
      state.scene.start = [x, y];
    }
    state.lastRun = null;
    draw();
  }

  // Wire UI
  document.querySelectorAll(".step").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (!btn.disabled) showStep(btn.dataset.step);
    });
  });
  document.querySelectorAll("[data-go]").forEach((btn) => {
    btn.addEventListener("click", () => showStep(btn.dataset.go));
  });
  $("use-demo").addEventListener("click", () => loadDemo().catch((err) => {
    $("upload-status").textContent = err.message;
  }));
  $("run").addEventListener("click", runScenario);
  $("reset").addEventListener("click", () => {
    if (!state.demo) return;
    state.scene = {
      start: state.demo.default_scene.start.slice(),
      goal: state.demo.default_scene.goal.slice(),
      obstacles: new Set(state.demo.default_scene.obstacles.map(([x, y]) => key(x, y))),
    };
    state.lastRun = null;
    draw();
  });
  $("world").addEventListener("click", onCanvasClick);

  const drop = $("drop");
  const file = $("file");
  function handleFile(f) {
    if (!f) return;
    $("upload-status").textContent = `Selected “${f.name}” — prototype loads the path-planning demo method pack.`;
    loadDemo().catch((err) => { $("upload-status").textContent = err.message; });
  }
  file.addEventListener("change", () => handleFile(file.files[0]));
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("drag"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("drag"));
  drop.addEventListener("drop", (e) => {
    e.preventDefault();
    drop.classList.remove("drag");
    handleFile(e.dataTransfer.files[0]);
  });

  // Third-party simulation environments (future connectors — UI list only).
  const CONNECTORS = [
    { name: "AutoCAD", kind: "CAD / drafting and geometry" },
    { name: "Tinkercad", kind: "Browser CAD / simple 3D design" },
    { name: "SimScale", kind: "Cloud CAE (CFD, FEA, thermal)" },
    { name: "MATLAB / Simulink", kind: "Models, control, and system simulation" },
    { name: "Gazebo", kind: "Robot / world simulation (often with ROS)" },
    { name: "Webots", kind: "Robot simulation" },
    { name: "Unity", kind: "Interactive 3D / game-engine sims" },
    { name: "Unreal Engine", kind: "High-fidelity 3D environments" },
    { name: "ANSYS", kind: "Engineering multiphysics" },
    { name: "COMSOL Multiphysics", kind: "Physics-based FEM simulation" },
    { name: "Blender", kind: "3D scenes and simple physics" },
    { name: "PyBullet / MuJoCo", kind: "Physics engines for robotics & RL" },
    { name: "NVIDIA Isaac Sim", kind: "Robotics simulation" },
    { name: "OpenModelica", kind: "Modelica-based system simulation" },
  ];

  const connectorsPanel = $("connectors-panel");
  const connectorList = $("connector-list");
  connectorList.innerHTML = CONNECTORS.map((c) => `
    <li>
      <div>
        <div class="name">${esc(c.name)}</div>
        <span class="soon">Coming later</span>
      </div>
      <div class="kind">${esc(c.kind)}</div>
    </li>`).join("");

  function openConnectors(open) {
    connectorsPanel.hidden = !open;
    connectorsPanel.setAttribute("aria-hidden", open ? "false" : "true");
    $("connectors-btn").setAttribute("aria-expanded", open ? "true" : "false");
  }
  $("connectors-btn").addEventListener("click", () => openConnectors(connectorsPanel.hidden));
  $("connectors-close").addEventListener("click", () => openConnectors(false));
  connectorsPanel.addEventListener("click", (e) => {
    if (e.target === connectorsPanel) openConnectors(false);
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !connectorsPanel.hidden) openConnectors(false);
  });

  showStep("upload");
})();
