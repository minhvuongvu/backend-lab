"""Render README.md and CLAUDE.md as readable HTML pages that share the lab look & navigation.

The Markdown files stay the source of truth: Claude Code only loads rules from CLAUDE.md, and GitHub
shows README.md on the repository page. This script regenerates:
  index.html       ← README.md   (lab home page)
  hub/rules.html   ← CLAUDE.md + .claude/rules/*.md   (core rules + detailed, path-scoped rules)

Supports the Markdown subset used in those files: headings, paragraphs, lists (nested by indent),
tables, fenced code, inline code, bold/italic, links. Standard library only.
Usage: python3 scripts/build_pages.py [--check]
"""
import argparse
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = [
    # source, output, title, eyebrow, prefix to repo root (for links and assets)
    ("README.md", "index.html", "backend-lab", "Trang chủ", ""),
    ("CLAUDE.md", "hub/rules.html", "Quy tắc của lab", "Trang tổng · Quy tắc", "../"),
]
# Detailed rules appended to a page, in file-name order (YAML front matter stripped).
APPENDIX = {"CLAUDE.md": ".claude/rules/*.md"}


def read_source(src):
    md = (ROOT / src).read_text(encoding="utf-8")
    if src not in APPENDIX:
        return md
    for f in sorted(ROOT.glob(APPENDIX[src])):
        part = re.sub(r"\A---\n.*?\n---\n", "", f.read_text(encoding="utf-8"), flags=re.S)
        md = md.rstrip() + "\n\n" + part.strip() + "\n"
    return md


def slug(text):
    t = re.sub(r"<[^>]+>", "", text).lower()
    t = t.replace("đ", "d")
    import unicodedata
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def inline(text, prefix):
    """Inline Markdown → HTML. Code spans are protected first so nothing inside them is formatted."""
    codes = []

    def keep_code(m):
        codes.append(f"<code>{html.escape(m.group(1), quote=False)}</code>")
        return f"\x00{len(codes) - 1}\x00"

    text = re.sub(r"`([^`]+)`", keep_code, text)
    text = html.escape(text, quote=False)

    def link(m):
        label, url = m.group(1), m.group(2)
        if not re.match(r"^(https?:|mailto:|#)", url):
            url = prefix + url
            url = re.sub(r"(^|/)README\.md(#.*)?$", lambda mm: mm.group(1) + "index.html" + (mm.group(2) or ""), url) \
                if url.endswith("README.md") or "README.md#" in url else url
            url = re.sub(r"CLAUDE\.md(#.*)?$", lambda mm: "hub/rules.html" + (mm.group(1) or ""), url)
            url = url.replace("hub/hub/", "hub/").replace("../hub/rules.html", "rules.html") if prefix == "../" else url
        if "#" in url and not url.startswith(("http:", "https:")):
            base, frag = url.split("#", 1)
            url = base + "#" + slug(frag)  # GitHub-style anchors keep diacritics; our heading ids drop them
        return f'<a href="{html.escape(url)}">{label}</a>'

    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], text)


