"""build_knowledge.py: problem index / glossary linter and pages."""
import unittest

from _helpers import TempRepo
from _hub_fixtures import *  # noqa: F401,F403


class KnowledgeTest(unittest.TestCase):
    def test_good_markup_builds_problem_and_glossary_pages(self):
        body = (KNOW_TABLE.format(rows='<tr data-problem="lost-events-on-deploy" data-kind="correctness">'
                                       '<td>Đúng đắn</td><td>Mất event khi deploy</td></tr>')
                + '<dl class="glossary"><dt id="term-at-least-once" data-term="at-least-once">at-least-once</dt>'
                  '<dd>Giao ít nhất một lần</dd></dl>')
        repo = repo_with_topics(**{"alpha/01-research.html": research_page(body)})
        try:
            r = repo.py("build_knowledge.py", "--check")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(repo.py("build_knowledge.py").returncode, 0)
            self.assertIn("lost-events-on-deploy", repo.path("hub/problems.html").read_text(encoding="utf-8"))
            self.assertIn("at-least-once", repo.path("hub/glossary.html").read_text(encoding="utf-8"))
        finally:
            repo.cleanup()

    def test_check_catches_missing_problem_kind_and_term(self):
        body = (KNOW_TABLE.format(rows='<tr><td>Hiệu năng</td><td>p99 tăng vọt</td></tr>'          # no data-problem
                                       '<tr data-problem="Bad_Slug" data-kind="speed">'            # bad slug + kind
                                       '<td>x</td><td>y</td></tr>')
                + '<dl class="glossary"><dt>idempotency</dt><dd>định nghĩa</dd>'                   # no data-term
                  '<dt id="term-wrong" data-term="fencing-token">fencing token</dt><dd>d</dd></dl>')  # id mismatch
        repo = repo_with_topics(**{"alpha/01-research.html": research_page(body)})
        try:
            r = repo.py("build_knowledge.py", "--check")
            self.assertNotEqual(r.returncode, 0)
            out = r.stdout + r.stderr
            for needle in ("thiếu data-problem", "Bad_Slug", "data-kind", "thiếu data-term", "term-fencing-token"):
                self.assertIn(needle, out)
        finally:
            repo.cleanup()

if __name__ == "__main__":
    unittest.main()
