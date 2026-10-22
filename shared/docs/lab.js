// Shared behaviour for backend-lab HTML documents: TOC, scrollspy, theme, syntax highlight, mermaid.
// Classic script (not a module) so pages work when opened via file:// — module scripts are blocked there by CORS.
// Expects window.mermaid and window.hljs to be loaded before this file.
(() => {

const root = document.documentElement;

function storedTheme() {
  try { return localStorage.getItem("lab-theme"); } catch { return null; }
}
function isDark() {
  const t = root.dataset.theme;
  return t ? t === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
}

const saved = storedTheme();
if (saved) root.dataset.theme = saved;

// Build the table of contents from .part-title, h2 and h3 inside main.
function buildToc() {
  const nav = document.querySelector("nav.toc ol");
  if (!nav) return [];
  const headings = [...document.querySelectorAll("main .part-title, main h2, main h3")];
  const slug = (s) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/đ/g, "d").replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
  const tracked = [];
  for (const h of headings) {
    const li = document.createElement("li");
    if (h.classList.contains("part-title")) {
      li.className = "part";
      li.textContent = h.textContent;
      nav.appendChild(li);
      continue;
    }
    if (h.closest("details")) continue;
    // Hub pages may aggregate hundreds of questions; keep their TOC to the section headings.
    if (document.body.dataset.page === "hub" && h.closest("article.qa, article.ask")) continue;
    if (!h.id) h.id = slug(h.textContent) || `s-${tracked.length}`;
    li.className = h.tagName === "H2" ? "lvl-2" : "lvl-3";
    const a = document.createElement("a");
    a.href = `#${h.id}`;
    const num = h.querySelector(".num")?.textContent.trim();
    const label = [...h.childNodes].filter((n) => !(n.classList && n.classList.contains("num"))).map((n) => n.textContent).join("").trim();
    a.textContent = num ? `${num}. ${label}` : label;
    li.appendChild(a);
    nav.appendChild(li);
    tracked.push([h, a]);
  }
  return tracked;
}

function scrollspy(tracked) {
  if (!tracked.length) return;
  const byId = new Map(tracked.map(([h, a]) => [h.id, a]));
  let current = null;
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (!e.isIntersecting) continue;
      current?.classList.remove("active");
      current = byId.get(e.target.id);
      current?.classList.add("active");
    }
  }, { rootMargin: "0px 0px -75% 0px" });
  tracked.forEach(([h]) => io.observe(h));
}

async function renderMermaid() {
  const blocks = document.querySelectorAll("pre.mermaid, div.mermaid");
  const mermaid = window.mermaid;
  if (!blocks.length || !mermaid) return;
  // Capture sources and disable auto-render BEFORE awaiting, otherwise mermaid's own
  // startOnLoad replaces the text with SVG while we wait and we re-render garbage.
  blocks.forEach((b) => { if (!b.dataset.src) b.dataset.src = b.textContent; });
  mermaid.initialize({ startOnLoad: false });
  // Mermaid measures label text when it renders; wait for the web font or labels get clipped.
  try { await document.fonts?.ready; } catch { /* Font Loading API unavailable */ }
  mermaid.initialize({ startOnLoad: false, theme: isDark() ? "dark" : "default", securityLevel: "strict", fontFamily: getComputedStyle(document.body).fontFamily });
  // Render one diagram at a time with our own ids. mermaid.run() names each SVG after Date.now(),
  // so two diagrams rendered in the same millisecond share an id and d3 draws every diagram into
  // the first SVG (seen on ROADMAP.html with 20+ diagrams). A per-page counter makes ids unique.
  const pass = ++renderPass;
  for (const [i, b] of [...blocks].entries()) {
    if (pass !== renderPass) return; // a newer pass (theme toggle) took over
    b.removeAttribute("data-processed");
    try {
      const { svg, bindFunctions } = await mermaid.render(`lab-mmd-${pass}-${i}`, b.dataset.src);
      b.innerHTML = svg;
      bindFunctions?.(b);
    } catch (err) {
      console.error("[lab] mermaid render failed", err);
      b.textContent = b.dataset.src;
    }
  }
}
let renderPass = 0;

function highlight() {
  if (window.hljs) document.querySelectorAll("pre code").forEach((el) => window.hljs.highlightElement(el));
}

function setupThemeToggle() {
  const btn = document.querySelector(".theme-toggle");
  if (!btn) return;
  const label = () => { btn.textContent = isDark() ? "☀ Light" : "☾ Dark"; };
  label();
  btn.addEventListener("click", () => {
    root.dataset.theme = isDark() ? "light" : "dark";
    try { localStorage.setItem("lab-theme", root.dataset.theme); } catch { /* storage unavailable */ }
    label();
    syncHljsTheme();
    renderMermaid();
  });
}

function syncHljsTheme() {
  const light = document.getElementById("hljs-light");
  const dark = document.getElementById("hljs-dark");
  if (light && dark) { dark.disabled = !isDark(); light.disabled = isDark(); }
}

