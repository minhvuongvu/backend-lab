#!/usr/bin/env python3
"""Build the cross-topic Q&A hub (hub/questions.html) and lint Q&A / suggested-question markup.

Sources (read only), topics/_* directories (test fixtures) are skipped:
  - topics/<slug>/questions.html            "Hỏi đáp": every question the learner asked, with answers
        <article class="qa" id="q-001" data-status="open|answered|revisit" data-phase="0-7"
                 data-date="YYYY-MM-DD" data-kind="..." data-tags="a,b">
          <h3 class="q">…</h3> <div class="a">…</div> (required unless open)
          [p.refs] [p.followup] [div.a-update data-date=…]*
  - topics/<slug>/suggested-questions.html  "Câu hỏi nên hỏi": questions worth asking (no answers)
        <article class="ask" id="s-001" data-status="suggested|asked|skipped"
                 data-level="foundation|senior|expert" data-phase="0-7" data-kind="..." data-tags="a,b">
          <h3 class="q">…</h3> <p class="why-ask">…</p> [p.hint]
          <p class="answered-by"><a href="questions.html#q-007">…</a></p> (required iff asked)

Anything inside author guidance (`div.guide`) and HTML comments is ignored.

Output hub/questions.html: counts, open/revisit questions first (newest first), suggested questions
not asked yet (by level), every Q&A entry per topic (articles copied verbatim so lab.css/lab.js
styling and quiz mode apply; relative links rewritten to topics/<slug>/…, ids prefixed with the slug
so they stay unique on the hub page) and an index by tag.

Usage:
    python3 scripts/build_questions.py                 # regenerate hub/questions.html
    python3 scripts/build_questions.py --check         # lint; exit 1 on problems
    python3 scripts/build_questions.py --check --no-page --topic transactional-outbox

Check rules: required attributes and allowed values, id format and uniqueness per page, date format,
1–5 lowercase kebab-case tags, h3.q present, div.a present unless open (Q&A), p.why-ask present and
p.answered-by present iff asked and pointing to an existing q-NNN of the topic's questions.html.

Standard library only.
"""

import argparse
import html
import posixpath
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_insights as bi  # noqa: E402  (shared minimal DOM)
from _paths import hub_path, hubify  # noqa: E402

ROOT = bi.ROOT
QA_PAGE, ASK_PAGE = "questions.html", "suggested-questions.html"
KINDS = {"concept": "khái niệm", "why": "vì sao", "how": "làm thế nào", "compare": "so sánh",
         "tradeoff": "đánh đổi", "debug": "gỡ lỗi", "production": "production"}
QA_STATUS = {"open": "mở", "answered": "đã trả lời", "revisit": "cần xem lại"}
ASK_STATUS = {"suggested": "chưa hỏi", "asked": "đã hỏi", "skipped": "bỏ qua"}
LEVELS = {"foundation": "Nền tảng", "senior": "Senior", "expert": "Chuyên sâu"}
QA_ID_RE, ASK_ID_RE = re.compile(r"^q-\d{3,}$"), re.compile(r"^s-\d{3,}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
URL_ATTR_RE = re.compile(r'(\s(?:href|src)=")([^"]*)(")')
ID_ATTR_RE = re.compile(r'(\sid=")([^"]*)(")')


# ---------------------------------------------------------------- parsing (DOM + raw source spans)
class SpanBuilder(bi.TreeBuilder):
    """bi.TreeBuilder that also records the raw source span of every <article> element."""

    def __init__(self, text):
        super().__init__()
        self.text = text
        self.line_start = [0]
        for m in re.finditer("\n", text):
            self.line_start.append(m.end())
        self.spans = {}

    def abs_pos(self):
        line, col = self.getpos()
        return self.line_start[line - 1] + col

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)
        if tag == "article":
            self.spans[self.cur] = [self.abs_pos(), None]

    def handle_endtag(self, tag):
        if tag == "article":
            n = self.cur
            while n is not None and n.tag != "article":
                n = n.parent
            if n is not None and n in self.spans:
                self.spans[n][1] = self.text.find(">", self.abs_pos()) + 1
        super().handle_endtag(tag)


def parse_spans(path):
    text = path.read_text(encoding="utf-8")
    b = SpanBuilder(text)
    b.feed(text)
    b.close()
    return b.root, b.spans, text


