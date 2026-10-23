// Coursera-style demo catalog page.
(function () {
  const $ = (id) => document.getElementById(id);
  function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function stars(n) {
    const full = Math.round(Number(n) || 0);
    return "★".repeat(Math.min(5, full)) + "☆".repeat(Math.max(0, 5 - Math.min(5, full)));
  }

  function renderCourses(items) {
    const el = $("cr-courses");
    if (!el) return;
    el.innerHTML = (items || []).map((c) => `
      <article class="cr-course">
        <div class="cr-course-thumb" style="background:${esc(c.color || "#0056d2")}">${esc(c.type || "Course")}</div>
        <div class="cr-course-body">
          <p class="cr-partner">${esc(c.partner)}</p>
          <h3 class="cr-course-title">${esc(c.title)}</h3>
          <p class="cr-rating">${stars(c.rating)} ${esc(c.rating)} <span class="cr-meta">(${esc(c.reviews)})</span></p>
          <p class="cr-meta">${esc(c.level)} · ${esc(c.duration)}</p>
          ${c.tag ? `<span class="cr-tag">${esc(c.tag)}</span>` : ""}
          <a class="cr-enroll" href="${esc(c.url)}" target="_blank" rel="noopener">Go to course</a>
        </div>
      </article>`).join("");
  }

  function renderList(elId, items, kindFallback) {
    const el = $(elId);
    if (!el) return;
    el.innerHTML = (items || []).map((it) => {
      const kind = it.kind || kindFallback || "Item";
      const meta = [it.channel, it.source, it.venue, it.date, it.year, it.duration]
        .filter(Boolean).map(esc).join(" · ");
      return `<article class="cr-item">
        <div class="cr-item-kind">${esc(kind)}</div>
        <div>
          <h3><a href="${esc(it.url)}" target="_blank" rel="noopener">${esc(it.title)}</a></h3>
          <p>${esc(it.blurb || "")}</p>
          <p class="cr-source">${meta}</p>
        </div>
        <a class="cr-open" href="${esc(it.url)}" target="_blank" rel="noopener">Open</a>
      </article>`;
    }).join("") || `<p class="cr-muted">Nothing listed yet.</p>`;
  }

  async function load() {
    const res = await fetch("/demo/coursera_catalog.json");
    if (!res.ok) throw new Error("Could not load Coursera catalog");
    const data = await res.json();
    $("cr-hero-title").textContent = data.hero?.title || "Learn on Coursera";
    $("cr-hero-sub").textContent = data.hero?.subtitle
      || `Topic: ${data.topic || ""}`;
    renderCourses(data.courses);
    renderList("cr-videos", data.videos, "Video");
    renderList("cr-articles", data.articles, "Article");
    renderList("cr-news", data.news, "News");
    renderList("cr-journals", data.journals, "Journal");
  }

  $("cr-explore")?.addEventListener("click", () => {
    document.getElementById("courses")?.scrollIntoView({ behavior: "smooth" });
  });

  load().catch((err) => {
    const sub = $("cr-hero-sub");
    if (sub) sub.textContent = err.message;
  });
})();