// Links between the documents of one topic; file N belongs to phase N.
const DOCS = [
  ["README.html", "README"],
  ["01-research.html", "1 · Research"],
  ["02-system-design.html", "2 · Design"],
  ["03-implementation.html", "3 · Implement"],
  ["04-experiment-plan.html", "4 · Plan"],
  ["05-results.html", "5 · Results"],
  ["06-conclusion.html", "6 · Conclusion"],
  ["07-production.html", "7 · Production"],
  ["suggested-questions.html", "Nên hỏi"],
  ["questions.html", "Hỏi đáp"],
];

// Repo-level pages (<body data-page="hub">): the home page index.html at the repo root and the hub
// pages in hub/. Paths are relative to the repo root and resolved from wherever the page lives.
const HUB = [
  ["index.html", "Trang chủ"],
  ["hub/lab.html", "Tổng quan"],
  ["hub/roadmap.html", "Lộ trình"],
  ["hub/problems.html", "Theo vấn đề"],
  ["hub/insights.html", "Kho insight"],
  ["hub/questions.html", "Hỏi đáp"],
  ["hub/benchmarks.html", "Số liệu"],
  ["hub/glossary.html", "Thuật ngữ"],
  ["hub/rules.html", "Quy tắc"],
];

function buildDocNav() {
  const header = document.querySelector("header.doc-header");
  if (!header) return;
  if (document.body.dataset.page === "hub") {
    const path = decodeURIComponent(location.pathname);
    const inHub = /\/hub\/[^/]*$/.test(path);
    const here = (inHub ? "hub/" : "") + path.split("/").pop();
    const nav = document.createElement("nav");
    nav.className = "doc-nav";
    nav.setAttribute("aria-label", "Trang tổng");
    for (const [file, label] of HUB) {
      const a = document.createElement("a");
      a.href = inHub ? (file.startsWith("hub/") ? file.slice(4) : "../" + file) : file;
      a.textContent = label;
      if (file === here) a.className = "current";
      nav.appendChild(a);
    }
    header.appendChild(nav);
    return;
  }
  const here = decodeURIComponent(location.pathname.split("/").pop());
  const nav = document.createElement("nav");
  nav.className = "doc-nav";
  nav.setAttribute("aria-label", "Tài liệu của topic");
  // In templates/ the topic README is topic-README.html; inside topics/<slug>/ it is README.html.
  const inTemplates = /\/templates\/[^/]*$/.test(decodeURIComponent(location.pathname));
  for (const [file, label] of DOCS) {
    const target = inTemplates && file === "README.html" ? "topic-README.html" : file;
    const a = document.createElement("a");
    a.href = target;
    a.textContent = label;
    if (target === here) a.className = "current";
    nav.appendChild(a);
  }
  header.appendChild(nav);
}

// Self-quiz on Q&A pages (questions.html, suggested-questions.html, hub/questions.html): a toolbar button hides
// answers/hints (body.qa-quiz); clicking a question reveals that entry. The mode is remembered per browser.
function setupQuiz() {
  const entries = document.querySelectorAll("article.qa, article.ask");
  if (!entries.length) return;
  const KEY = "lab-qa-quiz";
  const body = document.body;
  const bar = document.createElement("div");
  bar.className = "qa-toolbar";
  const btn = document.createElement("button");
  btn.type = "button";
  const count = document.createElement("span");
  const real = [...entries].filter((e) => !e.closest(".guide"));
  const n = (sel) => real.filter((e) => e.matches(sel)).length;
  const parts = [];
  if (n("article.qa")) parts.push(`${n("article.qa")} câu hỏi · ${n("article.qa[data-status=open]")} chưa trả lời`);
  if (n("article.ask")) parts.push(`${n("article.ask")} câu gợi ý · ${n("article.ask[data-status=suggested]")} chưa hỏi`);
  count.textContent = parts.join(" — ");
  bar.append(btn, count);
  const label = () => { btn.textContent = body.classList.contains("qa-quiz") ? "Hiện đáp án" : "Ẩn đáp án (tự kiểm tra)"; };
  const set = (on) => {
    body.classList.toggle("qa-quiz", on);
    entries.forEach((e) => e.classList.remove("revealed"));
    try { localStorage.setItem(KEY, on ? "1" : "0"); } catch { /* storage unavailable */ }
    label();
  };
  let stored = null;
  try { stored = localStorage.getItem(KEY); } catch { /* storage unavailable */ }
  body.classList.toggle("qa-quiz", stored === "1");
  label();
  btn.addEventListener("click", () => set(!body.classList.contains("qa-quiz")));
  for (const e of entries) {
    const q = e.querySelector("h3.q");
    if (!q) continue;
    q.tabIndex = 0;
    const reveal = () => { if (body.classList.contains("qa-quiz")) e.classList.toggle("revealed"); };
    q.addEventListener("click", reveal);
    q.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); reveal(); } });
  }
  const header = document.querySelector("header.doc-header");
  if (header) header.after(bar); else document.querySelector("main")?.prepend(bar);
}

buildDocNav();
setupQuiz();
scrollspy(buildToc());
setupThemeToggle();
syncHljsTheme();
highlight();
renderMermaid();
})();