def raw_of(node, spans, text):
    span = spans.get(node)
    if not span or span[1] is None or span[1] <= span[0]:
        return ""
    return text[span[0]:span[1]]


# ---------------------------------------------------------------- link / id rewriting
def rewrite_url(url, slug, page):
    """Point a link written inside topics/<slug>/<page> to the same target from the repo root
    (hubify() then adds ../ for the hub page)."""
    if not url or re.match(r"^(?:[a-z][a-z0-9+.-]*:|//)", url, re.I):
        return url  # absolute / external / mailto / data:
    if url.startswith("#"):
        return f"topics/{slug}/{page}{url}"
    if url.startswith("/"):
        return url
    path, _, frag = url.partition("#")
    norm = posixpath.normpath(f"topics/{slug}/{path}") if path else f"topics/{slug}/{page}"
    if norm.startswith("hub/"):
        norm = norm[4:]  # sibling of hub/questions.html; hubify leaves bare names alone
    return norm + (f"#{frag}" if frag else "")


def rewrite_fragment(raw, slug, page):
    raw = COMMENT_RE.sub("", raw)
    raw = URL_ATTR_RE.sub(lambda m: m.group(1) + html.escape(rewrite_url(html.unescape(m.group(2)), slug, page),
                                                              quote=True) + m.group(3), raw)
    # The article keeps its original id in data-qid (shown by lab.css) next to the topic slug.
    raw = re.sub(r'(<article\b[^>]*?)(\sid=")([^"]*)(")',
                 lambda m: f'{m.group(1)} data-topic="{slug}" data-qid="{m.group(3)}"{m.group(2)}{m.group(3)}{m.group(4)}',
                 raw, count=1)
    return ID_ATTR_RE.sub(lambda m: f"{m.group(1)}{slug}--{m.group(2)}{m.group(3)}", raw)


# ---------------------------------------------------------------- extraction + lint
def split_tags(raw):
    return [t.strip() for t in (raw or "").split(",") if t.strip()]


def tag_problems(tags):
    out = []
    if not tags:
        out.append("thiếu data-tags")
    elif len(tags) > 5:
        out.append(f"data-tags cần 1–5 tag, đang có {len(tags)}")
    bad = [t for t in tags if not bi.TAG_RE.match(t)]
    if bad:
        out.append(f"tag không phải kebab-case chữ thường: {', '.join(bad)}")
    return out


def valid_date(s):
    if not DATE_RE.match(s or ""):
        return False
    try:
        date.fromisoformat(s)
        return True
    except ValueError:
        return False


def common_problems(a, id_re, statuses):
    probs = []
    iid = a.get("id", "")
    if not id_re.match(iid):
        probs.append(f"id không đúng dạng ({iid!r})")
    st = a.get("data-status", "")
    if st not in statuses:
        probs.append(f"data-status không hợp lệ ({st!r}; cho phép: {'|'.join(statuses)})")
    ph = a.get("data-phase", "")
    if not (ph.isdigit() and 0 <= int(ph) <= 7):
        probs.append(f"data-phase không hợp lệ ({ph!r}; cho phép 0–7)")
    kind = a.get("data-kind", "")
    if kind not in KINDS:
        probs.append(f"data-kind không hợp lệ ({kind!r}; cho phép: {'|'.join(KINDS)})")
    probs.extend(tag_problems(split_tags(a.get("data-tags"))))
    return probs


def entries(root, cls):
    return [n for n in root.find_all("article", cls) if not n.has_ancestor_class("guide")]


