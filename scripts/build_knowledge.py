#!/usr/bin/env python3
"""Build the problem index (PROBLEMS.html) and shared glossary (GLOSSARY.html); lint their markup.

Scans topics/*/NN-*.html and aggregates across topics:
  - PROBLEMS.html: one card per symptom slug (data-problem). Engineers start from a symptom
    ("mất event khi deploy", "p99 tăng khi tải cao"), not from a pattern name, so this page answers
    "gặp triệu chứng X thì nguyên nhân là gì, solution/topic nào giải, chọn cách nào, xử lý ra sao".
    Sources: 01 §4.1/§4.2 (symptom + impact), 01 §13 and §17 failure-mode tables and deep dives
    (cause / mechanism), 06 §6 decision guide (context -> choice -> why), 07 §3 runbook
    (diagnosis / fix), plus insights whose data-tags contain the slug.
  - GLOSSARY.html: §6 terms (dt[data-term]) merged across topics, A–Z, each linking back to
    every topic that defines it.

Markup contract (also documented in the header comments of templates 01, 06, 07):
  - <table data-index="problem-type|problem-impact|failure-mode|decision|runbook">; every row with
    content has data-problem="slug[,slug]" (kebab-case symptom slug).
  - symptom rows (problem-type, problem-impact, failure-mode) and .deep-dive blocks that carry
    data-problem also carry data-kind="correctness|performance|scalability|cost|operability";
    optional data-symptom="short text" (default: the Biểu hiện / Failure mode cell or deep-dive title).
  - decision rows carry data-choice="<implementation id>" (before / A / B ...).
  - glossary: <dt id="term-<slug>" data-term="<slug>"> followed by <dd>.
Content inside div.guide (template guidance) and empty placeholder rows are ignored.

Usage:
    python3 scripts/build_knowledge.py                    # regenerate PROBLEMS.html and GLOSSARY.html
    python3 scripts/build_knowledge.py --json index.json  # also dump the index
    python3 scripts/build_knowledge.py --check            # lint finished pages; exit 1 on problems
    python3 scripts/build_knowledge.py --check --topic transactional-outbox --include-draft

Check rules (pages whose <body> has class "draft" are skipped unless --include-draft):
  - indexed row with content but no data-problem; slug not lowercase kebab-case;
  - symptom row / deep dive with data-problem but missing or invalid data-kind;
  - decision row without data-choice;
  - row with data-problem inside a table without data-index;
  - glossary dt with text but no data-term, invalid term slug, or id != "term-<data-term>";
  - duplicate element ids within a page.

Standard library only; reuses the parser of build_insights.py.
"""

import argparse
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_insights as bi  # noqa: E402  (shared minimal DOM + insight extraction)
from _paths import hub_path, hubify  # noqa: E402

ROOT = bi.ROOT
SLUG_RE = bi.TAG_RE
KINDS = {
    "correctness": "Đúng đắn / độ tin cậy",
    "performance": "Hiệu năng",
    "scalability": "Khả năng mở rộng",
    "cost": "Chi phí / tài nguyên",
    "operability": "Vận hành",
}
INDEXES = {"problem-type", "problem-impact", "failure-mode", "decision", "runbook"}
SYMPTOM_INDEXES = {"problem-type", "problem-impact", "failure-mode"}
ROLE = {  # index -> section of the problem card
    "problem-type": "symptom", "problem-impact": "symptom", "failure-mode": "cause",
    "decision": "decision", "runbook": "runbook", "deep-dive": "cause",
}
REF_ONLY = re.compile(r"\[R\d+\]")
SYMPTOM_COL = {"problem-type": "Biểu hiện", "problem-impact": "Biểu hiện", "failure-mode": "Failure mode", "runbook": "Triệu chứng"}


def e(s):
    return html.escape(s or "", quote=True)


def split_slugs(raw):
    return [s.strip() for s in (raw or "").split(",") if s.strip()]


