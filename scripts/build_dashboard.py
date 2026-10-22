#!/usr/bin/env python3
"""Build the lab dashboard (LAB.html), the reference-numbers hub (BENCHMARKS.html) and the
auto-generated "Topic liên quan" section of every topic README.

Sources (read only, except the related-topics block):
  - topics/<slug>/README.html   status via data-* (mode, type, current-phase, updated, phases,
                                 approvals, decision log)
  - ROADMAP.html                tr[data-slug] rows: track, prerequisites, priority, suggested mode
  - topics/*/NN-*.html          insight tags (via scripts/build_insights.py), [data-problem] slugs
  - topics/*/05-results.html    [data-bench] rows (reference measurements, see the template comment)
  - topics/*/results/env.md     environment summary shown next to each benchmark
  - topics/*/questions.html, topics/*/suggested-questions.html
                                 open/revisit Q&A entries and suggested questions not asked yet
                                 (via scripts/build_questions.py)

Outputs:
  - LAB.html: counts, roadmap progress per track, every topic with phase chips, approvals waiting
    for the user, topics ready to study next, recent decisions;
  - BENCHMARKS.html: measurements grouped by quantity slug so the same quantity measured in several
    topics/environments sits side by side, with search/filter;
  - topics/*/README.html: only the region between <!-- related:start --> and <!-- related:end -->
    (prerequisites, dependents, shared insight tags, shared problem slugs — each with its reason).

Usage:
    python3 scripts/build_dashboard.py               # LAB.html + BENCHMARKS.html + related sections
    python3 scripts/build_dashboard.py --no-related  # do not touch topic READMEs
    python3 scripts/build_dashboard.py --check       # validate benchmark rows; exit 1 on problems
    python3 scripts/build_dashboard.py --include-underscore --roadmap /tmp/ROADMAP.html   # test fixtures

topics/_* directories are test fixtures (real slugs never start with "_") and are skipped by default.

Check rules for each [data-bench] element with a non-empty slug:
  - slug is lowercase kebab-case; value is a number; unit and metric are present;
  - ci-low / ci-high, when given, are numbers with ci-low <= value <= ci-high;
  - data-raw is given and the file exists (relative to the topic directory).

Standard library only.
"""

import argparse
import html
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_insights as bi  # noqa: E402  (shared minimal DOM + insight index)
import build_questions as bq  # noqa: E402  (Q&A log counts)
from _paths import hub_path, hubify  # noqa: E402

ROOT = bi.ROOT
# Real topic slugs are kebab-case and never start with "_" (scripts/new-topic.sh enforces it); "_"-prefixed
# directories are scratch/test fixtures and are ignored unless --include-underscore is given.
INCLUDE_UNDERSCORE = False


def topic_dirs():
    tdir = ROOT / "topics"
    if not tdir.exists():
        return []
    return [p for p in sorted(tdir.iterdir()) if p.is_dir() and (INCLUDE_UNDERSCORE or not p.name.startswith("_"))]
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
PHASES = {1: "Research", 2: "Design", 3: "Implement", 4: "Plan", 5: "Execute", 6: "Conclusion", 7: "Production"}
STATUS_LABEL = {"todo": "Chưa làm", "in-progress": "Đang làm", "done": "Xong", "skipped": "Bỏ qua",
                "planned": "Dự kiến"}
MARK_START, MARK_END = "<!-- related:start -->", "<!-- related:end -->"


