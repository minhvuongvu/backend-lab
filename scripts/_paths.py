"""Where the repo-level hub pages live, and how to point links from inside hub/ back to the repo root.

Hub pages (generated or hand-maintained) sit in hub/; topic documents stay in topics/<slug>/;
shared assets in shared/docs/. Generators build links as if the page were at the repo root and pass
the final HTML through hubify() before writing it into hub/.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HUB = ROOT / "hub"
PAGES = {
    "lab": "lab.html",
    "roadmap": "roadmap.html",
    "problems": "problems.html",
    "insights": "insights.html",
    "benchmarks": "benchmarks.html",
    "glossary": "glossary.html",
    "rules": "rules.html",
}
LEGACY = {"LAB.html": "lab.html", "ROADMAP.html": "roadmap.html", "PROBLEMS.html": "problems.html",
          "INSIGHTS.html": "insights.html", "BENCHMARKS.html": "benchmarks.html", "GLOSSARY.html": "glossary.html"}


def hub_path(key):
    return HUB / PAGES[key]


def hubify(html):
    """Rewrite root-relative links for a page that lives in hub/ (idempotent)."""
    html = re.sub(r'((?:href|src)=")(?!\.\./|https?:|#|mailto:)(shared/|topics/|templates/|index\.html)', r"\1../\2", html)
    for old, new in LEGACY.items():
        html = re.sub(rf'((?:href)="){re.escape(old)}', rf"\1{new}", html)
    return html