def cell_texts(tr):
    return [c.text() for c in tr.children if isinstance(c, bi.Node) and c.tag in ("td", "th")]


def headers(table):
    thead = table.find("thead")
    row = thead.find("tr") if thead else None
    return cell_texts(row) if row else []


def implementations(topic_dir):
    """ID -> description from the README Implementations table (for decision 'choice' labels)."""
    out = {}
    readme = topic_dir / "README.html"
    if not readme.exists():
        return out
    for tr in bi.parse(readme).find_all("tr"):
        impl = tr.attrs.get("data-impl")
        if impl:
            cells = cell_texts(tr)
            out[impl] = cells[-1] if cells else ""
    return out


def nearest_anchor_map(root):
    """node id() -> (heading text, anchor id) of the nearest preceding heading with an id."""
    last = {"text": "", "id": ""}
    out = {}
    for n in root.iter():
        if n.tag in ("h2", "h3", "h4") and not n.has_ancestor_class("guide") and n.attrs.get("id"):
            last = {"text": n.text(), "id": n.attrs["id"]}
        out[id(n)] = dict(last)
    return out


def scan_page(topic, title, impls, page):
    root = bi.parse(page)
    body = root.find("body")
    is_draft = body is not None and "draft" in body.classes
    rel = f"topics/{topic}/{page.name}"
    anchors = nearest_anchor_map(root)
    entries, terms, problems = [], [], []

    # duplicate ids (whole page)
    seen = {}
    for n in root.iter():
        nid = n.attrs.get("id")
        if nid:
            seen[nid] = seen.get(nid, 0) + 1
    for nid, cnt in seen.items():
        if cnt > 1:
            problems.append(f"{rel}: id trùng '{nid}' ({cnt} lần)")

    def base(node, kind_of_entry, fields, symptom, slugs, kind):
        a = anchors.get(id(node), {"text": "", "id": ""})
        return {
            "topic": topic, "topic_title": title, "page": page.name, "phase": int(page.name[:2]),
            "role": ROLE[kind_of_entry], "source": kind_of_entry, "problems": slugs, "kind": kind,
            "symptom": symptom, "fields": fields, "section": a["text"],
            "href": f"{rel}#{a['id']}" if a["id"] else rel,
        }

    # ---- indexed tables
    for table in root.find_all("table"):
        if table.has_ancestor_class("guide"):
            continue
        idx = table.attrs.get("data-index")
        rows = [tr for tr in table.find_all("tr") if tr.parent is not None and tr.parent.tag == "tbody"]
        if not idx:
            for tr in rows:
                if tr.attrs.get("data-problem"):
                    problems.append(f"{rel}: hàng có data-problem nằm trong bảng thiếu data-index ({anchors[id(tr)]['text']})")
            continue
        if idx not in INDEXES:
            problems.append(f"{rel}: data-index không hợp lệ '{idx}'")
            continue
        hdr = headers(table)
        for tr in rows:
            cells = cell_texts(tr)
            raw = tr.attrs.get("data-problem", "")
            # A template placeholder row may still hold its ID ("FM1") or a bare reason link ("[R5]"): not content.
            has_content = any(REF_ONLY.sub("", v).strip() for h, v in zip(hdr, cells) if h != "ID")
            if not has_content and not raw.strip():
                continue  # untouched template placeholder
            where = f"{rel} [{idx}] ({anchors[id(tr)]['text']})"
            slugs = split_slugs(raw)
            kind = (tr.attrs.get("data-kind") or "").strip()
            if not slugs:
                problems.append(f"{where}: hàng có nội dung nhưng thiếu data-problem")
            bad = [s for s in slugs if not SLUG_RE.match(s)]
            if bad:
                problems.append(f"{where}: slug không phải kebab-case chữ thường: {', '.join(bad)}")
            if idx in SYMPTOM_INDEXES and kind not in KINDS:
                problems.append(f"{where}: data-kind thiếu hoặc không hợp lệ ('{kind}')")
            choice = (tr.attrs.get("data-choice") or "").strip()
            if idx == "decision" and not choice:
                problems.append(f"{where}: hàng decision thiếu data-choice")
            if not slugs:
                continue
            fields = [(h, v) for h, v in zip(hdr, cells) if v]
            col = SYMPTOM_COL.get(idx)
            symptom = tr.attrs.get("data-symptom") or next((v for h, v in zip(hdr, cells) if col and h.startswith(col) and v), "")
            entry = base(tr, idx, fields, symptom, [s.lower() for s in slugs], kind if kind in KINDS else "")
            if idx == "decision":
                entry["choice"] = choice
                entry["choice_label"] = impls.get(choice, "")
            entries.append(entry)

    # ---- deep dives
    last_title = None
    for n in root.iter():
        if "deep-dive-title" in n.classes:
            code = n.find("span", "dd-code")
            code_text = code.text() if code else ""
            full = n.text()
            last_title = {"code": code_text, "title": full[len(code_text):].strip() if full.startswith(code_text) else full,
                          "id": n.attrs.get("id", "")}
        if n.tag != "div" or "deep-dive" not in n.classes or n.has_ancestor_class("guide"):
            continue
        raw = n.attrs.get("data-problem", "")
        slugs = split_slugs(raw)
        if not slugs:
            continue
        where = f"{rel} [deep-dive {last_title['code'] if last_title else ''}]"
        bad = [s for s in slugs if not SLUG_RE.match(s)]
        if bad:
            problems.append(f"{where}: slug không phải kebab-case chữ thường: {', '.join(bad)}")
        kind = (n.attrs.get("data-kind") or "").strip()
        if kind not in KINDS:
            problems.append(f"{where}: data-kind thiếu hoặc không hợp lệ ('{kind}')")
        meta = n.find("dl", "dd-meta")
        fields = []
        if meta:
            label = None
            for c in meta.children:
                if isinstance(c, bi.Node) and c.tag == "dt":
                    label = c.text()
                elif isinstance(c, bi.Node) and c.tag == "dd" and label:
                    if c.text():
                        fields.append((label, c.text()))
                    label = None
        # "Hiện tượng" paragraph = the h4 followed by a p
        kids = [c for c in n.children if isinstance(c, bi.Node)]
        for i, c in enumerate(kids):
            if c.tag == "h4" and c.text().startswith("Hiện tượng") and i + 1 < len(kids) and kids[i + 1].text():
                fields.insert(0, ("Hiện tượng", kids[i + 1].text()))
        title_txt = f"{last_title['code']} {last_title['title']}".strip() if last_title else ""
        entry = base(n, "deep-dive", fields, n.attrs.get("data-symptom") or (last_title["title"] if last_title else ""),
                     [s.lower() for s in slugs], kind if kind in KINDS else "")
        entry["deep_dive"] = title_txt
        if last_title and last_title["id"]:
            entry["href"] = f"{rel}#{last_title['id']}"
        entries.append(entry)

    # ---- glossary
    for dl in root.find_all("dl", "glossary"):
        if dl.has_ancestor_class("guide"):
            continue
        kids = [c for c in dl.children if isinstance(c, bi.Node)]
        for i, dt in enumerate(kids):
            if dt.tag != "dt":
                continue
            name = dt.text()
            term = (dt.attrs.get("data-term") or "").strip()
            dd = kids[i + 1] if i + 1 < len(kids) and kids[i + 1].tag == "dd" else None
            definition = dd.text() if dd else ""
            if not name and not definition:
                continue  # placeholder
            where = f"{rel} [glossary '{name}']"
            if not term:
                problems.append(f"{where}: dt thiếu data-term")
                continue
            if not SLUG_RE.match(term):
                problems.append(f"{where}: data-term không phải kebab-case chữ thường: {term}")
            if dt.attrs.get("id") != f"term-{term}":
                problems.append(f"{where}: id phải là 'term-{term}' (đang là '{dt.attrs.get('id', '')}')")
            terms.append({"term": term.lower(), "name": name, "definition": definition, "topic": topic,
                          "topic_title": title, "href": f"{rel}#term-{term}"})
    return entries, terms, problems, is_draft


