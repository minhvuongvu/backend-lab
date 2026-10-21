import random
import statistics
import unittest

from _helpers import TempRepo, load_module

stats = load_module("stats")


class PercentileTest(unittest.TestCase):
    def test_type7_interpolation(self):
        self.assertAlmostEqual(stats.percentile(list(range(1, 11)), 90), 9.1)
        self.assertAlmostEqual(stats.percentile(list(range(1, 11)), 50), 5.5)
        self.assertEqual(stats.percentile([7.0], 99), 7.0)

    def test_empty_is_nan(self):
        self.assertNotEqual(stats.percentile([], 50), stats.percentile([], 50))  # NaN != NaN


class RankTestsTest(unittest.TestCase):
    def test_mann_whitney_exact_no_ties(self):
        _, p, method = stats.mann_whitney([1, 2, 3], [4, 5, 6])
        self.assertEqual(method, "exact")
        self.assertAlmostEqual(p, 0.1)

    def test_mann_whitney_exact_with_ties(self):
        _, p, method = stats.mann_whitney([1, 2, 2], [2, 3, 4])
        self.assertEqual(method, "exact")
        self.assertAlmostEqual(p, 0.3)

    def test_mann_whitney_identical_samples(self):
        _, p, _ = stats.mann_whitney([5, 5, 5], [5, 5, 5])
        self.assertAlmostEqual(p, 1.0)

    def test_cliffs_delta(self):
        self.assertEqual(stats.cliffs_delta([4, 5, 6], [1, 2, 3]), 1.0)
        self.assertEqual(stats.cliffs_delta([1, 2, 3], [4, 5, 6]), -1.0)
        self.assertEqual(stats.cliffs_delta([1, 2], [1, 2]), 0.0)
        self.assertEqual(stats.cliffs_label(0.1), "negligible")
        self.assertEqual(stats.cliffs_label(-0.5), "large")


class CliTest(unittest.TestCase):
    def setUp(self):
        self.repo = TempRepo(scripts=["stats.py"])

    def tearDown(self):
        self.repo.cleanup()

    def test_plan_order_deterministic_and_blocked(self):
        args = ["plan-order", "--impls", "before,A,B", "--scenarios", "S1,F1", "--runs", "3", "--seed", "42"]
        r1 = self.repo.py("stats.py", *args, "--out", "o1.csv")
        r2 = self.repo.py("stats.py", *args, "--out", "o2.csv")
        self.assertEqual(r1.returncode, 0, r1.stderr)
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertEqual(self.repo.path("o1.csv").read_bytes(), self.repo.path("o2.csv").read_bytes())
        rows = self.repo.csv("o1.csv")
        self.assertEqual(len(rows), 2 * 3 * 3)
        blocks = {}
        for r in rows:
            blocks.setdefault((r["scenario"], r["block"]), []).append(r["impl"])
        for impls in blocks.values():  # every block runs every implementation exactly once
            self.assertEqual(sorted(impls), ["A", "B", "before"])

    def test_plan_order_refuses_overwrite(self):
        args = ["plan-order", "--impls", "before,A", "--scenarios", "S1", "--runs", "2", "--seed", "1", "--out", "o.csv"]
        self.assertEqual(self.repo.py("stats.py", *args).returncode, 0)
        self.assertNotEqual(self.repo.py("stats.py", *args).returncode, 0)
        self.assertEqual(self.repo.py("stats.py", *args, "--force").returncode, 0)

    def _write_long(self, shifts, runs=5, n=300, seed=7):
        rng = random.Random(seed)
        lines = ["impl,scenario,run,value"]
        for impl, factor in shifts.items():
            for run in range(1, runs + 1):
                run_noise = 1 + rng.gauss(0, 0.02)
                for _ in range(n):
                    lines.append(f"{impl},S1,{run},{rng.lognormvariate(3, 0.4) * factor * run_noise:.4f}")
        self.repo.write("long.csv", "\n".join(lines) + "\n")

    def test_compare_detects_worse_and_no_difference(self):
        self._write_long({"before": 1.0, "A": 1.25, "B": 1.0})
        s = self.repo.py("stats.py", "summarize", "--input", "long.csv", "--format", "long", "--resamples", "500",
                         "--out", "runs.csv")
        self.assertEqual(s.returncode, 0, s.stderr)
        c = self.repo.py("stats.py", "compare", "--summary", "runs.csv", "--metric", "p50", "--resamples", "1000",
                         "--out", "cmp.csv")
        self.assertEqual(c.returncode, 0, c.stderr)
        verdicts = {r["impl"]: r["verdict"] for r in self.repo.csv("cmp.csv")}
        self.assertEqual(verdicts["A"], "worse")
        self.assertIn(verdicts["B"], {"no detectable difference", "practically negligible"})

    def test_summarize_never_averages_percentiles(self):
        # Three runs with very different tails: median-of-run-p99 and pooled p99 both differ from the mean.
        values = {1: list(range(1, 101)), 2: list(range(1, 101)), 3: [v * 10 for v in range(1, 101)]}
        lines = ["impl,scenario,run,value"] + [f"before,S1,{run},{v}" for run, vs in values.items() for v in vs]
        self.repo.write("long.csv", "\n".join(lines) + "\n")
        s = self.repo.py("stats.py", "summarize", "--input", "long.csv", "--format", "long", "--resamples", "200",
                         "--out", "runs.csv")
        self.assertEqual(s.returncode, 0, s.stderr)
        g = self.repo.csv("runs.groups.csv")[0]
        run_p99 = [stats.percentile(sorted(vs), 99) for vs in values.values()]
        pooled = stats.percentile(sorted(v for vs in values.values() for v in vs), 99)
        self.assertAlmostEqual(float(g["p99_median"]), statistics.median(run_p99), places=3)
        self.assertAlmostEqual(float(g["pooled_p99"]), pooled, places=3)
        self.assertNotAlmostEqual(float(g["p99_median"]), statistics.mean(run_p99), places=1)


if __name__ == "__main__":
    unittest.main()
