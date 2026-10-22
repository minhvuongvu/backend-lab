"""Fixture builders shared by the hub-builder tests (build_insights / build_knowledge / build_questions / build_dashboard)."""
from _helpers import TempRepo

HUB_SCRIPTS = ["build_insights.py", "build_knowledge.py", "build_questions.py", "build_dashboard.py"]

WHY = ("<dt>Cơ chế</dt><dd><ol><li>bước 1</li><li>bước 2</li></ol></dd><dt>Điều kiện</dt><dd>tải cao</dd>"
       "<dt>Định lượng</dt><dd>{q}</dd><dt>Khi nào không đúng</dt><dd>khi X</dd><dt>Liên hệ</dt><dd>§8</dd>")


def insight(iid, tags, quant="~60 event/ngày", claim="Khẳng định có thật"):
    return (f'<div class="callout insight" id="{iid}" data-tags="{tags}"><span class="callout-title">Insight</span>'
            f'<p class="claim">{claim}</p><div class="why"><strong>Vì sao:</strong><dl class="why-steps">'
            f'{WHY.format(q=quant)}</dl></div><div class="evidence"><strong>Căn cứ:</strong> suy luận</div></div>')


def research_page(body, draft=False):
    cls = ' class="draft"' if draft else ""
    return f'<!doctype html><html><head><title>t</title></head><body{cls}><main><article class="doc">{body}</article></main></body></html>'


README = '<!doctype html><html><body><h1>{title}</h1></body></html>'


def repo_with_topics(**pages):
    """pages: {"slug/01-research.html": html, ...}"""
    repo = TempRepo(scripts=HUB_SCRIPTS)
    seen = set()
    for rel, html in pages.items():
        slug = rel.split("/")[0]
        repo.write(f"topics/{rel}", html)
        if slug not in seen:
            repo.write(f"topics/{slug}/README.html", README.format(title=slug.title()))
            seen.add(slug)
    return repo


KNOW_TABLE = ('<table data-index="problem-type"><thead><tr><th>Loại vấn đề</th><th>Biểu hiện</th></tr></thead>'
              '<tbody>{rows}</tbody></table>')


BENCH = ('<table class="benchmarks"><thead><tr><th>Đại lượng</th></tr></thead><tbody>'
         '<tr data-bench="{slug}" data-value="{value}" data-unit="{unit}" data-metric="p99" data-ci-low="{lo}" '
         'data-ci-high="{hi}" data-conditions="1k req/s" data-raw="{raw}"><td>x</td></tr></tbody></table>')


def qa(qid, status="answered", phase="1", date="2026-10-20", kind="why", tags="mvcc,isolation-levels",
       question="Vì sao MVCC không chặn đọc?", answer='<p>Vì đọc snapshot. Xem <a href="01-research.html#s11">01 §11</a> '
       'và <a href="#src-1">[1]</a>, <a href="https://example.com/doc">doc</a>.</p>', extra=""):
    """One article.qa of topics/<slug>/questions.html; pass answer=None to omit div.a, question="" to omit h3.q."""
    q = f'<h3 class="q">{question}</h3>' if question else ""
    a = f'<div class="a">{answer}</div>' if answer is not None else ""
    return (f'<article class="qa" id="{qid}" data-status="{status}" data-phase="{phase}" data-date="{date}" '
            f'data-kind="{kind}" data-tags="{tags}">{q}{a}{extra}</article>')


def ask(sid, status="suggested", level="senior", phase="1", kind="tradeoff", tags="mvcc",
        question="Khi nào snapshot cũ làm phình bảng?", why="Lộ ra hiểu lầm về vacuum.", extra=""):
    """One article.ask of topics/<slug>/suggested-questions.html; why="" omits p.why-ask."""
    w = f'<p class="why-ask">{why}</p>' if why else ""
    return (f'<article class="ask" id="{sid}" data-status="{status}" data-phase="{phase}" data-level="{level}" '
            f'data-kind="{kind}" data-tags="{tags}"><h3 class="q">{question}</h3>{w}{extra}</article>')


def qa_page(*articles, guide=""):
    return research_page(f'{guide}<section id="qa-log">{"".join(articles)}</section>'
                         '<ol class="sources"><li id="src-1">nguồn</li></ol>')


def ask_page(*articles, guide=""):
    return research_page(f'{guide}<section id="ask-list">{"".join(articles)}</section>')