def e(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def num(s):
    try:
        return float(str(s).strip())
    except (TypeError, ValueError):
        return None


def fmt(v):
    if v is None:
        return ""
    return f"{v:g}" if abs(v) < 1e6 else f"{v:,.0f}"


# ---------------------------------------------------------------- roadmap
def read_roadmap(path=None):
    path = Path(path) if path else hub_path("roadmap")
    rows, tracks = [], {}
    if not path.exists():
        return rows, tracks
    dom = bi.parse(path)
    for fig in dom.iter():
        if fig.attrs.get("data-roadmap") and fig.attrs.get("data-track-name"):
            tracks[fig.attrs["data-roadmap"]] = fig.attrs["data-track-name"]
    for tr in dom.find_all("tr"):
        slug = tr.attrs.get("data-slug")
        if not slug:
            continue
        name_node = tr.find("strong")
        rows.append({
            "slug": slug,
            "name": name_node.text() if name_node else slug,
            "track": tr.attrs.get("data-track", ""),
            "prereq": [p.strip() for p in (tr.attrs.get("data-prereq") or "").split(",") if p.strip()],
            "mode": tr.attrs.get("data-mode", "full"),
            "priority": int(num(tr.attrs.get("data-priority")) or 3),
            "status": tr.attrs.get("data-status", "planned"),
        })
    return rows, tracks


# ---------------------------------------------------------------- topics
def field(dom, name):
    for n in dom.iter():
        if n.attrs.get("data-field") == name:
            return n.text()
    return ""


def read_topic(tdir):
    readme = tdir / "README.html"
    dom = bi.parse(readme)
    h1 = dom.find("h1")
    phases = {}
    for li in dom.find_all("li"):
        p = num(li.attrs.get("data-phase"))
        if p and li.attrs.get("data-status"):
            phases[int(p)] = li.attrs["data-status"]
    approvals, questions = [], 0
    for ul in dom.find_all("ul"):
        if "approvals" in ul.classes:
            for li in ul.find_all("li"):
                if li.attrs.get("data-status") == "open":
                    approvals.append({"phase": li.attrs.get("data-phase", ""), "text": li.text()})
        if "questions" in ul.classes:
            questions += sum(1 for li in ul.find_all("li") if li.attrs.get("data-status") == "open")
    decisions = []
    for table in dom.find_all("table"):
        if "decisions" not in table.classes:
            continue
        body = table.find("tbody") or table
        for tr in body.find_all("tr"):
            cells = [td.text() for td in tr.find_all("td")]
            if len(cells) >= 3 and re.match(r"\d{4}-\d{2}-\d{2}", cells[0] or ""):
                decisions.append({"date": cells[0], "phase": cells[1], "decision": cells[2],
                                  "reason": cells[3] if len(cells) > 3 else ""})
    qa_pending, ask_pending = bq.pending_counts(tdir)
    statuses = [phases.get(i, "todo") for i in PHASES]
    if all(s in ("done", "skipped") for s in statuses):
        overall = "done"
    elif any(s in ("done", "in-progress") for s in statuses):
        overall = "in-progress"
    else:
        overall = "planned"
    return {
        "slug": tdir.name,
        "title": h1.text() if h1 else tdir.name,
        "mode": field(dom, "mode") or "full",
        "type": field(dom, "type") or "standard",
        "current_phase": field(dom, "current-phase"),
        "updated": field(dom, "updated"),
        "phases": phases,
        "approvals": approvals,
        "questions": questions,
        "qa_pending": qa_pending,
        "ask_pending": ask_pending,
        "decisions": decisions,
        "overall": overall,
    }


def read_topics():
    return [read_topic(p) for p in topic_dirs() if (p / "README.html").exists()]


def read_problems():
    """topic slug -> set of problem slugs from [data-problem] elements outside author guidance."""
    out = {}
    for topic in topic_dirs():
        slugs = set()
        for page in sorted(topic.glob("[0-9][0-9]-*.html")):
            for n in bi.parse(page).iter():
                raw = n.attrs.get("data-problem")
                if raw and not n.has_ancestor_class("guide"):
                    slugs.update(s.strip().lower() for s in raw.split(",") if s.strip())
        if slugs:
            out[topic.name] = slugs
    return out


def read_env(tdir):
    """Pick a few rows of results/env.md (markdown table 'Mục | Giá trị | ...') for display."""
    path = tdir / "results" / "env.md"
    if not path.exists():
        return ""
    wanted = ("CPU", "RAM", "OS", "Docker", "JDK")
    parts = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[1] and any(cells[0].startswith(w) for w in wanted):
            parts.append(f"{cells[0].split('(')[0].strip()}: {cells[1]}")
    return " · ".join(parts)


# ---------------------------------------------------------------- benchmarks
def read_benchmarks(topics):
    titles = {t["slug"]: t["title"] for t in topics}
    out, problems = [], []
    for topic in topic_dirs():
        page = topic / "05-results.html"
        if not page.exists():
            continue
        dom = bi.parse(page)
        body = dom.find("body")
        draft = bool(body and "draft" in body.classes)
        env = read_env(topic)
        for n in dom.iter():
            slug = (n.attrs.get("data-bench") or "").strip()
            if not slug or n.has_ancestor_class("guide"):
                continue
            a = n.attrs
            b = {
                "slug": slug, "topic": topic.name, "topic_title": titles.get(topic.name, topic.name),
                "value": num(a.get("data-value")), "unit": (a.get("data-unit") or "").strip(),
                "ci_low": num(a.get("data-ci-low")), "ci_high": num(a.get("data-ci-high")),
                "metric": (a.get("data-metric") or "").strip(), "conditions": (a.get("data-conditions") or "").strip(),
                "raw": (a.get("data-raw") or "").strip(), "env": (a.get("data-env") or "results/env.md").strip(),
                "env_summary": env, "draft": draft, "label": n.text(),
            }
            where = f"topics/{topic.name}/05-results.html [{slug}]"
            if not SLUG_RE.match(slug):
                problems.append(f"{where}: slug không phải kebab-case chữ thường")
            if b["value"] is None:
                problems.append(f"{where}: data-value không phải số ({a.get('data-value')!r})")
            if not b["unit"]:
                problems.append(f"{where}: thiếu data-unit")
            if not b["metric"]:
                problems.append(f"{where}: thiếu data-metric")
            for k in ("data-ci-low", "data-ci-high"):
                if (a.get(k) or "").strip() and num(a.get(k)) is None:
                    problems.append(f"{where}: {k} không phải số")
            if None not in (b["ci_low"], b["ci_high"], b["value"]) and not (b["ci_low"] <= b["value"] <= b["ci_high"]):
                problems.append(f"{where}: value nằm ngoài [ci-low, ci-high]")
            if not b["raw"]:
                problems.append(f"{where}: thiếu data-raw")
            elif not (topic / b["raw"]).exists():
                problems.append(f"{where}: data-raw không tồn tại: {b['raw']}")
            out.append(b)
    return out, problems


# ---------------------------------------------------------------- related topics
def related_for(topics, roadmap, insights, problems):
    names = {r["slug"]: r["name"] for r in roadmap}
    names.update({t["slug"]: t["title"] for t in topics})
    existing = {t["slug"] for t in topics}
    tags = {}
    for i in insights:
        tags.setdefault(i["topic"], set()).update(i["tags"])
    by_slug = {r["slug"]: r for r in roadmap}
    result = {}
    for t in topics:
        s = t["slug"]
        rel = {}

        def add(other, reason):
            if other != s:
                rel.setdefault(other, []).append(reason)

        for p in by_slug.get(s, {}).get("prereq", []):
            add(p, "tiền đề")
        for r in roadmap:
            if s in r["prereq"]:
                add(r["slug"], "dựa trên topic này")
        for other, otags in tags.items():
            shared = sorted(tags.get(s, set()) & otags)
            if shared and other != s:
                add(other, "cùng tag " + ", ".join(f"#{x}" for x in shared[:4]))
        for other, oprobs in problems.items():
            shared = sorted(problems.get(s, set()) & oprobs)
            if shared and other != s:
                add(other, "cùng vấn đề " + ", ".join(shared[:3]))
        order = {"tiền đề": 0, "dựa trên topic này": 1}
        result[s] = sorted(
            ({"slug": o, "name": names.get(o, o), "exists": o in existing, "reasons": rs} for o, rs in rel.items()),
            key=lambda x: (min(order.get(r, 2) for r in x["reasons"]), -len(x["reasons"]), x["slug"]))
    return result


def render_related(items):
    if not items:
        return '\n    <p class="empty-note">Chưa có topic liên quan.</p>\n    '
    lis = []
    for it in items:
        href = f"../{it['slug']}/README.html" if it["exists"] else f"../../hub/roadmap.html#{it['slug']}"
        missing = "" if it["exists"] else ' <span class="rel-missing">chưa tạo</span>'
        reasons = "".join(f'<span class="rel-reason">{e(r)}</span>' for r in it["reasons"])
        lis.append(f'      <li data-related="{e(it["slug"])}"><a href="{e(href)}">{e(it["name"])}</a>{missing} {reasons}</li>')
    return '\n    <ul class="related-list">\n' + "\n".join(lis) + "\n    </ul>\n    "


def write_related(topics, related):
    changed = 0
    for t in topics:
        path = ROOT / "topics" / t["slug"] / "README.html"
        text = path.read_text(encoding="utf-8")
        i, j = text.find(MARK_START), text.find(MARK_END)
        if i < 0 or j < i:
            print(f"[related] bỏ qua {path.relative_to(ROOT)}: không có marker related:start/end")
            continue
        new = text[:i + len(MARK_START)] + render_related(related.get(t["slug"], [])) + text[j:]
        if new != text:
            path.write_text(new, encoding="utf-8", newline="\n")
            changed += 1
    return changed


# ---------------------------------------------------------------- pages
def page(title, eyebrow, header_extra, body, scripts=("lab-dashboard.js",)):
    js = "".join(f'\n<script src="shared/docs/{s}" defer></script>' for s in scripts)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<link rel="stylesheet" href="shared/docs/lab.css">
<script src="shared/docs/lab.js" defer></script>{js}
</head>
<!-- GENERATED by scripts/build_dashboard.py — do not edit by hand. -->
<body data-page="hub">
<div class="layout">
  <nav class="toc" aria-label="Mục lục">
    <div class="toc-title">{e(title)}</div>
    <ol></ol>
    <button class="theme-toggle" type="button">Theme</button>
  </nav>
  <main>
  <article class="doc">
  <header class="doc-header">
    <div class="eyebrow">backend-lab · {e(eyebrow)}</div>
    <h1>{e(title)}</h1>
    {header_extra}
    <div class="meta"><span>Sinh lúc {generated}</span><span>Nguồn: topics/*/README.html, ROADMAP.html, topics/*/05-results.html</span></div>
  </header>
{body}
  </article>
  </main>
</div>
</body>
</html>
"""


def stats(pairs):
    cells = "".join(f"<div><strong>{e(v)}</strong><span>{e(k)}</span></div>" for k, v in pairs)
    return f'<div class="dash-stats">{cells}</div>'


def phase_chips(phases):
    out = []
    for i, name in PHASES.items():
        st = phases.get(i, "todo")
        out.append(f'<span class="ph ph-{e(st)}" title="{i} · {name}: {STATUS_LABEL.get(st, st)}">{i}</span>')
    return f'<span class="ph-chips">{"".join(out)}</span>'


def effective_status(slug, roadmap_status, topic_by_slug):
    t = topic_by_slug.get(slug)
    return t["overall"] if t else roadmap_status


def render_lab(topics, roadmap, tracks, insights, dives, benches):
    by_slug = {t["slug"]: t for t in topics}
    eff = {r["slug"]: effective_status(r["slug"], r["status"], by_slug) for r in roadmap}
    phases_done = sum(1 for t in topics for s in t["phases"].values() if s == "done")
    rm_done = sum(1 for s in eff.values() if s == "done")
    header = stats([
        ("topic", len(topics)), ("phase xong", phases_done), ("insight", len(insights)),
        ("chuyên đề", len(dives)), ("số liệu tham chiếu", len({b["slug"] for b in benches})),
        ("lộ trình xong", f"{rm_done}/{len(roadmap)}" if roadmap else "—"),
    ])
    sections = []

    # Roadmap progress per track
    if roadmap:
        rows = []
        order = list(tracks) + sorted({r["track"] for r in roadmap} - set(tracks))
        for tr in order:
            items = [r for r in roadmap if r["track"] == tr]
            if not items:
                continue
            done = sum(1 for r in items if eff[r["slug"]] == "done")
            prog = sum(1 for r in items if eff[r["slug"]] == "in-progress")
            pct = round(100 * done / len(items))
            doing = f" · {prog} đang làm" if prog else ""
            rows.append(
                f'<tr><td><a href="ROADMAP.html">{e(tracks.get(tr, tr))}</a></td>'
                f'<td><div class="progress" role="img" aria-label="{pct}%"><span style="--w:{pct}%"></span></div></td>'
                f'<td>{done}/{len(items)} xong{doing}</td></tr>')
        sections.append(
            '<section><h2 id="progress">Tiến độ theo lộ trình</h2>'
            '<div class="table-wrap"><table class="track-progress"><thead><tr><th>Track</th><th>Tiến độ</th><th>Topic</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div></section>')

    # Topics
    if topics:
        rows = []
        for t in topics:
            mode = t["mode"] + (f" · {t['type']}" if t["type"] != "standard" else "")
            appr = f'<a href="topics/{e(t["slug"])}/README.html#approvals" class="appr-count">{len(t["approvals"])}</a>' if t["approvals"] else "0"
            base = f'topics/{e(t["slug"])}/'
            qs = (f'<span class="q-readme" title="ul.questions li[data-status=open] trong README">{t["questions"]} câu hỏi mở (README)</span>'
                  f'<br><a class="q-qa" href="{base}questions.html">{t["qa_pending"]} hỏi đáp cần xem lại</a>'
                  f'<br><a class="q-ask" href="{base}suggested-questions.html">{t["ask_pending"]} câu hỏi gợi ý chưa hỏi</a>')
            rows.append(
                f'<tr data-topic="{e(t["slug"])}"><td><a href="topics/{e(t["slug"])}/README.html"><strong>{e(t["title"])}</strong></a>'
                f'<br><code>{e(t["slug"])}</code></td><td><span class="mode-chip mode-{e(t["mode"])}">{e(mode)}</span></td>'
                f'<td>{e(t["current_phase"])}<br>{phase_chips(t["phases"])}</td><td>{appr}</td><td>{qs}</td><td>{e(t["updated"])}</td></tr>')
        sections.append(
            '<section><h2 id="topics">Topic</h2><div class="table-wrap"><table class="lab-topics"><thead><tr>'
            '<th>Topic</th><th>Chế độ</th><th>Phase</th><th>Chờ duyệt</th><th>Câu hỏi</th><th>Cập nhật</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div></section>')
    else:
        sections.append('<section><h2 id="topics">Topic</h2><p class="empty-note">Chưa có topic. Chạy '
                        '<code>/research &lt;topic&gt;</code>, hoặc chọn một topic ở mục "Sẵn sàng học tiếp".</p></section>')

    # Approvals
    appr = [(t, a) for t in topics for a in t["approvals"]]
    if appr:
        lis = []
        for t, a in appr:
            phase = f" · phase {e(a['phase'])}" if a["phase"] else ""
            lis.append(f'<li><a href="topics/{e(t["slug"])}/README.html#approvals">{e(t["title"])}</a>{phase}: {e(a["text"])}</li>')
        lis = "".join(lis)
        body = f'<ul class="lab-approvals">{lis}</ul>'
    else:
        body = '<p class="empty-note">Không có quyết định nào đang chờ bạn duyệt.</p>'
    sections.append(f'<section><h2 id="approvals">Đang chờ bạn duyệt</h2>{body}</section>')

    # Ready next: prerequisites done, topic not started yet
    ready = [r for r in roadmap if eff[r["slug"]] == "planned" and r["slug"] not in by_slug
             and all(eff.get(p) == "done" for p in r["prereq"])]
    ready.sort(key=lambda r: (r["priority"], r["slug"]))
    if ready:
        lis = []
        for r in ready[:10]:
            why = ("không có tiền đề" if not r["prereq"]
                   else "tiền đề đã xong: " + ", ".join(r["prereq"]))
            cmd = f"/research {r['slug']}" + (" lite" if r["mode"] == "lite" else "")
            lis.append(f'<li><a href="ROADMAP.html#{e(r["slug"])}"><strong>{e(r["name"])}</strong></a> '
                       f'<span class="prio prio-{r["priority"]}">Ưu tiên {r["priority"]}</span> — {e(why)} · <code>{e(cmd)}</code></li>')
        body = f'<ul class="lab-ready">{"".join(lis)}</ul>'
    else:
        body = '<p class="empty-note">Chưa có topic nào đủ tiền đề (hoặc chưa có ROADMAP.html).</p>'
    sections.append(f'<section><h2 id="ready">Sẵn sàng học tiếp</h2>{body}</section>')

    # Recent decisions
    decisions = sorted(((d, t) for t in topics for d in t["decisions"]), key=lambda x: x[0]["date"], reverse=True)[:12]
    if decisions:
        rows = "".join(
            f'<tr><td>{e(d["date"])}</td><td><a href="topics/{e(t["slug"])}/README.html#decisions">{e(t["title"])}</a></td>'
            f'<td>{e(d["phase"])}</td><td>{e(d["decision"])}</td><td>{e(d["reason"])}</td></tr>' for d, t in decisions)
        body = ('<div class="table-wrap"><table class="lab-decisions"><thead><tr><th>Ngày</th><th>Topic</th><th>Phase</th>'
                f'<th>Quyết định</th><th>Lý do</th></tr></thead><tbody>{rows}</tbody></table></div>')
    else:
        body = '<p class="empty-note">Chưa có quyết định nào.</p>'
    sections.append(f'<section><h2 id="decisions">Quyết định gần đây</h2>{body}</section>')

    return page("Tổng quan lab", "Tổng quan", header, "\n".join(sections), scripts=())


def render_benchmarks(benches, topics):
    groups = {}
    for b in benches:
        groups.setdefault(b["slug"], []).append(b)
    multi = sum(1 for g in groups.values() if len({b["topic"] for b in g}) > 1)
    header = stats([("đại lượng", len(groups)), ("lần đo", len(benches)),
                    ("topic có số liệu", len({b["topic"] for b in benches})), ("đại lượng đo ở nhiều topic", multi)])
    if not benches:
        body = ('<section><h2 id="empty">Chưa có số liệu tham chiếu</h2><p class="empty-note">Số liệu tham chiếu là các hàng '
                '<code>[data-bench]</code> ở §8 của <code>05-results.html</code> mỗi topic. Sau phase 5, chạy '
                '<code>python3 scripts/build_dashboard.py</code> để cập nhật trang này.</p></section>')
        return page("Số liệu tham chiếu", "Số liệu", header, body)

    topic_opts = "".join(f'<option value="{e(s)}">{e(t)}</option>'
                         for s, t in sorted({(b["topic"], b["topic_title"]) for b in benches}))
    filters = ('<div class="bench-filters"><input type="search" class="bench-search" placeholder="Tìm đại lượng, điều kiện, topic…" '
               f'aria-label="Tìm"><select class="bench-topic" aria-label="Topic"><option value="">Mọi topic</option>{topic_opts}</select>'
               '<label><input type="checkbox" class="bench-multi"> Chỉ đại lượng đo ở nhiều topic</label>'
               '<span class="bench-count"></span></div>')
    order = sorted(groups, key=lambda s: (-len({b["topic"] for b in groups[s]}), s))
    secs = []
    for slug in order:
        g = groups[slug]
        n_topics = len({b["topic"] for b in g})
        # Bars only compare entries that share a unit.
        maxv = {}
        for b in g:
            if b["value"] is not None:
                maxv[b["unit"]] = max(maxv.get(b["unit"], 0), abs(b["value"]))
        rows = []
        for b in sorted(g, key=lambda x: (x["topic"], x["metric"])):
            ci = (f' <span class="ci">[{fmt(b["ci_low"])}, {fmt(b["ci_high"])}]</span>'
                  if b["ci_low"] is not None and b["ci_high"] is not None else "")
            w = round(100 * abs(b["value"]) / maxv[b["unit"]]) if b["value"] is not None and maxv.get(b["unit"]) else 0
            base = f"topics/{b['topic']}/"
            raw = f'<a href="{e(base + b["raw"])}">{e(Path(b["raw"]).name)}</a>' if b["raw"] else "—"
            draft = ' <span class="rel-missing">nháp</span>' if b["draft"] else ""
            search = " ".join([slug, b["topic"], b["topic_title"], b["metric"], b["conditions"], b["label"]]).lower()
            env_sum = " · " + e(b["env_summary"]) if b["env_summary"] else ""
            env_cell = f'<td class="bench-env"><a href="{e(base + b["env"])}">env</a>{env_sum}</td>'
            rows.append(
                f'<tr data-topic="{e(b["topic"])}" data-search="{e(search)}">'
                f'<td><a href="{e(base)}05-results.html#benchmarks">{e(b["topic_title"])}</a>{draft}</td>'
                f'<td class="bench-val"><strong>{e(fmt(b["value"]))}</strong> {e(b["unit"])}{ci}'
                f'<div class="bench-bar"><span style="--w:{w}%"></span></div></td>'
                f'<td>{e(b["metric"])}</td><td>{e(b["conditions"])}</td>'
                f'{env_cell}'
                f'<td>{raw}</td></tr>')
        badge = ' <span class="multi-badge">nhiều topic</span>' if n_topics > 1 else ""
        secs.append(
            f'<section class="bench-group" data-slug="{e(slug)}" data-multi="{1 if n_topics > 1 else 0}">'
            f'<h3 id="b-{e(slug)}"><code>{e(slug)}</code>{badge}</h3>'
            '<div class="table-wrap"><table class="bench-table"><thead><tr><th>Topic</th><th>Giá trị [95% CI]</th><th>Metric</th>'
            f'<th>Điều kiện</th><th>Môi trường</th><th>Raw</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>')
    body = (f'<section><h2 id="filters">Tìm &amp; lọc</h2>{filters}'
            '<p class="note">Chỉ số [đo được], mỗi giá trị link tới raw. Thanh ngang so sánh độ lớn giữa các lần đo cùng đơn vị trong một đại lượng; '
            'so sánh giữa topic chỉ có nghĩa khi điều kiện và môi trường tương đương — đọc cột Điều kiện và Môi trường trước khi so.</p></section>'
            f'<section><h2 id="quantities">Theo đại lượng</h2>{"".join(secs)}</section>')
    return page("Số liệu tham chiếu", "Số liệu", header, body)


# ---------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="validate [data-bench] rows; exit 1 on problems (no files written)")
    ap.add_argument("--no-related", action="store_true", help="do not rewrite the related-topics block of topic READMEs")
    ap.add_argument("--lab-out", default=str(hub_path("lab")))
    ap.add_argument("--bench-out", default=str(hub_path("benchmarks")))
    ap.add_argument("--roadmap", help="roadmap page to read (default: ROADMAP.html; for testing)")
    ap.add_argument("--include-underscore", action="store_true", help="also read topics/_* test fixtures")
    args = ap.parse_args()
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    global INCLUDE_UNDERSCORE
    INCLUDE_UNDERSCORE = args.include_underscore
    topics = read_topics()
    benches, problems = read_benchmarks(topics)
    if args.check:
        for p in problems:
            print(f"[bench] {p}")
        print(f"checked {len(benches)} benchmark row(s) in {len({b['topic'] for b in benches})} topic(s): {len(problems)} problem(s)")
        sys.exit(1 if problems else 0)

    roadmap, tracks = read_roadmap(args.roadmap)
    idx = bi.collect()
    keep = (lambda t: True) if INCLUDE_UNDERSCORE else (lambda t: not t.startswith("_"))
    insights = [i for i in idx["insights"] if keep(i["topic"])]
    dives = [d for d in idx["deep_dives"] if keep(d["topic"])]

    Path(args.lab_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.bench_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.lab_out).write_text(hubify(render_lab(topics, roadmap, tracks, insights, dives, benches)), encoding="utf-8", newline="\n")
    Path(args.bench_out).write_text(hubify(render_benchmarks(benches, topics)), encoding="utf-8", newline="\n")
    changed = 0
    if not args.no_related:
        changed = write_related(topics, related_for(topics, roadmap, insights, read_problems()))
    print(f"wrote hub/lab.html ({len(topics)} topic(s), {len(roadmap)} roadmap row(s)), "
          f"hub/benchmarks.html ({len(benches)} measurement(s)); related sections updated: {changed}")
    if problems:
        print(f"warning: {len(problems)} benchmark problem(s); run with --check for details")


if __name__ == "__main__":
    main()
