import re
import unittest

from _helpers import TempRepo

RM = "hub/roadmap.html"  # scripts/_paths.py: hub_path("roadmap")

ROW = ('        <tr id="{slug}" data-slug="{slug}" data-track="{track}" data-prereq="{pre}" data-mode="full" '
       'data-priority="{prio}" data-status="planned" data-created="false">\n'
       '          <td><strong>{name}</strong><br><code>{slug}</code></td>\n'
       '          <td>x</td>\n'
       '        </tr>\n')

PAGE = """<!doctype html>
<html lang="vi"><head><title>t</title></head>
<body data-page="hub">
  <main><article class="doc">
  <header class="doc-header"><div class="meta"><span data-roadmap-total>—</span></div></header>
  <section>
    <h2 id="paths">Gợi ý thứ tự học</h2>
    <h3 id="path-1">Đường 1</h3>
    <p>x</p>
    <ol class="learning-path">{path}
    </ol>
  </section>

  <section>
    <h2 id="graph">Đồ thị tiền đề</h2>
    <h3 id="graph-overview">Tổng quan</h3>
    <figure class="diagram" data-roadmap="overview"></figure>
    <h3 id="graph-kafka">Messaging &amp; Kafka</h3>
    <figure class="diagram" data-roadmap="kafka" data-track-name="Messaging &amp; Kafka"></figure>
    <h3 id="graph-correctness">Nền tảng tính đúng đắn</h3>
    <figure class="diagram" data-roadmap="correctness" data-track-name="Nền tảng tính đúng đắn"></figure>
    <h3 id="graph-postgres">PostgreSQL</h3>
    <figure class="diagram" data-roadmap="postgres" data-track-name="PostgreSQL"></figure>
  </section>

  <section>
    <h2 id="topics">Danh sách topic</h2>
    <div class="table-wrap"><table class="roadmap">
      <thead><tr><th>Topic</th><th>Track</th></tr></thead>
      <tbody>
{rows}      </tbody>
    </table></div>
  </section>
  </article></main>
</body></html>
"""

# e (kafka, stage 3) is listed first and f (correctness, stage 1) depends on it -> "after stage 3" badge.
TOPICS = [
    ("e", "kafka", "", 1, "E kafka"),
    ("f", "correctness", "e", 1, "F needs E"),
    ("c", "postgres", "b", 1, "C needs B"),
    ("b", "correctness", "a", 2, "B needs A"),
    ("a", "correctness", "", 1, "A root"),
]


def page(topics=TOPICS, path=("a", "b")):
    rows = "".join(ROW.format(slug=s, track=t, pre=p, prio=pr, name=n) for s, t, p, pr, n in topics)
    items = "".join(f'\n        <li><a href="#{s}">{s}</a> — x</li>' for s in path)
    return PAGE.format(rows=rows, path=items)


def orders(html):
    return {m.group(1): int(m.group(2)) for m in re.finditer(r'<tr id="([^"]+)"[^>]*data-order="(\d+)"', html)}


class RoadmapOrderTest(unittest.TestCase):
    def setUp(self):
        self.repo = TempRepo(scripts=["roadmap_order.py"])

    def tearDown(self):
        self.repo.cleanup()

    def run_order(self, *args):
        return self.repo.py("roadmap_order.py", *args)

    def test_topological_order_respects_prerequisites(self):
        self.repo.write(RM, page())
        r = self.run_order()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        o = orders(self.repo.path(RM).read_text(encoding="utf-8"))
        self.assertEqual(sorted(o.values()), [1, 2, 3, 4, 5])
        self.assertLess(o["a"], o["b"])
        self.assertLess(o["b"], o["c"])
        self.assertLess(o["e"], o["f"])

    def test_idempotent_including_after_stage_badges(self):
        self.repo.write(RM, page())
        self.assertEqual(self.run_order().returncode, 0)
        first = self.repo.path(RM).read_bytes()
        self.assertEqual(self.run_order().returncode, 0)
        self.assertEqual(self.run_order().returncode, 0)
        third = self.repo.path(RM).read_bytes()
        self.assertEqual(first, third)
        html = third.decode("utf-8")
        # Regression: re-running once dropped both badges on rows that had an "after-stage" badge.
        self.assertEqual(html.count('class="order-no" title='), 5)
        self.assertEqual(html.count('class="after-stage"'), 1)
        self.assertRegex(html, r'<tr id="f"[^>]*data-after-stage="3"')
        self.assertNotIn("<td> <strong>", html)

    def test_group_header_rows_are_not_topics(self):
        self.repo.write(RM, page())
        self.assertEqual(self.run_order().returncode, 0)
        html = self.repo.path(RM).read_text(encoding="utf-8")
        self.assertEqual(html.count('class="track-group"'), 3)
        r = self.run_order("--check")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("ok: 5 topics", r.stdout)

    def test_cycle_exits_non_zero(self):
        cyc = [("a", "correctness", "b", 1, "A"), ("b", "correctness", "a", 1, "B")]
        self.repo.write(RM, page(cyc, path=()))
        r = self.run_order("--check")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("cycle", r.stdout)

    def test_unknown_prerequisite_exits_non_zero(self):
        bad = [("a", "correctness", "ghost", 1, "A")]
        self.repo.write(RM, page(bad, path=()))
        r = self.run_order("--check")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unknown prerequisite ghost", r.stdout)

    def test_learning_path_out_of_order_is_flagged(self):
        self.repo.write(RM, page(path=("b", "a")))
        r = self.run_order("--check")
        self.assertIn("path-1: b comes before its prerequisites ['a']", r.stdout)
        self.assertIn("learning-path order problems: 1", r.stdout)


if __name__ == "__main__":
    unittest.main()