def scan_qa(slug, title, path):
    root, spans, text = parse_spans(path)
    rel = f"topics/{slug}/{QA_PAGE}"
    items, problems, seen = [], [], set()
    for n in entries(root, "qa"):
        a = n.attrs
        iid = a.get("id", "")
        where = f"{rel}#{iid or '?'}"
        probs = common_problems(a, QA_ID_RE, QA_STATUS)
        if iid and iid in seen:
            probs.append(f"id trùng '{iid}'")
        seen.add(iid)
        if not valid_date(a.get("data-date", "")):
            probs.append(f"data-date không phải YYYY-MM-DD ({a.get('data-date', '')!r})")
        q = n.find("h3", "q")
        if q is None or not q.text():
            probs.append("thiếu h3.q (câu hỏi)")
        ans = n.find("div", "a")
        if a.get("data-status") != "open" and (ans is None or not ans.text()):
            probs.append("thiếu div.a (câu trả lời) dù không ở trạng thái open")
        for up in n.find_all("div", "a-update"):
            if not valid_date(up.attrs.get("data-date", "")):
                probs.append(f"div.a-update có data-date không hợp lệ ({up.attrs.get('data-date', '')!r})")
        problems.extend(f"{where}: {p}" for p in probs)
        items.append({
            "topic": slug, "topic_title": title, "id": iid, "status": a.get("data-status", ""),
            "phase": a.get("data-phase", ""), "date": a.get("data-date", ""), "kind": a.get("data-kind", ""),
            "tags": [t.lower() for t in split_tags(a.get("data-tags"))], "question": q.text() if q else "",
            "href": f"{rel}#{iid}", "html": rewrite_fragment(raw_of(n, spans, text), slug, QA_PAGE),
        })
    return items, problems


def scan_ask(slug, title, path, qa_ids):
    root, spans, text = parse_spans(path)
    rel = f"topics/{slug}/{ASK_PAGE}"
    items, problems, seen = [], [], set()
    for n in entries(root, "ask"):
        a = n.attrs
        iid = a.get("id", "")
        where = f"{rel}#{iid or '?'}"
        probs = common_problems(a, ASK_ID_RE, ASK_STATUS)
        if iid and iid in seen:
            probs.append(f"id trùng '{iid}'")
        seen.add(iid)
        level = a.get("data-level", "")
        if level not in LEVELS:
            probs.append(f"data-level không hợp lệ ({level!r}; cho phép: {'|'.join(LEVELS)})")
        q = n.find("h3", "q")
        if q is None or not q.text():
            probs.append("thiếu h3.q (câu hỏi)")
        why = n.find("p", "why-ask")
        if why is None or not why.text():
            probs.append("thiếu p.why-ask (vì sao đáng hỏi)")
        by = n.find("p", "answered-by")
        if a.get("data-status") == "asked":
            links = [x.attrs.get("href", "") for x in by.find_all("a")] if by is not None else []
            if not links:
                probs.append("data-status=asked nhưng thiếu p.answered-by có link tới questions.html#q-NNN")
            for href in links:
                m = re.match(r"^(?:\./)?questions\.html#(q-\d{3,})$", href)
                if not m:
                    probs.append(f"answered-by phải trỏ tới questions.html#q-NNN ({href!r})")
                elif m.group(1) not in qa_ids:
                    probs.append(f"answered-by trỏ tới {m.group(1)} không có trong {QA_PAGE}")
        elif by is not None:
            probs.append(f"có p.answered-by nhưng data-status={a.get('data-status', '')!r} (chỉ dùng khi asked)")
        problems.extend(f"{where}: {p}" for p in probs)
        items.append({
            "topic": slug, "topic_title": title, "id": iid, "status": a.get("data-status", ""), "level": level,
            "phase": a.get("data-phase", ""), "kind": a.get("data-kind", ""),
            "tags": [t.lower() for t in split_tags(a.get("data-tags"))], "question": q.text() if q else "",
            "href": f"{rel}#{iid}", "html": rewrite_fragment(raw_of(n, spans, text), slug, ASK_PAGE),
        })
    return items, problems


def topic_dirs():
    tdir = ROOT / "topics"
    if not tdir.exists():
        return []
    return [p for p in sorted(tdir.iterdir()) if p.is_dir() and not p.name.startswith("_")]  # _* = test fixtures


def collect(only_topic=None):
    data = {"topics": [], "qa": [], "ask": [], "problems": {}}
    for tdir in topic_dirs():
        if only_topic and tdir.name != only_topic:
            continue
        qa_path, ask_path = tdir / QA_PAGE, tdir / ASK_PAGE
        if not qa_path.exists() and not ask_path.exists():
            continue
        title = bi.topic_title(tdir)
        data["topics"].append({"slug": tdir.name, "title": title})
        qa_items = []
        if qa_path.exists():
            qa_items, probs = scan_qa(tdir.name, title, qa_path)
            data["qa"].extend(qa_items)
            data["problems"][f"topics/{tdir.name}/{QA_PAGE}"] = probs
        if ask_path.exists():
            ask_items, probs = scan_ask(tdir.name, title, ask_path, {q["id"] for q in qa_items})
            data["ask"].extend(ask_items)
            data["problems"][f"topics/{tdir.name}/{ASK_PAGE}"] = probs
    return data