def collect(only_topic=None):
    data = {"topics": [], "entries": [], "terms": [], "insights": [], "lint": {}}
    tdir_root = ROOT / "topics"
    if not tdir_root.exists():
        return data
    for tdir in sorted(p for p in tdir_root.iterdir() if p.is_dir() and not p.name.startswith("_")):  # _* = test fixtures
        if only_topic and tdir.name != only_topic:
            continue
        pages = sorted(tdir.glob("[0-9][0-9]-*.html"))
        if not pages:
            continue
        title = bi.topic_title(tdir)
        impls = implementations(tdir)
        data["topics"].append({"slug": tdir.name, "title": title})
        for page in pages:
            entries, terms, probs, is_draft = scan_page(tdir.name, title, impls, page)
            data["entries"].extend(entries)
            data["terms"].extend(terms)
            data["lint"][f"topics/{tdir.name}/{page.name}"] = {"draft": is_draft, "problems": probs}
            ins, _dives, _p, _d = bi.scan_page(tdir.name, title, page)
            data["insights"].extend(ins)
    return data


# ---------------------------------------------------------------- rendering helpers
def page_shell(title, eyebrow, stats_html, filters, body, generated, js=True):
    script = '<script src="shared/docs/lab-knowledge.js" defer></script>\n' if js else ""
    return f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<link rel="stylesheet" href="shared/docs/lab.css">
