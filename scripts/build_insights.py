#!/usr/bin/env python3
"""Build the cross-topic insight hub (INSIGHTS.html) and lint insight markup.

Scans topics/*/NN-*.html for `div.callout.insight` and `div.deep-dive` blocks and produces:
  - INSIGHTS.html at the repo root: search + filters, insights grouped by tag (where principles
    shared across topics show up), by topic, and a list of deep dives (CĐ), each linking back to
    topics/<slug>/<page>#<anchor>;
  - optionally a JSON index (--json);
  - optionally a lint report (--check) used by /research before gates.

Insights inside author guidance (`div.guide`, e.g. the worked example in templates) and insights
whose claim is still empty are ignored for the hub.

Usage:
    python3 scripts/build_insights.py                    # regenerate INSIGHTS.html
    python3 scripts/build_insights.py --json index.json  # also dump the index
    python3 scripts/build_insights.py --check            # lint finished pages; exit 1 on problems
    python3 scripts/build_insights.py --check --topic transactional-outbox --include-draft

Check rules (pages whose <body> has class "draft" are skipped unless --include-draft):
  - insight without id, duplicate id within a page;
  - empty claim (placeholder left behind);
  - missing or empty why-steps field: Cơ chế, Điều kiện, Định lượng, Khi nào không đúng, Liên hệ;
  - empty evidence;
  - data-tags missing, not 2–5 tags, or a tag that is not lowercase kebab-case;
  - deep dive without title or without valid data-tags.

Standard library only.
"""

import argparse
import html
import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
WHY_FIELDS = ["Cơ chế", "Điều kiện", "Định lượng", "Khi nào không đúng", "Liên hệ"]
TAG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
KINDS = {"measured": "đo được", "doc": "theo tài liệu", "inferred": "suy luận"}


# ---------------------------------------------------------------- minimal DOM
class Node:
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.children, self.parent = tag, dict(attrs), [], parent

    @property
    def classes(self):
        return set((self.attrs.get("class") or "").split())

    def text(self):
        parts = []
        for c in self.children:
            parts.append(c if isinstance(c, str) else c.text())
        return " ".join(" ".join(parts).split())

    def iter(self):
        for c in self.children:
            if isinstance(c, Node):
                yield c
                yield from c.iter()

    def find(self, tag=None, cls=None):
        for n in self.iter():
            if (tag is None or n.tag == tag) and (cls is None or cls in n.classes):
                return n
        return None

    def find_all(self, tag=None, cls=None):
        return [n for n in self.iter() if (tag is None or n.tag == tag) and (cls is None or cls in n.classes)]

    def has_ancestor_class(self, cls):
        p = self.parent
        while p is not None:
            if cls in p.classes:
                return True
            p = p.parent
        return False


class TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", {}, None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.cur)
        self.cur.children.append(node)
        if tag not in VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        if data.strip():
            self.cur.children.append(data)


def parse(path):
    b = TreeBuilder()
    b.feed(path.read_text(encoding="utf-8"))
    return b.root


# ---------------------------------------------------------------- extraction
def split_tags(raw):
    """Raw tags as written (validated as-is by tag_problems); callers lowercase for indexing."""
    return [t.strip() for t in (raw or "").split(",") if t.strip()]


def why_fields(insight):
    """Map dt label -> dd text for the why-steps definition list."""
    dl = insight.find("dl", "why-steps")
    out = {}
    if dl is None:
        return out
    label = None
    for c in dl.children:
        if not isinstance(c, Node):
            continue
        if c.tag == "dt":
            label = c.text()
        elif c.tag == "dd" and label is not None:
            out[label] = c.text()
            label = None
    return out


def evidence_kinds(node):
    kinds = []
    for n in node.iter():
        if "tag" in n.classes:
            for k in KINDS:
                if k in n.classes and k not in kinds:
                    kinds.append(k)
    return kinds


