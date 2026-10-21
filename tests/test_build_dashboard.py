"""build_dashboard.py: benchmark linter, LAB/BENCHMARKS pages, topics/_* skipped."""
import unittest

from _helpers import TempRepo
from _hub_fixtures import *  # noqa: F401,F403


class DashboardTest(unittest.TestCase):
    def test_bench_check_and_underscore_topics_skipped(self):
        good = BENCH.format(slug="pg-insert-in-tx-cost", value="0.42", unit="ms", lo="0.4", hi="0.45",
                            raw="results/raw/a.csv")
        repo = repo_with_topics(**{"alpha/05-results.html": research_page(good),
                                   "_fixture/05-results.html": research_page(
                                       BENCH.format(slug="X", value="abc", unit="", lo="", hi="", raw="nope"))})
        try:
            repo.write("topics/alpha/results/raw/a.csv", "t,v\n1,2\n")
            r = repo.py("build_dashboard.py", "--check")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)       # _fixture ignored
            r = repo.py("build_dashboard.py", "--check", "--include-underscore")
            self.assertNotEqual(r.returncode, 0)                         # ...but its rows are invalid
            self.assertEqual(repo.py("build_dashboard.py").returncode, 0)
            self.assertIn("pg-insert-in-tx-cost", repo.path("hub/benchmarks.html").read_text(encoding="utf-8"))
        finally:
            repo.cleanup()

    def test_bench_check_catches_bad_rows(self):
        cases = {
            "value": BENCH.format(slug="a-b", value="abc", unit="ms", lo="1", hi="2", raw="results/raw/a.csv"),
            "unit": BENCH.format(slug="a-b", value="1.5", unit="", lo="1", hi="2", raw="results/raw/a.csv"),
            "ci": BENCH.format(slug="a-b", value="5", unit="ms", lo="1", hi="2", raw="results/raw/a.csv"),
            "raw": BENCH.format(slug="a-b", value="1.5", unit="ms", lo="1", hi="2", raw="results/raw/missing.csv"),
        }
        for name, html in cases.items():
            with self.subTest(name):
                repo = repo_with_topics(**{"alpha/05-results.html": research_page(html)})
                try:
                    repo.write("topics/alpha/results/raw/a.csv", "t,v\n")
                    self.assertNotEqual(repo.py("build_dashboard.py", "--check").returncode, 0)
                finally:
                    repo.cleanup()

if __name__ == "__main__":
    unittest.main()