<script src="shared/docs/lab.js" defer></script>
{script}</head>
<!-- GENERATED by scripts/build_knowledge.py — do not edit by hand. -->
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
    <div class="kn-stats">{stats_html}</div>
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


def stats(items):
    return "".join(f"<div><strong>{v}</strong><span>{e(k)}</span></div>" for k, v in items)


def filter_bar(prefix, placeholder, topics, kinds=None, count_label="mục"):
    topic_opts = "".join(f'<option value="{e(t["slug"])}">{e(t["title"])}</option>' for t in topics)
    kind_sel = ""
    if kinds:
        kind_opts = "".join(f'<option value="{k}">{e(v)}</option>' for k, v in kinds.items())
        kind_sel = f'<select id="kn-kind"><option value="">Mọi loại vấn đề</option>{kind_opts}</select>'
    return (f'<section class="kn-filters" aria-label="Bộ lọc" data-kn="{prefix}">'
            f'<input type="search" id="kn-q" placeholder="{e(placeholder)}" autocomplete="off">'
            f'<select id="kn-topic"><option value="">Mọi topic</option>{topic_opts}</select>{kind_sel}'
            f'<p class="kn-count"><span id="kn-visible">0</span> / <span id="kn-total">0</span> {e(count_label)} đang hiển thị</p></section>')


def fields_dl(fields, skip=()):
    rows = "".join(f"<dt>{e(h)}</dt><dd>{e(v)}</dd>" for h, v in fields if h not in skip)
    return f'<dl class="kn-fields">{rows}</dl>' if rows else ""


def src_link(entry):
    sec = f" · {e(entry['section'])}" if entry["section"] else ""
    return f'<a class="kn-src" href="{e(entry["href"])}">{e(entry["topic_title"])} · {e(entry["page"])}{sec}</a>'