def topic_title(topic_dir):
    readme = topic_dir / "README.html"
    if readme.exists():
        h1 = parse(readme).find("h1")
        if h1 is not None and h1.text():
            return h1.text()
    return topic_dir.name


def scan_page(topic, title, page):
    """Return (insights, deep_dives, problems_for_check, is_draft)."""
    root = parse(page)
    body = root.find("body")
    is_draft = body is not None and "draft" in body.classes
    rel = f"topics/{topic}/{page.name}"
    phase = int(page.name[:2])
    insights, dives, problems = [], [], []
    seen_ids = {}
    last_heading = {"text": "", "id": ""}
    last_dd_title = None

    for n in root.iter():
        if n.tag in ("h2", "h3") and not n.has_ancestor_class("guide"):
            last_heading = {"text": n.text(), "id": n.attrs.get("id", "")}
        if "deep-dive-title" in n.classes:
            code = n.find("span", "dd-code")
            code_text = code.text() if code else ""
            full = n.text()
            last_dd_title = {"code": code_text, "title": full[len(code_text):].strip() if full.startswith(code_text) else full,
                             "id": n.attrs.get("id", "")}
        if n.tag != "div" or n.has_ancestor_class("guide"):
            continue

        if {"callout", "insight"} <= n.classes:
            iid = n.attrs.get("id", "")
            claim_node = n.find("p", "claim")
            claim = claim_node.text() if claim_node else ""
            fields = why_fields(n)
            ev = n.find("div", "evidence")
            evidence = ev.text() if ev else ""
            evidence = re.sub(r"^Căn cứ:\s*", "", evidence)
            raw_tags = split_tags(n.attrs.get("data-tags"))
            tags = [t.lower() for t in raw_tags]
            where = f"{rel}#{iid or last_heading['id']} ({last_heading['text'] or 'đầu trang'})"
            if iid:
                if iid in seen_ids:
                    problems.append(f"{where}: id trùng '{iid}'")
                seen_ids[iid] = True
            else:
                problems.append(f"{where}: insight thiếu id")
            if not claim:
                problems.append(f"{where}: claim rỗng (placeholder chưa thay)")
            else:
                missing = [f for f in WHY_FIELDS if not fields.get(f)]
                if missing:
                    problems.append(f"{where}: why-steps thiếu/rỗng: {', '.join(missing)}")
                if not evidence:
                    problems.append(f"{where}: thiếu Căn cứ")
                problems.extend(f"{where}: {p}" for p in tag_problems(raw_tags))
                why_node = n.find("div", "why")
                insights.append({
                    "topic": topic, "topic_title": title, "page": page.name, "phase": phase,
                    "section": last_heading["text"], "section_id": last_heading["id"],
                    "id": iid, "anchor": iid or last_heading["id"], "href": f"{rel}#{iid or last_heading['id']}",
                    "claim": claim, "why": fields, "why_text": why_node.text() if why_node else "",
                    "evidence": evidence, "kinds": evidence_kinds(n), "tags": tags,
                })

        elif "deep-dive" in n.classes:
            meta = {}
            dl = n.find("dl", "dd-meta")
            if dl is not None:
                label = None
                for c in dl.children:
                    if isinstance(c, Node) and c.tag == "dt":
                        label = c.text()
                    elif isinstance(c, Node) and c.tag == "dd" and label:
                        meta[label] = c.text()
                        label = None
            info = last_dd_title or {"code": "", "title": "", "id": ""}
            raw_tags = split_tags(n.attrs.get("data-tags"))
            tags = [t.lower() for t in raw_tags]
            where = f"{rel}#{info['id']} ({info['code'] or 'chuyên đề'})"
            if not info["title"]:
                problems.append(f"{where}: chuyên đề chưa có tiêu đề (placeholder chưa thay)")
                continue
            problems.extend(f"{where}: {p}" for p in tag_problems(raw_tags))
            dives.append({
                "topic": topic, "topic_title": title, "page": page.name, "code": info["code"],
                "title": info["title"], "href": f"{rel}#{info['id']}", "scope": meta.get("Thuộc", ""),
                "why_specific": meta.get("Vì sao đặc thù", ""), "impact": meta.get("Ảnh hưởng tới", ""), "tags": tags,
            })
    return insights, dives, problems, is_draft


