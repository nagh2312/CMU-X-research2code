// Immersive connector screens: Coursera lecture, YouTube watch, News article.
(function () {
  const $ = (id) => document.getElementById(id);
  function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function platformKey() {
    const path = location.pathname.replace(/\/+$/, "");
    if (path === "/coursera") return "coursera";
    const m = path.match(/\/connect\/([a-z]+)/i);
    return (m && m[1].toLowerCase()) || "coursera";
  }

  function paperIdFromQuery() {
    return new URLSearchParams(location.search).get("paper")
      || sessionStorage.getItem("r2l_paper_id")
      || null;
  }

  function playerHTML({ badge, title, duration, variant }) {
    const playClass = variant === "youtube" ? "player-play yt" : "player-play";
    return `
      <button type="button" class="player-stage" data-play-demo aria-label="Play lecture video (demo — not started)">
        <span class="player-badge">${esc(badge)}</span>
        <span class="${playClass}" aria-hidden="true"></span>
        <span class="player-caption">
          <span>${esc(title)}</span>
          <span>${esc(duration || "0:00")} · Not started</span>
        </span>
        <span class="player-progress" aria-hidden="true"><i></i></span>
      </button>`;
  }

  function wirePlayer(root, outboundUrl) {
    root.querySelectorAll("[data-play-demo]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const bar = btn.querySelector(".player-progress > i");
        if (bar) bar.style.width = "3%";
        const cap = btn.querySelector(".player-caption span:last-child");
        if (cap) cap.textContent = (cap.textContent || "").replace("Not started", "Ready — opens platform");
        // Brief beat so it feels like a player, then go to the real platform search/course.
        setTimeout(() => {
          if (outboundUrl) window.open(outboundUrl, "_blank", "noopener");
        }, 350);
      });
    });
  }

  function renderCoursera(paper, pack) {
    const lectures = pack.lectures || [];
    let idx = Number(pack.active_lecture) || 0;
    if (idx < 0 || idx >= lectures.length) idx = 0;

    const app = $("cx-app");
    const paint = () => {
      const lec = lectures[idx] || {};
      document.title = `${pack.course_title || "Course"} | Coursera`;
      app.innerHTML = `
        <header class="cr-top">
          <div class="cr-top-inner">
            <a class="cr-logo" href="/connect/coursera">coursera</a>
            <div class="cr-search"><input value="${esc(paper.topic || "")}" readonly aria-label="Search"><span>⌕</span></div>
            <div class="cr-top-meta">Lecture · mapped to your paper</div>
          </div>
        </header>
        <div class="cr-course-head">
          <p class="cr-partner">${esc(pack.partner || "Partner")}</p>
          <h1>${esc(pack.course_title || "Course")}</h1>
          <p class="cr-stars">★ ${esc(pack.rating || "4.9")} · ${esc(pack.enrolled || "")} · ${esc(pack.level || "")}</p>
          <p class="cr-mapped">Mapped from: ${esc(paper.paper_name)}</p>
        </div>
        <div class="cr-layout">
          <section>
            ${playerHTML({
              badge: "Lecture video",
              title: lec.title || "Lecture",
              duration: lec.duration,
              variant: "coursera",
            })}
            <h2 class="cr-lecture-title">${esc(lec.title || "")}</h2>
            <p class="cr-lecture-meta">${esc(lec.week || "Week")} · ${esc(lec.duration || "")} · Video yet to be played</p>
            <p class="cr-blurb">${esc(lec.blurb || "")}</p>
            <div class="cr-actions">
              <a class="cr-btn primary" href="${esc(lec.url || pack.url)}" target="_blank" rel="noopener">Continue on Coursera</a>
              <a class="cr-btn ghost" href="${esc(pack.url)}" target="_blank" rel="noopener">Open full course</a>
            </div>
          </section>
          <aside class="cr-sidebar">
            <div class="cr-sidebar-h">Course content · paper-mapped lectures</div>
            ${lectures.map((l, i) => `
              <button type="button" class="cr-lec ${i === idx ? "active" : ""}" data-lec="${i}">
                <span class="cr-lec-num">${i + 1}</span>
                <span>
                  <p class="cr-lec-title">${esc(l.title)}</p>
                  <p class="cr-lec-week">${esc(l.week)}</p>
                </span>
                <span class="cr-lec-dur">${esc(l.duration)}</span>
              </button>`).join("")}
          </aside>
        </div>`;
      app.querySelectorAll("[data-lec]").forEach((btn) => {
        btn.addEventListener("click", () => {
          idx = Number(btn.dataset.lec);
          paint();
        });
      });
      wirePlayer(app, lec.url || pack.url);
    };
    paint();
  }

  function renderYouTube(paper, pack) {
    const videos = pack.videos || [];
    let idx = Number(pack.active) || 0;
    if (idx < 0 || idx >= videos.length) idx = 0;
    const app = $("cx-app");

    const paint = () => {
      const v = videos[idx] || {};
      document.title = `${v.title || "Video"} - YouTube`;
      app.innerHTML = `
        <header class="yt-top">
          <div class="yt-top-inner">
            <a class="yt-logo" href="/connect/youtube"><b>▶</b> YouTube</a>
            <div class="yt-search"><input value="${esc(paper.topic || "")}" readonly aria-label="Search"><span>⌕</span></div>
          </div>
        </header>
        <div class="yt-layout">
          <section>
            ${playerHTML({
              badge: "Up next · not playing",
              title: v.title || "Video",
              duration: v.duration,
              variant: "youtube",
            })}
            <h1 class="yt-title">${esc(v.title || "")}</h1>
            <p class="yt-sub">${esc(v.views || "")} · ${esc(v.ago || "")} · ${esc(v.duration || "")}</p>
            <div class="yt-channel">
              <div class="yt-avatar" aria-hidden="true"></div>
              <div>
                <b>${esc(v.channel || "Channel")}</b>
                <div class="yt-mapped">Mapped to your paper: ${esc(paper.paper_name)}</div>
              </div>
            </div>
            <div class="yt-desc">${esc(v.blurb || "")}</div>
            <a class="yt-open" href="${esc(v.url)}" target="_blank" rel="noopener">Open on YouTube</a>
          </section>
          <aside>
            <p class="yt-side-h">Videos mapped to your research paper</p>
            ${videos.map((item, i) => `
              <button type="button" class="yt-rec ${i === idx ? "active" : ""}" data-yt="${i}">
                <div class="yt-thumb"><span>${esc(item.duration || "")}</span></div>
                <div>
                  <p class="yt-rec-title">${esc(item.title)}</p>
                  <p class="yt-rec-meta">${esc(item.channel)}</p>
                  <p class="yt-rec-meta">${esc(item.views)}</p>
                </div>
              </button>`).join("")}
          </aside>
        </div>`;
      app.querySelectorAll("[data-yt]").forEach((btn) => {
        btn.addEventListener("click", () => {
          idx = Number(btn.dataset.yt);
          paint();
        });
      });
      wirePlayer(app, v.url);
    };
    paint();
  }

  function renderNews(paper, pack) {
    const articles = pack.articles || [];
    let idx = Number(pack.active) || 0;
    if (idx < 0 || idx >= articles.length) idx = 0;
    const app = $("cx-app");

    const paint = () => {
      const a = articles[idx] || {};
      document.title = `${a.title || "Article"} | News`;
      const paras = (a.body || [a.blurb || ""]).map((p) => `<p>${esc(p)}</p>`).join("");
      app.innerHTML = `
        <header class="nw-mast">
          <div class="nw-mast-inner">
            <a class="nw-brand" href="/connect/news">The Paper Desk</a>
            <p class="nw-date-line">News · mapped to your research upload</p>
          </div>
        </header>
        <article class="nw-layout">
          <p class="nw-kicker">${esc(a.kicker || a.meta || "News")}</p>
          <h1>${esc(a.title || "")}</h1>
          <p class="nw-byline">By ${esc(a.author || "Staff")} · ${esc(a.source || "")} · ${esc(a.date || "")}</p>
          <div class="nw-hero">Feature image · ${esc(paper.topic || "research topic")}</div>
          <div class="nw-mapped">Mapped to uploaded paper: <b>${esc(paper.paper_name)}</b> — ${esc(paper.one_line || "")}</div>
          <div class="nw-body">${paras}</div>
          <div class="nw-actions">
            <a class="nw-btn" href="${esc(a.url)}" target="_blank" rel="noopener">Read on news platform</a>
          </div>
          <div class="nw-related">
            <h2>More articles mapped to this paper</h2>
            ${articles.map((item, i) => `
              <button type="button" data-nw="${i}">
                <h3>${esc(item.title)}</h3>
                <p>${esc(item.source)} · ${esc(item.date || "")}</p>
              </button>`).join("")}
          </div>
        </article>`;
      app.querySelectorAll("[data-nw]").forEach((btn) => {
        btn.addEventListener("click", () => {
          idx = Number(btn.dataset.nw);
          paint();
          window.scrollTo({ top: 0, behavior: "smooth" });
        });
      });
    };
    paint();
  }

  function renderJournals(paper, items) {
    document.title = "Technical journals | Connectors";
    $("cx-app").innerHTML = `
      <div class="jn-wrap">
        <h1>Technical journals</h1>
        <p>Mapped to <b>${esc(paper.paper_name)}</b></p>
        <div class="jn-list">
          ${(items || []).map((it) => `
            <article class="jn-item">
              <h3><a href="${esc(it.url)}" target="_blank" rel="noopener">${esc(it.title)}</a></h3>
              <p>${esc(it.source)} · ${esc(it.meta || "")}</p>
              <p>${esc(it.blurb || "")}</p>
            </article>`).join("")}
        </div>
      </div>`;
  }

  async function load() {
    const key = platformKey();
    document.body.classList.add(`platform-${key}`);

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

    if (key === "coursera") return renderCoursera(paper, paper.coursera || {});
    if (key === "youtube") return renderYouTube(paper, paper.youtube || {});
    if (key === "news") return renderNews(paper, paper.news || {});
    if (key === "journals") return renderJournals(paper, paper.journals || []);
    $("cx-app").innerHTML = `<p class="cx-loading">Unknown connector.</p>`;
  }

  load().catch((err) => {
    const app = $("cx-app");
    if (app) app.innerHTML = `<p class="cx-loading">${esc(err.message)}</p>`;
  });
})();
