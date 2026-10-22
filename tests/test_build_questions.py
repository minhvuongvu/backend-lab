"""build_questions.py: Q&A / suggested-question linter and hub/questions.html."""
import re
import unittest

from _hub_fixtures import *  # noqa: F401,F403


def build(repo):
    r = repo.py("build_questions.py")
    if r.returncode != 0:
        raise AssertionError(r.stdout + r.stderr)
    return repo.path("hub/questions.html").read_text(encoding="utf-8")


class QuestionsPageTest(unittest.TestCase):
    def setUp(self):
        guide = '<div class="guide">' + qa("q-900", status="bogus", tags="Bad Tag", question="Ví dụ mẫu") + "</div>"
        self.repo = repo_with_topics(**{
            "alpha/questions.html": qa_page(
                qa("q-001"),
                qa("q-002", status="open", answer=None, date="2026-10-21", kind="how", question="Câu mở alpha"),
                qa("q-003", status="revisit", date="2026-10-22", kind="debug", question="Câu xem lại alpha",
                   tags="mvcc,vacuum") + "<!-- " + qa("q-004", status="bogus") + " -->",
                guide=guide),
            "alpha/suggested-questions.html": ask_page(
                ask("s-001", level="expert", question="Gợi ý chuyên sâu"),
                ask("s-002", level="foundation", question="Gợi ý nền tảng"),
                ask("s-003", status="asked", question="Đã hỏi rồi",
                    extra='<p class="answered-by"><a href="questions.html#q-001">Đã hỏi → q-001</a></p>')),
            "beta/questions.html": qa_page(qa("q-001", question="Câu beta", kind="compare", tags="kafka")),
            "_fixture/questions.html": qa_page(qa("q-001", question="Câu fixture ẩn")),
        })

    def tearDown(self):
        self.repo.cleanup()

    def test_counts_order_and_sections(self):
        page = build(self.repo)
        self.assertIn('data-page="hub"', page)
        stats = dict((label, int(n)) for n, label in re.findall(r"<strong>(\d+)</strong><span>([^<]+)</span>", page))
        self.assertEqual(stats["câu hỏi"], 4)
        self.assertEqual(stats["mở"], 1)
        self.assertEqual(stats["cần xem lại"], 1)
        self.assertEqual(stats["đã trả lời"], 2)
        self.assertEqual(stats["gợi ý chưa hỏi"], 2)
        self.assertEqual(stats["topic"], 2)
        # open/revisit list: newest first, links to the topic page
        pending = page[page.index('<ul class="qa-pending">'):]
        pending = pending[:pending.index("</ul>")]
        self.assertLess(pending.index("Câu xem lại alpha"), pending.index("Câu mở alpha"))
        self.assertIn('href="../topics/alpha/questions.html#q-002"', pending)
        # suggested: only status=suggested, foundation before expert
        self.assertLess(page.index("Gợi ý nền tảng"), page.index("Gợi ý chuyên sâu"))
        self.assertNotIn("Đã hỏi rồi", page)
        self.assertIn('href="../topics/alpha/suggested-questions.html#s-001"', page)
        # per-topic sections with articles copied verbatim
        self.assertIn('<section class="qa-topic" data-slug="alpha">', page)
        self.assertIn('<section class="qa-topic" data-slug="beta">', page)
        self.assertEqual(page.count('<article class="qa"'), 4)
        self.assertIn('<h3 class="q">Câu beta</h3>', page)
        # tag index
        self.assertIn('data-tag="mvcc"', page)
        self.assertIn('data-tag="kafka"', page)
        # per kind
        self.assertIn("<code>compare</code></td><td>1</td>", page)

    def test_links_rewritten_ids_prefixed(self):
        page = build(self.repo)
        self.assertIn('href="../topics/alpha/01-research.html#s11"', page)
        self.assertIn('href="../topics/alpha/questions.html#src-1"', page)
        self.assertIn('href="https://example.com/doc"', page)
        self.assertIn('href="../topics/beta/01-research.html#s11"', page)
        self.assertIn('id="alpha--q-001"', page)
        self.assertIn('id="beta--q-001"', page)
        self.assertNotRegex(page, r'\sid="q-001"')
        # the original id stays visible (lab.css shows data-topic · data-qid on the hub)
        self.assertIn('data-topic="alpha" data-qid="q-001" id="alpha--q-001"', page)

    def test_guide_comments_and_underscore_topics_ignored(self):
        page = build(self.repo)
        self.assertNotIn("Ví dụ mẫu", page)
        self.assertNotIn("q-004", page)
        self.assertNotIn("Câu fixture ẩn", page)
        r = self.repo.py("build_questions.py", "--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("checked 3 page(s), 7 question(s): 0 problem(s)", r.stdout)

    def test_no_page_writes_nothing(self):
        r = self.repo.py("build_questions.py", "--check", "--no-page")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(self.repo.path("hub/questions.html").exists())


class EmptyTest(unittest.TestCase):
    def test_empty_repo_renders_empty_state(self):
        repo = TempRepo(scripts=HUB_SCRIPTS)
        try:
            page = build(repo)
            self.assertIn('id="empty"', page)
            self.assertIn('href="../shared/docs/lab.css"', page)
            r = repo.py("build_questions.py", "--check")
            self.assertEqual(r.returncode, 0)
            self.assertIn("checked 0 page(s), 0 question(s): 0 problem(s)", r.stdout)
        finally:
            repo.cleanup()


class CheckTest(unittest.TestCase):
    QA_CASES = {
        "status": (qa("q-001", status="done"), "data-status"),
        "phase": (qa("q-001", phase="9"), "data-phase"),
        "kind": (qa("q-001", kind="trivia"), "data-kind"),
        "date": (qa("q-001", date="2026-13-40"), "data-date"),
        "date-format": (qa("q-001", date="22/10/2026"), "data-date"),
        "id-format": (qa("q1"), "id không đúng dạng"),
        "duplicate-id": (qa("q-001") + qa("q-001"), "id trùng"),
        "tags-missing": (qa("q-001", tags=""), "thiếu data-tags"),
        "tags-count": (qa("q-001", tags="a,b,c,d,e,f"), "1–5"),
        "tags-case": (qa("q-001", tags="MVCC"), "kebab-case"),
        "no-question": (qa("q-001", question=""), "h3.q"),
        "no-answer": (qa("q-001", status="answered", answer=None), "div.a"),
        "update-date": (qa("q-001", extra='<div class="a-update" data-date="hôm qua">x</div>'), "a-update"),
    }
    ASK_CASES = {
        "status": (ask("s-001", status="maybe"), "data-status"),
        "level": (ask("s-001", level="junior"), "data-level"),
        "id-format": (ask("q-001"), "id không đúng dạng"),
        "no-why": (ask("s-001", why=""), "why-ask"),
        "asked-without-link": (ask("s-001", status="asked"), "answered-by"),
        "asked-dangling": (ask("s-001", status="asked",
                               extra='<p class="answered-by"><a href="questions.html#q-099">q-099</a></p>'), "q-099"),
        "answered-by-not-asked": (ask("s-001",
                                      extra='<p class="answered-by"><a href="questions.html#q-001">q-001</a></p>'), "asked"),
    }

    def run_case(self, pages, needle):
        repo = repo_with_topics(**pages)
        try:
            r = repo.py("build_questions.py", "--check")
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn(needle, r.stdout)
        finally:
            repo.cleanup()

    def test_qa_errors(self):
        for name, (html, needle) in self.QA_CASES.items():
            with self.subTest(name):
                self.run_case({"alpha/questions.html": qa_page(html)}, needle)

    def test_open_question_needs_no_answer(self):
        repo = repo_with_topics(**{"alpha/questions.html": qa_page(qa("q-001", status="open", answer=None))})
        try:
            self.assertEqual(repo.py("build_questions.py", "--check").returncode, 0)
        finally:
            repo.cleanup()

    def test_suggested_errors(self):
        for name, (html, needle) in self.ASK_CASES.items():
            with self.subTest(name):
                self.run_case({"alpha/questions.html": qa_page(qa("q-001")),
                               "alpha/suggested-questions.html": ask_page(html)}, needle)


class OtherHubsIgnoreQuestionsTest(unittest.TestCase):
    def test_insight_and_knowledge_linters_skip_qa_pages(self):
        # questions.html has no insight and may use span.tag evidence labels: it must not be linted as a phase page.
        body = qa("q-001", answer='<p>x <span class="tag measured">đo được</span></p>')
        repo = repo_with_topics(**{"alpha/01-research.html": research_page(insight("ins-a-1", "mvcc,kafka")),
                                   "alpha/questions.html": qa_page(body),
                                   "alpha/suggested-questions.html": ask_page(ask("s-001"))})
        try:
            for script in ("build_insights.py", "build_knowledge.py"):
                r = repo.py(script, "--check")
                self.assertEqual(r.returncode, 0, f"{script}: {r.stdout}{r.stderr}")
                self.assertIn("checked 1 page(s)", r.stdout, script)
        finally:
            repo.cleanup()


if __name__ == "__main__":
    unittest.main()