def convert(md, prefix):
    lines = md.splitlines()
    out, i = [], 0
    in_section = False
    title = None
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            lang = line[3:].strip()
            body = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                body.append(lines[i])
                i += 1
            cls = f' class="language-{lang}"' if lang else ""
            out.append(f"<pre><code{cls}>{html.escape(chr(10).join(body), quote=False)}</code></pre>")
            i += 1
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            level, text = len(m.group(1)), m.group(2).strip()
            if level == 1 and title is None:
                title = text
            else:
                if level == 2:
                    if in_section:
                        out.append("</section>")
                    out.append("<section>")
                    in_section = True
                out.append(f'<h{level} id="{slug(text)}">{inline(text, prefix)}</h{level}>')
            i += 1
            continue
        if line.strip().startswith("<!--"):
            # HTML comments in the Markdown (e.g. topic table markers) are kept invisible.
            while i < len(lines) and "-->" not in lines[i]:
                i += 1
            i += 1
            continue
        if line.lstrip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{3,}", lines[i + 1]):
            cells = lambda l: [c.strip() for c in l.strip().strip("|").split("|")]
            head = cells(line)
            i += 2
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(cells(lines[i]))
                i += 1
            t = ['<div class="table-wrap"><table>', "<thead><tr>" + "".join(f"<th>{inline(c, prefix)}</th>" for c in head) + "</tr></thead>", "<tbody>"]
            t += ["<tr>" + "".join(f"<td>{inline(c, prefix)}</td>" for c in r) + "</tr>" for r in rows]
            t.append("</tbody></table></div>")
            out.append("\n".join(t))
            continue
        if re.match(r"^\s*([-*]|\d+\.)\s+", line):
            items = []
            while i < len(lines) and (re.match(r"^\s*([-*]|\d+\.)\s+", lines[i]) or (lines[i].startswith("  ") and lines[i].strip())):
                items.append(lines[i])
                i += 1
            out.append(render_list(items, prefix))
            continue
        if not line.strip():
            i += 1
            continue
        para = [line.strip()]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,4}\s|```|\s*([-*]|\d+\.)\s|\s*\|)", lines[i]):
            para.append(lines[i].strip())
            i += 1
        out.append(f"<p>{inline(' '.join(para), prefix)}</p>")
    if in_section:
        out.append("</section>")
    return title, "\n".join(out)


def render_list(items, prefix):
    """Nested lists by indentation (2+ spaces per level); continuation lines join the previous item."""
    root = {"children": [], "ordered": False}
    stack = [(-1, root)]
    for raw in items:
        m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", raw)
        if not m:
            stack[-1][1]["children"][-1]["text"] += " " + raw.strip()
            continue
        indent, marker, text = len(m.group(1)), m.group(2), m.group(3)
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if not parent["children"]:
            parent["ordered"] = marker[0].isdigit()
        node = {"text": text, "children": [], "ordered": False}
        parent["children"].append(node)
        stack.append((indent, node))

    def emit(node):
        if not node["children"]:
            return ""
        tag = "ol" if node["ordered"] else "ul"
        return f"<{tag}>" + "".join(f"<li>{inline(c['text'], prefix)}{emit(c)}</li>" for c in node["children"]) + f"</{tag}>"

    return emit(root)


def page(title, eyebrow, body, prefix, source):
    return f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="{prefix}shared/docs/lab.css">
<link id="hljs-light" rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
<link id="hljs-dark" rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js" defer></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js" defer></script>
<script src="{prefix}shared/docs/lab.js" defer></script>
</head>
<!-- GENERATED from {source} by scripts/build_pages.py — edit {source}, not this file. -->
<body data-page="hub">
<div class="layout">
  <nav class="toc" aria-label="Mục lục">
    <div class="toc-title">{html.escape(title)}</div>
    <ol></ol>
    <button class="theme-toggle" type="button">Theme</button>
  </nav>
  <main>
  <article class="doc">
  <header class="doc-header">
    <div class="eyebrow">{html.escape(eyebrow)}</div>
    <h1>{html.escape(title)}</h1>
    <div class="meta"><span>Nguồn: <code>{source}</code> (trang này tự sinh)</span></div>
  </header>
{body}
  </article>
  </main>
</div>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="exit 1 if a generated page is out of date")
    args = ap.parse_args()
    stale = []
    for src, dst, default_title, eyebrow, prefix in PAGES:
        md = read_source(src)
        title, body = convert(md, prefix)
        out = page(title or default_title, eyebrow, body, prefix, src)
        target = ROOT / dst
        if args.check:
            if not target.exists() or target.read_text(encoding="utf-8") != out:
                stale.append(dst)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(out, encoding="utf-8", newline="\n")
        print(f"wrote {dst} from {src}")
    if stale:
        print("out of date (run python3 scripts/build_pages.py): " + ", ".join(stale))
        sys.exit(1)


if __name__ == "__main__":
    main()