def tag_problems(tags):
    out = []
    if not tags:
        out.append("thiếu data-tags")
    elif not 2 <= len(tags) <= 5:
        out.append(f"data-tags cần 2–5 tag, đang có {len(tags)}")
    bad = [t for t in tags if not TAG_RE.match(t)]
    if bad:
        out.append(f"tag không phải kebab-case chữ thường: {', '.join(bad)}")
    return out


def collect(only_topic=None):
    topics_dir = ROOT / "topics"
    data = {"insights": [], "deep_dives": [], "topics": [], "problems": {}}
    if not topics_dir.exists():
        return data
    for tdir in sorted(p for p in topics_dir.iterdir() if p.is_dir()):
        if only_topic and tdir.name != only_topic:
            continue
        pages = sorted(tdir.glob("[0-9][0-9]-*.html"))
        if not pages:
            continue
        title = topic_title(tdir)
        data["topics"].append({"slug": tdir.name, "title": title})
        for page in pages:
            ins, dives, probs, is_draft = scan_page(tdir.name, title, page)
            data["insights"].extend(ins)
            data["deep_dives"].extend(dives)
            data["problems"][f"topics/{tdir.name}/{page.name}"] = {"draft": is_draft, "problems": probs}
    return data


# ---------------------------------------------------------------- rendering
def e(s):
    return html.escape(s or "", quote=True)


def kind_badges(kinds):
    return "".join(f'<span class="tag {k}">{KINDS[k]}</span>' for k in kinds)


def tag_chips(tags):
    return "".join(f'<span class="ins-tag">#{e(t)}</span>' for t in tags)


def card(ins, full=True):
    search = " ".join([ins["claim"], ins["why_text"], ins["evidence"], ins["topic_title"], ins["section"], " ".join(ins["tags"])]).lower()
    attrs = (f'data-topic="{e(ins["topic"])}" data-tags="{e(",".join(ins["tags"]))}" '
             f'data-kinds="{e(" ".join(ins["kinds"]))}" data-search="{e(search)}"')
    src = (f'<a class="ins-src" href="{e(ins["href"])}">{e(ins["topic_title"])} · {e(ins["page"])}'
           f'{" · " + e(ins["section"]) if ins["section"] else ""}</a>')
    if not full:
        return f'<li class="ins-item" {attrs}><span class="ins-claim">{e(ins["claim"])}</span> {src}</li>'
    rows = "".join(f"<dt>{e(k)}</dt><dd>{e(ins['why'].get(k, ''))}</dd>" for k in WHY_FIELDS if ins["why"].get(k))
    why = f'<details class="ins-why"><summary>Vì sao</summary><dl class="why-steps">{rows}</dl></details>' if rows else ""
    ev = f'<div class="ins-evidence"><strong>Căn cứ:</strong> {e(ins["evidence"])}</div>' if ins["evidence"] else ""
    return (f'<article class="ins-card" {attrs}>'
            f'<p class="ins-claim">{e(ins["claim"])}</p>{why}{ev}'
            f'<div class="ins-meta">{kind_badges(ins["kinds"])}{tag_chips(ins["tags"])}{src}</div></article>')


