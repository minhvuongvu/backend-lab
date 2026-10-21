#!/usr/bin/env python3
"""Render-check backend-lab HTML pages in headless Chrome/Edge (standard library only).

For every page it loads the file, lets scripts run (virtual time budget) and inspects the DOM:
  - no mermaid "Syntax error";
  - every <pre class="mermaid"> block ended up with an <svg>, and every rendered svg (id lab-mmd-*)
    contains at least one node/actor (catches the "all diagrams drawn into the first svg" bug);
  - pages with a header.doc-header got the injected nav.doc-nav.

Usage:
  python3 scripts/check_render.py                 # hub pages + templates
  python3 scripts/check_render.py topics/x/*.html # specific pages (topic documents)
  python3 scripts/check_render.py --budget 120000 # more virtual time for very large pages
Exit codes: 0 ok, 1 problems found, 0 with a warning when no browser is available (skipped).
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PAGES = ["index.html", "hub/lab.html", "hub/roadmap.html", "hub/problems.html", "hub/insights.html", "hub/benchmarks.html",
                 "hub/glossary.html", "hub/rules.html",
                 "templates/topic-README.html", *sorted(str(p.relative_to(ROOT)) for p in (ROOT / "templates").glob("0[1-7]-*.html"))]
BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
PRE_RE = re.compile(r'<pre class="mermaid"[^>]*>(.*?)</pre>', re.S)
SVG_RE = re.compile(r'<svg[^>]*id="lab-mmd[^"]*"')
SHAPE_RE = re.compile(r'class="(?:node|actor)[ "]')


def find_browser():
    if os.environ.get("LAB_CHROME"):
        return os.environ["LAB_CHROME"]
    for p in BROWSERS:
        if os.path.exists(p):
            return p
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge"):
        found = shutil.which(name)
        if found:
            return found
    return None


def dump_dom(browser, page, profile, budget):
    cmd = [browser, "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={profile}",
           f"--virtual-time-budget={budget}", "--dump-dom", page.resolve().as_uri()]
    res = subprocess.run(cmd, capture_output=True, timeout=max(120, budget // 1000 * 3))
    return res.stdout.decode("utf-8", errors="replace")


def check_dom(dom):
    problems = []
    # Only count the error mermaid draws inside an SVG; prose may legitimately mention "Syntax error".
    if any("Syntax error" in svg for svg in re.findall(r"<svg.*?</svg>", dom, re.S)):
        problems.append("mermaid reported 'Syntax error'")
    blocks = PRE_RE.findall(dom)
    not_rendered = sum(1 for b in blocks if "<svg" not in b)
    if not_rendered:
        problems.append(f"{not_rendered}/{len(blocks)} mermaid block(s) without svg")
    for m in SVG_RE.finditer(dom):
        end = dom.find("</svg>", m.start())
        if not SHAPE_RE.search(dom[m.start():end]):
            problems.append(f"empty diagram ({m.group(0)[:60]}…)")
    if 'class="doc-header"' in dom and 'class="doc-nav"' not in dom:
        problems.append("nav.doc-nav missing (lab.js did not run?)")
    return problems, len(blocks)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pages", nargs="*", help="pages relative to the repo root (default: hub pages + templates)")
    ap.add_argument("--budget", type=int, default=60000, help="virtual time budget in ms (default 60000)")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    browser = find_browser()
    if not browser:
        print("WARN check_render: no Chrome/Edge/Chromium found (set LAB_CHROME) — render check skipped")
        return 0
    pages = [ROOT / p if not Path(p).is_absolute() else Path(p) for p in (args.pages or DEFAULT_PAGES)]
    failed = 0
    with tempfile.TemporaryDirectory(prefix="lab-render-") as profile:
        for page in pages:
            if not page.exists():
                print(f"SKIP {page.relative_to(ROOT) if page.is_relative_to(ROOT) else page}: not found")
                continue
            dom = dump_dom(browser, page, profile, args.budget)
            rel = page.relative_to(ROOT) if page.is_relative_to(ROOT) else page
            if not dom.strip():
                print(f"FAIL {rel}: empty DOM (browser error)")
                failed += 1
                continue
            problems, diagrams = check_dom(dom)
            if problems:
                failed += 1
                print(f"FAIL {rel}: " + "; ".join(problems))
            else:
                print(f"ok   {rel} ({diagrams} diagram(s))")
    print(f"{len(pages) - failed}/{len(pages)} page(s) ok")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
