// Connector destination: materials mapped to the uploaded research paper.
(function () {
  const PLATFORMS = {
    coursera: {
      key: "coursera",
      brand: "coursera",
      title: "Courses for your paper",
      subtitle: "Study platforms → Coursera. Materials are chosen from the paper you uploaded in Learn by Doing.",
      cta: "Go to Coursera",
      listLabel: "Mapped courses",
      kind: "Course",
      useCards: true,
    },
    youtube: {
      key: "youtube",
      brandHtml: 'You<span>Tube</span>',
      title: "Videos for your paper",
      subtitle: "Study platforms → YouTube. Watch/list results mapped to your uploaded paper’s method.",
      cta: "Watch on YouTube",
      listLabel: "Mapped videos",
      kind: "Video",
      useCards: false,
    },
    news: {
      key: "news",
      brand: "News",
      title: "News articles for your paper",
      subtitle: "Study platforms → News. Latest and published coverage mapped to your paper’s topic.",
      cta: "Open article",
      listLabel: "Mapped news",
      kind: "News",
      useCards: false,
    },
    journals: {
      key: "journals",
      brand: "Journals",
      title: "Technical journals for your paper",
      subtitle: "Study platforms → Technical journals. Foundational papers mapped to your upload.",
      cta: "Open journal",
      listLabel: "Mapped journals",
      kind: "Journal",
      useCards: false,
    },
  };

  const $ = (id) => document.getElementById(id);
  function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function platformFromPath() {
    const path = location.pathname.replace(/\/+$/, "");
    if (path === "/coursera") return PLATFORMS.coursera;
    const m = path.match(/\/connect\/([a-z]+)/i);
    return (m && PLATFORMS[m[1].toLowerCase()]) || PLATFORMS.coursera;
  }

  function paperIdFromQuery() {
    const q = new URLSearchParams(location.search);
    return q.get("paper")
      || sessionStorage.getItem("r2l_paper_id")
      || null;
  }

  function renderCards(items, cta) {
    return (items || []).map((it) => `
      <article class="cx-card">
        <div class="cx-thumb" style="background:${esc(it.color || "#0056d2")}">${esc(it.meta || "Course")}</div>
        <div class="cx-card-body">
          <p>${esc(it.partner || it.source || it.channel || "")}</p>
          <h3>${esc(it.title)}</h3>
          <p>${esc(it.blurb || "")}</p>
          <p>${esc(it.meta || "")}</p>
          <a class="cx-cta" href="${esc(it.url)}" target="_blank" rel="noopener">${esc(cta)}</a>
        </div>
      </article>`).join("");
  }

  function renderRows(items, kind, cta) {
    return (items || []).map((it) => `
      <article class="cx-row">
        <div class="cx-kind">${esc(it.kind || kind)}</div>
        <div>
          <h3><a href="${esc(it.url)}" target="_blank" rel="noopener">${esc(it.title)}</a></h3>
          <p>${esc(it.blurb || "")}</p>
          <p class="cx-muted">${esc([it.channel, it.source, it.partner, it.meta].filter(Boolean).join(" · "))}</p>
        </div>
        <a class="cx-open" href="${esc(it.url)}" target="_blank" rel="noopener">${esc(cta)}</a>
      </article>`).join("");
  }

  async function load() {
    const platform = platformFromPath();
    document.body.classList.add(`platform-${platform.key}`);

    const brand = $("cx-brand");
    if (brand) {
      if (platform.brandHtml) brand.innerHTML = platform.brandHtml;
      else brand.textContent = platform.brand;
    }
    $("cx-hero-title").textContent = platform.title;
    $("cx-hero-sub").textContent = platform.subtitle;
    $("cx-list-label").textContent = platform.listLabel;

    const res = await fetch("/demo/paper_connector_materials.json");
    if (!res.ok) throw new Error("Could not load paper→connector map");
    const data = await res.json();

    let paperId = paperIdFromQuery() || data.default_paper_id;
    let paper = data.papers[paperId];
    if (!paper) {
      paperId = data.default_paper_id;
      paper = data.papers[paperId];
    }
    sessionStorage.setItem("r2l_paper_id", paperId);

    $("cx-paper-name").textContent = paper.paper_name || paperId;
    $("cx-paper-topic").textContent = paper.topic || "";
    $("cx-paper-line").textContent = paper.one_line || "";

    const items = paper[platform.key] || [];
    const host = $("cx-materials");
    if (!items.length) {
      host.innerHTML = `<div class="cx-empty"><p><b>No materials mapped yet</b> for this paper on ${esc(platform.brand || platform.key)}.</p>
        <p class="cx-muted">Upload a supported demo paper in the workbench, then reopen Connectors.</p>
        <p><a href="/">← Back to Learn by Doing</a></p></div>`;
      return;
    }

    host.innerHTML = platform.useCards
      ? `<div class="cx-grid">${renderCards(items, platform.cta)}</div>`
      : `<div class="cx-list">${renderRows(items, platform.kind, platform.cta)}</div>`;

    // Update outbound links context note
    const note = $("cx-redirect-note");
    if (note) {
      note.textContent = `Selecting an item opens ${platform.brand || platform.key} (or search) in a new tab. Mapping used paper id “${paperId}”.`;
    }
  }

  load().catch((err) => {
    const host = $("cx-materials");
    if (host) host.innerHTML = `<div class="cx-empty"><p>${esc(err.message)}</p><p><a href="/">← Back</a></p></div>`;
  });
})();