# ---------------------------------------------------------------- PROBLEMS.html
def render_problems(data):
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    topics = data["topics"]
    by_slug = {}
    for en in data["entries"]:
        for s in en["problems"]:
            by_slug.setdefault(s, []).append(en)

    if not by_slug:
        body = ('<section><h2 id="empty">Chưa có vấn đề nào được lập chỉ mục</h2>'
                '<p class="empty-note">Chưa có topic nào gắn <code>data-problem</code> vào bảng vấn đề (01 §4), failure mode (01 §13, §17), '
                'chuyên đề, decision guide (06 §6) hay runbook (07 §3). Chạy <code>/research &lt;topic&gt;</code>; sau mỗi phase, '
                '<code>python3 scripts/build_knowledge.py</code> sẽ cập nhật trang này.</p></section>')
        return page_shell("Chỉ mục theo vấn đề", "Theo vấn đề",
                          stats([("vấn đề", 0), ("topic", len(topics)), ("nguồn", 0)]), "", body, generated, js=False)

    def primary_kind(items):
        counts = {}
        for it in items:
            if it["kind"]:
                counts[it["kind"]] = counts.get(it["kind"], 0) + 1
        return max(counts, key=lambda k: (counts[k], -list(KINDS).index(k))) if counts else ""

    cards_by_kind = {k: [] for k in list(KINDS) + [""]}
    for slug, items in sorted(by_slug.items(), key=lambda kv: (-len({i["topic"] for i in kv[1]}), kv[0])):
        kinds = sorted({i["kind"] for i in items if i["kind"]}, key=list(KINDS).index)
        tset = sorted({i["topic"] for i in items})
        symptoms = []
        for i in items:
            if i["symptom"] and i["symptom"] not in symptoms and i["role"] in ("symptom", "cause"):
                symptoms.append(i["symptom"])
        related = [ins for ins in data["insights"] if slug in ins["tags"]]

        def section(role, heading, render_item):
            its = [i for i in items if i["role"] == role]
            if not its:
                return ""
            return f'<div class="kn-sec"><h4>{heading}</h4><ul class="kn-items">{"".join(render_item(i) for i in its)}</ul></div>'

        def symptom_item(i):
            return f'<li>{fields_dl(i["fields"])}{src_link(i)}</li>'

        def cause_item(i):
            title = f'<strong>{e(i.get("deep_dive") or i["symptom"])}</strong>' if (i.get("deep_dive") or i["symptom"]) else ""
            skip = ("Failure mode", "ID") if not i.get("deep_dive") else ()
            return f'<li>{title}{fields_dl(i["fields"], skip=skip)}{src_link(i)}</li>'

        def decision_item(i):
            ctx = next((v for h, v in i["fields"] if h.startswith("Ngữ cảnh")), "")
            why = next((v for h, v in i["fields"] if h.startswith("Vì sao")), "")
            choice = i.get("choice") or next((v for h, v in i["fields"] if h.startswith("Chọn")), "")
            label = f' — {e(i["choice_label"])}' if i.get("choice_label") else ""
            return (f'<li class="kn-decision"><span class="kn-ctx">{e(ctx) or "—"}</span> <span class="kn-arrow">→</span> '
                    f'<span class="kn-choice">{e(choice) or "?"}{label}</span>'
                    f'{f"<p class=kn-why>{e(why)}</p>" if why else ""}{src_link(i)}</li>')

        def runbook_item(i):
            return f'<li>{fields_dl(i["fields"])}{src_link(i)}</li>'

        topic_links = "".join(
            f'<a class="kn-topic-chip" href="topics/{e(t)}/01-research.html#problem">{e(next(x["title"] for x in topics if x["slug"] == t))}</a>'
            for t in tset)
        rel_html = ""
        if related:
            rel_items = "".join(f'<li><a href="{e(r["href"])}">{e(r["claim"])}</a> <span class="kn-src">{e(r["topic_title"])}</span></li>'
                                for r in related)
            rel_html = f'<div class="kn-sec"><h4>Insight liên quan</h4><ul class="kn-items kn-related">{rel_items}</ul></div>'
        search = " ".join([slug, " ".join(symptoms)] + [v for i in items for _, v in i["fields"]]).lower()
        kind_badges = "".join(f'<span class="kn-kind kn-kind-{k}">{e(KINDS[k])}</span>' for k in kinds)
        cross = '<span class="cross-badge">liên topic</span>' if len(tset) > 1 else ""
        card = (f'<article class="kn-card" id="p-{e(slug)}" data-kn-item data-topics="{e(" ".join(tset))}" '
                f'data-kinds="{e(" ".join(kinds))}" data-search="{e(search)}">'
                f'<h3 class="kn-title"><code>{e(slug)}</code></h3>'
                f'<div class="kn-badges">{cross}{kind_badges}<span class="kn-ntopic">{len(tset)} topic · {len(items)} nguồn</span></div>'
                f'{"<p class=kn-symptom>" + " · ".join(e(s) for s in symptoms[:4]) + "</p>" if symptoms else ""}'
                f'<div class="kn-topics"><span>Topic giải quyết:</span>{topic_links}</div>'
                f'{section("symptom", "Biểu hiện &amp; tác động", symptom_item)}'
                f'{section("cause", "Nguyên nhân / cơ chế", cause_item)}'
                f'{section("decision", "Chọn gì (decision guide đã hiệu chỉnh)", decision_item)}'
                f'{section("runbook", "Chẩn đoán &amp; xử lý (runbook)", runbook_item)}'
                f'{rel_html}</article>')
        cards_by_kind[primary_kind(items)].append(card)

    sections = []
    for k, cards in cards_by_kind.items():
        if not cards:
            continue
        label = KINDS.get(k, "Chưa phân loại")
        sections.append(f'<section class="kn-group" data-kn-group><h2 id="kind-{k or "none"}">{e(label)}</h2>{"".join(cards)}</section>')
    nsrc = len(data["entries"])
    cross = sum(1 for items in by_slug.values() if len({i["topic"] for i in items}) > 1)
    intro = ('<p class="note">Tra từ triệu chứng: mỗi thẻ là một vấn đề nhìn từ bên ngoài, gom từ mọi topic — biểu hiện, nguyên nhân, '
             'topic/solution giải nó, nên chọn cách nào trong ngữ cảnh nào (đã hiệu chỉnh bằng số đo ở 06) và cách chẩn đoán, xử lý (07).</p>')
    return page_shell("Chỉ mục theo vấn đề", "Theo vấn đề",
                      stats([("vấn đề", len(by_slug)), ("liên topic", cross), ("topic", len(topics)), ("nguồn", nsrc)]),
                      filter_bar("problems", "Tìm triệu chứng, nguyên nhân, cách xử lý…", topics, KINDS, "vấn đề"),
                      intro + "".join(sections), generated)


