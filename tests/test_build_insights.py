"""build_insights.py: insight linter and INSIGHTS.html; also the empty-repo render of every hub page."""
import unittest

from _helpers import TempRepo
from _hub_fixtures import *  # noqa: F401,F403


class EmptyRepoTest(unittest.TestCase):
    def test_all_pages_render_without_topics(self):
        repo = TempRepo(scripts=HUB_SCRIPTS)
        try:
            for script, pages in [("build_insights.py", ["hub/insights.html"]),
                                  ("build_knowledge.py", ["hub/problems.html", "hub/glossary.html"]),
                                  ("build_questions.py", ["hub/questions.html"]),
                                  ("build_dashboard.py", ["hub/lab.html", "hub/benchmarks.html"])]:
                r = repo.py(script)
                self.assertEqual(r.returncode, 0, f"{script}: {r.stdout}{r.stderr}")
                for p in pages:
                    html = repo.path(p).read_text(encoding="utf-8")
                    self.assertIn('data-page="hub"', html, p)
                c = repo.py(script, "--check")
                self.assertEqual(c.returncode, 0, f"{script} --check: {c.stdout}{c.stderr}")
        finally:
            repo.cleanup()


class InsightsTest(unittest.TestCase):
    def test_check_passes_on_complete_insight(self):
        repo = repo_with_topics(**{"alpha/01-research.html": research_page(insight("ins-a-1", "at-least-once,kafka"))})
        try:
            r = repo.py("build_insights.py", "--check")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = repo.py("build_insights.py")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Khẳng định có thật", repo.path("hub/insights.html").read_text(encoding="utf-8"))
        finally:
            repo.cleanup()

    def test_check_catches_missing_why_bad_tags_duplicate_ids(self):
        body = (insight("ins-dup", "kafka,at-least-once", quant="")    # empty "Định lượng"
                + insight("ins-dup", "Kafka,at-least-once")              # duplicate id + uppercase tag
                + insight("ins-ok", "single"))                           # only one tag (needs 2-5)
        repo = repo_with_topics(**{"alpha/01-research.html": research_page(body)})
        try:
            r = repo.py("build_insights.py", "--check")
            self.assertNotEqual(r.returncode, 0)
            out = r.stdout + r.stderr
            self.assertIn("Định lượng", out)
            self.assertIn("ins-dup", out)
            self.assertIn("Kafka", out)
        finally:
            repo.cleanup()

    def test_draft_pages_skipped_unless_include_draft(self):
        bad = insight("ins-x", "Bad Tag")
        repo = repo_with_topics(**{"alpha/01-research.html": research_page(bad, draft=True)})
        try:
            self.assertEqual(repo.py("build_insights.py", "--check").returncode, 0)
            self.assertNotEqual(repo.py("build_insights.py", "--check", "--include-draft").returncode, 0)
        finally:
            repo.cleanup()

    def test_guide_examples_are_ignored(self):
        body = '<div class="guide">' + insight("ins-example-1", "Bad Tag") + "</div>"
        repo = repo_with_topics(**{"alpha/01-research.html": research_page(body)})
        try:
            self.assertEqual(repo.py("build_insights.py", "--check").returncode, 0)
        finally:
            repo.cleanup()

if __name__ == "__main__":
    unittest.main()