def render(data):
    ins, dives, topics = data["insights"], data["deep_dives"], data["topics"]
    all_tags = {}
    for i in ins:
        for t in i["tags"]:
            all_tags.setdefault(t, []).append(i)
    for d in dives:
        for t in d["tags"]:
            all_tags.setdefault(t, [])
    # Tags shared by more topics first: that is where cross-topic principles are.
    tag_order = sorted(all_tags, key=lambda t: (-len({i["topic"] for i in all_tags[t]}), -len(all_tags[t]), t))
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if not topics or (not ins and not dives):
        body = ('<section><h2 id="empty">Chưa có insight</h2>'
                '<p class="empty-note">Chưa có topic nào có insight đã điền. Chạy <code>/research &lt;topic&gt;</code>; '
                'sau mỗi phase, <code>python3 scripts/build_insights.py</code> sẽ cập nhật trang này.</p></section>')
        filters = ""
    else:
        topic_opts = "".join(f'<option value="{e(t["slug"])}">{e(t["title"])}</option>' for t in topics)
        kind_opts = "".join(f'<option value="{k}">{v}</option>' for k, v in KINDS.items())
        chips = "".join(f'<button type="button" class="tag-chip" data-tag="{e(t)}">#{e(t)} '
                        f'<span class="chip-count">{len(all_tags[t])}</span></button>' for t in tag_order)
        filters = (f'<section class="ins-filters" aria-label="Bộ lọc">'
                   f'<input type="search" id="ins-q" placeholder="Tìm trong khẳng định, vì sao, căn cứ…" autocomplete="off">'
                   f'<select id="ins-topic"><option value="">Mọi topic</option>{topic_opts}</select>'
                   f'<select id="ins-kind"><option value="">Mọi loại căn cứ</option>{kind_opts}</select>'
                   f'<div class="tag-chips">{chips}</div>'
                   f'<p class="ins-count"><span id="ins-visible">{len(ins)}</span> / {len(ins)} insight đang hiển thị</p></section>')

        by_tag = []
        for t in tag_order:
            items = all_tags[t]
            if not items:
                continue
            ntopics = len({i["topic"] for i in items})
            badge = '<span class="cross-badge">liên topic</span>' if ntopics > 1 else ""
            by_tag.append(f'<div class="tag-group" data-tag="{e(t)}"><h3 id="tag-{e(t)}">#{e(t)} {badge}</h3>'
                          f'<p class="tag-sub">{len(items)} insight · {ntopics} topic</p>'
                          f'<ul class="ins-list">{"".join(card(i, full=False) for i in items)}</ul></div>')
        untagged = [i for i in ins if not i["tags"]]
        if untagged:
            by_tag.append('<div class="tag-group" data-tag=""><h3 id="tag-none">Chưa gắn tag</h3>'
                          f'<ul class="ins-list">{"".join(card(i, full=False) for i in untagged)}</ul></div>')

        by_topic = []
        for t in topics:
            items = [i for i in ins if i["topic"] == t["slug"]]
            if not items:
                continue
            by_topic.append(f'<div class="topic-group" data-topic="{e(t["slug"])}"><h3 id="topic-{e(t["slug"])}">{e(t["title"])}</h3>'
                            f'<p class="tag-sub"><a href="topics/{e(t["slug"])}/README.html">README</a> · {len(items)} insight</p>'
                            f'{"".join(card(i) for i in items)}</div>')

        if dives:
            rows = "".join(
                f'<tr data-topic="{e(d["topic"])}" data-tags="{e(",".join(d["tags"]))}" '
                f'data-search="{e(" ".join([d["title"], d["why_specific"], d["scope"], d["topic_title"], " ".join(d["tags"])]).lower())}">'
                f'<td><a href="{e(d["href"])}"><code>{e(d["code"])}</code></a></td><td>{e(d["title"])}</td>'
                f'<td>{e(d["topic_title"])}</td><td>{e(d["scope"])}</td><td>{e(d["why_specific"])}</td>'
                f'<td>{tag_chips(d["tags"])}</td></tr>' for d in dives)
            dive_html = ('<div class="table-wrap"><table class="dive-table"><thead><tr><th>Mã</th><th>Chuyên đề</th>'
                         '<th>Topic</th><th>Thuộc</th><th>Vì sao đặc thù</th><th>Tag</th></tr></thead>'
                         f'<tbody>{rows}</tbody></table></div>')
        else:
            dive_html = '<p class="empty-note">Chưa có chuyên đề đặc thù nào.</p>'

        body = (f'<section><h2 id="by-tag">Theo tag</h2><p class="note">Tag xuất hiện ở nhiều topic đứng trước: '
                f'đó là những nguyên lý lặp lại giữa các công nghệ.</p>{"".join(by_tag)}</section>'
                f'<section><h2 id="by-topic">Theo topic</h2>{"".join(by_topic)}</section>'
                f'<section><h2 id="deep-dives">Chuyên đề đặc thù</h2>{dive_html}</section>')

    cross = sum(1 for t in all_tags if len({i["topic"] for i in all_tags[t]}) > 1)
    return f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kho insight</title>