# ---------------------------------------------------------------- GLOSSARY.html
def letter_of(term):
    c = term[:1].upper()
    return c if c.isalpha() else "#"


def definition_item(text, defs):
    links = "".join(f'<a class="kn-src" href="{e(d["href"])}">{e(d["topic_title"])}</a>' for d in defs)
    body = e(text) if text else "<em>(chưa có định nghĩa)</em>"
    return f'<li><p>{body}</p><div class="kn-src-list">{links}</div></li>'


def render_glossary(data):
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    topics = data["topics"]
    by_term = {}
    for t in data["terms"]:
        by_term.setdefault(t["term"], []).append(t)
    if not by_term:
        body = ('<section><h2 id="empty">Chưa có thuật ngữ</h2>'
                '<p class="empty-note">Chưa có topic nào điền §6 Thuật ngữ với <code>data-term</code>. Chạy <code>/research &lt;topic&gt;</code>; '
                'sau mỗi phase, <code>python3 scripts/build_knowledge.py</code> sẽ cập nhật trang này.</p></section>')
        return page_shell("Thuật ngữ chung", "Thuật ngữ", stats([("thuật ngữ", 0), ("topic", len(topics))]), "", body, generated, js=False)

    letters = {}
    for term in sorted(by_term):
        letters.setdefault(letter_of(term), []).append(term)
    jump = "".join(f'<a href="#letter-{e(l)}">{e(l)}</a>' for l in letters)
    sections = []
    for l, terms in letters.items():
        items = []
        for term in terms:
            defs = by_term[term]
            names = []
            for d in defs:
                if d["name"] and d["name"] not in names:
                    names.append(d["name"])
            tset = sorted({d["topic"] for d in defs})
            # identical definitions collapse to one entry listing every topic that wrote it
            grouped = {}
            for d in defs:
                grouped.setdefault(d["definition"], []).append(d)
            def_html = "".join(definition_item(text, ds) for text, ds in grouped.items())
            differ = '<span class="kn-differ">định nghĩa khác nhau giữa topic</span>' if len(grouped) > 1 else ""
            search = " ".join([term, " ".join(names)] + [d["definition"] for d in defs]).lower()
            items.append(f'<div class="kn-term" id="g-{e(term)}" data-kn-item data-topics="{e(" ".join(tset))}" data-search="{e(search)}">'
                         f'<h3 class="kn-term-name">{e(names[0] if names else term)}</h3>'
                         f'<div class="kn-badges"><code>{e(term)}</code>'
                         f'{"".join(f"<span class=kn-alias>{e(n)}</span>" for n in names[1:])}'
                         f'<span class="kn-ntopic">dùng trong {len(tset)} topic</span>{differ}</div>'
                         f'<ul class="kn-defs">{def_html}</ul></div>')
        sections.append(f'<section class="kn-group" data-kn-group><h2 id="letter-{e(l)}">{e(l)}</h2>{"".join(items)}</section>')
    shared = sum(1 for defs in by_term.values() if len({d["topic"] for d in defs}) > 1)
    body = f'<nav class="kn-az" aria-label="A–Z">{jump}</nav>' + "".join(sections)
    return page_shell("Thuật ngữ chung", "Thuật ngữ",
                      stats([("thuật ngữ", len(by_term)), ("dùng chung", shared), ("topic", len(topics))]),
                      filter_bar("glossary", "Tìm thuật ngữ hoặc định nghĩa…", topics, None, "thuật ngữ"),
                      body, generated)


