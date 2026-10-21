// Builds the prerequisite diagrams on hub/roadmap.html from the topic table, so the table rows are the
// single source of truth (no hand-maintained mermaid source).
// Must run BEFORE lab.js (both deferred: this script is listed first in <head>), because lab.js
// renders every pre.mermaid on load.
(() => {
  const rows = [...document.querySelectorAll("table.roadmap tr[data-slug]")];
  if (!rows.length) return;

  const STATUS = ["planned", "in-progress", "done", "skipped"];
  const topics = new Map(rows.map((tr) => [tr.dataset.slug, {
    slug: tr.dataset.slug,
    track: tr.dataset.track,
    status: STATUS.includes(tr.dataset.status) ? tr.dataset.status : "planned",
    prereq: (tr.dataset.prereq || "").split(",").map((s) => s.trim()).filter(Boolean),
    name: (tr.querySelector("td strong")?.textContent || tr.dataset.slug).trim(),
  }]));

  // Track display names come from the diagram containers: <figure data-roadmap="<track>" data-track-name="...">
  const figures = [...document.querySelectorAll("figure[data-roadmap]")];
  const trackName = new Map(figures.filter((f) => f.dataset.roadmap !== "overview")
    .map((f) => [f.dataset.roadmap, f.dataset.trackName || f.dataset.roadmap]));

  const id = (slug) => "t_" + slug.replace(/[^a-zA-Z0-9]/g, "_");
  // Track keys may contain '-' (e.g. search-storage), which mermaid's parser treats as edge syntax;
  // prefixing also keeps overview node ids distinct from track subgraph ids across diagrams on one page.
  const gid = (track) => "g_" + track.replace(/[^a-zA-Z0-9]/g, "_");
  const oid = (track) => "o_" + track.replace(/[^a-zA-Z0-9]/g, "_");
  const label = (text) => text.replace(/"/g, "'").replace(/[<>]/g, "");
  const CLASSDEFS = [
    "    classDef planned stroke-width:1px",
    "    classDef in-progress stroke:#e0a030,stroke-width:3px",
    "    classDef done stroke:#2e9d62,stroke-width:3px",
    "    classDef skipped stroke-dasharray:2 2,opacity:0.5",
    "    classDef ext stroke-dasharray:4 3,opacity:0.75",
  ];
  const statusClass = (t) => (t.status === "in-progress" ? "in-progress" : t.status);

  function trackDiagram(track) {
    const own = [...topics.values()].filter((t) => t.track === track);
    const ownSlugs = new Set(own.map((t) => t.slug));
    const lines = ["flowchart LR", ...CLASSDEFS];
    const external = new Set();
    own.forEach((t) => t.prereq.forEach((p) => { if (!ownSlugs.has(p) && topics.has(p)) external.add(p); }));
    lines.push(`    subgraph ${gid(track)}["${label(trackName.get(track) || track)}"]`);
    lines.push("      direction LR");
    own.forEach((t) => lines.push(`      ${id(t.slug)}["${label(t.name)}"]:::${statusClass(t)}`));
    lines.push("    end");
    lines.push(`    style ${gid(track)} fill:transparent,stroke-dasharray:6 4`);
    external.forEach((p) => {
      const t = topics.get(p);
      lines.push(`    ${id(p)}["${label(t.name)} · ${label(trackName.get(t.track) || t.track)}"]:::ext`);
    });
    own.forEach((t) => t.prereq.forEach((p) => {
      if (!topics.has(p)) return;
      lines.push(`    ${id(p)} ${ownSlugs.has(p) ? "-->" : "-.->"} ${id(t.slug)}`);
    }));
    return lines.join("\n");
  }

  function overviewDiagram() {
    const counts = new Map();
    const done = new Map();
    topics.forEach((t) => {
      counts.set(t.track, (counts.get(t.track) || 0) + 1);
      if (t.status === "done") done.set(t.track, (done.get(t.track) || 0) + 1);
    });
    const edges = new Map();
    topics.forEach((t) => t.prereq.forEach((p) => {
      const from = topics.get(p)?.track;
      if (from && from !== t.track) edges.set(`${from}|${t.track}`, (edges.get(`${from}|${t.track}`) || 0) + 1);
    }));
    const lines = ["flowchart LR"];
    trackName.forEach((name, track) => {
      if (!counts.has(track)) return;
      lines.push(`    ${oid(track)}["${label(name)}<br/>${done.get(track) || 0}/${counts.get(track)} xong"]`);
    });
    edges.forEach((n, key) => {
      const [a, b] = key.split("|");
      lines.push(`    ${oid(a)} -->|${n}| ${oid(b)}`);
    });
    return lines.join("\n");
  }

  // Header counts are derived from the table too, so they never drift from the rows.
  const total = document.querySelector("[data-roadmap-total]");
  if (total) total.textContent = `${topics.size} topic đề xuất`;
  const byTrack = document.querySelector("[data-roadmap-by-track]");
  if (byTrack) {
    const per = new Map();
    topics.forEach((t) => per.set(t.track, (per.get(t.track) || 0) + 1));
    byTrack.textContent = [...trackName].filter(([k]) => per.has(k)).map(([k, n]) => `${n}: ${per.get(k)}`).join(", ");
  }

  for (const fig of figures) {
    const kind = fig.dataset.roadmap;
    const pre = document.createElement("pre");
    pre.className = "mermaid";
    pre.textContent = kind === "overview" ? overviewDiagram() : trackDiagram(kind);
    fig.insertBefore(pre, fig.firstChild);
  }
})();