<link rel="stylesheet" href="shared/docs/lab.css">
<script src="shared/docs/lab.js" defer></script>
<script src="shared/docs/lab-insights.js" defer></script>
</head>
<!-- GENERATED by scripts/build_insights.py — do not edit by hand. -->
<body data-page="hub">
<div class="layout">
  <nav class="toc" aria-label="Mục lục">
    <div class="toc-title">Kho insight</div>
    <ol></ol>
    <button class="theme-toggle" type="button">Theme</button>
  </nav>
  <main>
  <article class="doc">
  <header class="doc-header">
    <div class="eyebrow">backend-lab · Kho insight</div>
    <h1>Kho insight</h1>
    <div class="ins-stats">
      <div><strong>{len(topics)}</strong><span>topic</span></div>
      <div><strong>{len(ins)}</strong><span>insight</span></div>
      <div><strong>{len(dives)}</strong><span>chuyên đề</span></div>
      <div><strong>{len(all_tags)}</strong><span>tag</span></div>
      <div><strong>{cross}</strong><span>tag liên topic</span></div>
    </div>
    <div class="meta"><span>Sinh lúc {generated}</span><span>Nguồn: topics/*/NN-*.html</span></div>
  </header>
  {filters}
  {body}
  </article>
  </main>
</div>
</body>
</html>
"""


# ---------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=str(ROOT / "INSIGHTS.html"), help="output page (default: INSIGHTS.html at repo root)")
    ap.add_argument("--json", metavar="OUT", help="also write the index as JSON")
    ap.add_argument("--check", action="store_true", help="lint insight markup instead of (only) building; exit 1 on problems")
    ap.add_argument("--topic", help="limit --check (and the index) to one topic slug")
    ap.add_argument("--include-draft", action="store_true", help="--check also pages whose <body> still has class draft")
    ap.add_argument("--no-page", action="store_true", help="do not write INSIGHTS.html")
    args = ap.parse_args()
    # Vietnamese messages must not crash on consoles with a legacy code page (Windows cp1252).
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    data = collect(args.topic)

    if args.check:
        total = 0
        for page, info in data["problems"].items():
            if info["draft"] and not args.include_draft:
                continue
            for p in info["problems"]:
                print(f"[insight] {p}")
                total += 1
        checked = sum(1 for i in data["problems"].values() if args.include_draft or not i["draft"])
        print(f"checked {checked} page(s), {len(data['insights'])} insight(s), {len(data['deep_dives'])} deep dive(s): "
              f"{total} problem(s)")
        if total:
            sys.exit(1)
        return

    if args.json:
        out = {k: data[k] for k in ("topics", "insights", "deep_dives")}
        Path(args.json).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    if not args.no_page:
        Path(args.out).write_text(render(data), encoding="utf-8", newline="\n")
        print(f"wrote {Path(args.out).relative_to(ROOT) if Path(args.out).is_relative_to(ROOT) else args.out}: "
              f"{len(data['topics'])} topic(s), {len(data['insights'])} insight(s), {len(data['deep_dives'])} deep dive(s)")


if __name__ == "__main__":
    main()