# ---------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--problems-out", default=str(hub_path("problems")))
    ap.add_argument("--glossary-out", default=str(hub_path("glossary")))
    ap.add_argument("--json", metavar="OUT", help="also write the index as JSON")
    ap.add_argument("--check", action="store_true", help="lint problem/glossary markup; exit 1 on problems")
    ap.add_argument("--topic", help="limit to one topic slug")
    ap.add_argument("--include-draft", action="store_true", help="--check also pages whose <body> still has class draft")
    ap.add_argument("--no-page", action="store_true", help="do not write the HTML pages")
    args = ap.parse_args()
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    data = collect(args.topic)

    if args.check:
        total = 0
        for page, info in data["lint"].items():
            if info["draft"] and not args.include_draft:
                continue
            for p in info["problems"]:
                print(f"[knowledge] {p}")
                total += 1
        checked = sum(1 for i in data["lint"].values() if args.include_draft or not i["draft"])
        nprob = len({s for en in data["entries"] for s in en["problems"]})
        print(f"checked {checked} page(s), {nprob} problem slug(s), {len({t['term'] for t in data['terms']})} term(s): {total} problem(s)")
        if total:
            sys.exit(1)
        return

    if args.json:
        out = {"topics": data["topics"], "entries": data["entries"], "terms": data["terms"]}
        Path(args.json).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    if not args.no_page:
        Path(args.problems_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.glossary_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.problems_out).write_text(hubify(render_problems(data)), encoding="utf-8", newline="\n")
        Path(args.glossary_out).write_text(hubify(render_glossary(data)), encoding="utf-8", newline="\n")
        nprob = len({s for en in data["entries"] for s in en["problems"]})
        print(f"wrote hub/problems.html ({nprob} problem(s)) and hub/glossary.html ({len({t['term'] for t in data['terms']})} term(s)) "
              f"from {len(data['topics'])} topic(s)")


if __name__ == "__main__":
    main()