def pending_counts(tdir):
    """(open+revisit Q&A entries, suggested questions not asked yet) of one topic; used by build_dashboard."""
    qa = ask = 0
    if (tdir / QA_PAGE).exists():
        qa = sum(1 for n in entries(bi.parse(tdir / QA_PAGE), "qa") if n.attrs.get("data-status") in ("open", "revisit"))
    if (tdir / ASK_PAGE).exists():
        ask = sum(1 for n in entries(bi.parse(tdir / ASK_PAGE), "ask") if n.attrs.get("data-status") == "suggested")
    return qa, ask


# ---------------------------------------------------------------- rendering
def e(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def stats(pairs):
    return '<div class="dash-stats">' + "".join(f"<div><strong>{e(v)}</strong><span>{e(k)}</span></div>"
                                                for k, v in pairs) + "</div>"


def item_link(i, extra=""):
    return (f'<li data-topic="{e(i["topic"])}" data-status="{e(i["status"])}"><a href="{e(i["href"])}">{e(i["question"])}</a>'
            f' <span class="qa-src">{e(i["topic_title"])} · {e(i["id"])}{extra}</span></li>')


def render(data):
    qa, ask, topics = data["qa"], data["ask"], data["topics"]
    count = lambda items, key, val: sum(1 for i in items if i[key] == val)  # noqa: E731
    suggested = [i for i in ask if i["status"] == "suggested"]
    header = stats([("câu hỏi", len(qa)), ("mở", count(qa, "status", "open")),
                    ("cần xem lại", count(qa, "status", "revisit")), ("đã trả lời", count(qa, "status", "answered")),
                    ("gợi ý chưa hỏi", len(suggested)), ("topic", len(topics))])
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    sections = []

    if not qa and not ask:
        sections.append(
            '<section><h2 id="empty">Chưa có câu hỏi</h2><p class="empty-note">Chưa topic nào có '
            '<code>questions.html</code> (hỏi đáp) hay <code>suggested-questions.html</code> (câu hỏi nên hỏi) có mục nào. '
            'Mỗi câu hỏi bạn đặt khi học một topic được ghi vào <code>topics/&lt;slug&gt;/questions.html</code>; '
            'chạy <code>python3 scripts/build_questions.py</code> (hoặc <code>make questions</code>) để cập nhật trang này.</p></section>')
    else:
        # Per kind
        kinds = [(k, count(qa, "kind", k)) for k in KINDS]
        rows = "".join(f'<tr><td>{e(label)} <code>{e(k)}</code></td><td>{n}</td></tr>'
                       for (k, n), label in zip(kinds, KINDS.values()) if n)
        sections.append('<section><h2 id="by-kind">Theo loại câu hỏi</h2>' + (
            f'<div class="table-wrap"><table class="qa-kinds"><thead><tr><th>Loại</th><th>Số câu</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>' if rows else '<p class="empty-note">Chưa có câu hỏi đã ghi.</p>') + '</section>')

        # Open / revisit first, newest first
        pending = sorted((i for i in qa if i["status"] in ("open", "revisit")),
                         key=lambda i: (i["date"], i["topic"], i["id"]), reverse=True)
        if pending:
            lis = "".join(item_link(i, f' · {e(QA_STATUS[i["status"]])} · {e(i["date"])}') for i in pending)
            body = f'<ul class="qa-pending">{lis}</ul>'
        else:
            body = '<p class="empty-note">Không có câu hỏi nào đang mở hay cần xem lại.</p>'
        sections.append(f'<section><h2 id="pending">Câu hỏi mở / cần xem lại</h2>{body}</section>')

        # Suggested, not asked yet, by level
        if suggested:
            groups = []
            for lv, label in LEVELS.items():
                items = [i for i in suggested if i["level"] == lv]
                if items:
                    groups.append(f'<div class="ask-level" data-level="{e(lv)}"><h3 id="level-{e(lv)}">{e(label)} '
                                  f'<span class="chip-count">{len(items)}</span></h3>'
                                  + "".join(i["html"] for i in items) + "</div>")
            body = "".join(groups)
        else:
            body = '<p class="empty-note">Không còn câu hỏi gợi ý nào chưa hỏi.</p>'
        sections.append(f'<section id="ask-list"><h2 id="suggested">Câu hỏi nên hỏi</h2>'
                        f'<p class="note">Câu hỏi gợi ý chưa hỏi, từ nền tảng tới chuyên sâu; hỏi xong thì ghi vào hỏi đáp của topic.</p>'
                        f'{body}</section>')

        # Per topic
        per_topic = []
        for t in topics:
            items = [i for i in qa if i["topic"] == t["slug"]]
            if not items:
                continue
            per_topic.append(
                f'<section class="qa-topic" data-slug="{e(t["slug"])}"><h3 id="topic-{e(t["slug"])}">{e(t["title"])}</h3>'
                f'<p class="tag-sub"><a href="topics/{e(t["slug"])}/{QA_PAGE}">Hỏi đáp của topic</a> · '
                f'<a href="topics/{e(t["slug"])}/README.html">README</a> · {len(items)} câu hỏi</p>'
                + "".join(i["html"] for i in items) + "</section>")
        sections.append('<section id="qa-log"><h2 id="by-topic">Hỏi đáp theo topic</h2>'
                        + ("".join(per_topic) or '<p class="empty-note">Chưa có câu hỏi đã ghi.</p>') + "</section>")

        # By tag
        tags = {}
        for i in qa + suggested:  # asked suggestions already appear as their Q&A entry
            for tg in i["tags"]:
                tags.setdefault(tg, []).append(i)
        order = sorted(tags, key=lambda tg: (-len({i["topic"] for i in tags[tg]}), -len(tags[tg]), tg))
        blocks = "".join(
            f'<div class="tag-group" data-tag="{e(tg)}"><h3 id="tag-{e(tg)}">#{e(tg)}</h3><ul>'
            + "".join(item_link(i) for i in tags[tg]) + "</ul></div>" for tg in order)
        sections.append('<section><h2 id="by-tag">Theo tag</h2>'
                        + (blocks or '<p class="empty-note">Chưa có tag.</p>') + "</section>")

    return f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hỏi đáp</title>
<link rel="stylesheet" href="shared/docs/lab.css">
<script src="shared/docs/lab.js" defer></script>
</head>
<!-- GENERATED by scripts/build_questions.py — do not edit by hand. -->
<body data-page="hub">
<div class="layout">
  <nav class="toc" aria-label="Mục lục">
    <div class="toc-title">Hỏi đáp</div>
    <ol></ol>
    <button class="theme-toggle" type="button">Theme</button>
  </nav>
  <main>
  <article class="doc">
  <header class="doc-header">
    <div class="eyebrow">backend-lab · Hỏi đáp</div>
    <h1>Hỏi đáp</h1>
    {header}
    <div class="meta"><span>Sinh lúc {generated}</span><span>Nguồn: topics/*/{QA_PAGE}, topics/*/{ASK_PAGE}</span></div>
  </header>
{chr(10).join(sections)}
  </article>
  </main>
</div>
</body>
</html>
"""


# ---------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=str(hub_path("questions")), help="output page (default: hub/questions.html)")
    ap.add_argument("--check", action="store_true", help="lint Q&A and suggested-question markup; exit 1 on problems")
    ap.add_argument("--topic", help="limit to one topic slug")
    ap.add_argument("--no-page", action="store_true", help="do not write hub/questions.html")
    args = ap.parse_args()
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    data = collect(args.topic)

    if args.check:
        total = 0
        for probs in data["problems"].values():
            for p in probs:
                print(f"[question] {p}")
                total += 1
        print(f"checked {len(data['problems'])} page(s), {len(data['qa']) + len(data['ask'])} question(s): {total} problem(s)")
        if total:
            sys.exit(1)
        return

    if not args.no_page:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(hubify(render(data)), encoding="utf-8", newline="\n")
        print(f"wrote {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}: {len(data['topics'])} topic(s), "
              f"{len(data['qa'])} question(s), {len(data['ask'])} suggested question(s)")


if __name__ == "__main__":
    main()
