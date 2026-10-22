"""scripts/new-topic.sh on a temporary copy of the repo skeleton."""
import re
import subprocess
import unittest

from _helpers import ENV, REPO, TempRepo, find_bash

BASH = find_bash()
TOKENS = re.compile(r"\{\{(SLUG|PKG|TOPIC|DATE)\}\}")


@unittest.skipIf(BASH is None, "bash not found (set LAB_BASH)")
class NewTopicTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = TempRepo(scripts=["new-topic.sh"], copy_paths=["templates", "shared/scaffold", "README.md"])

    @classmethod
    def tearDownClass(cls):
        cls.repo.cleanup()

    def run_script(self, slug):
        return subprocess.run([BASH, "scripts/new-topic.sh", slug], cwd=self.repo.dir, env=ENV,
                              capture_output=True, text=True, encoding="utf-8")

    def test_01_creates_topic_from_templates_and_scaffold(self):
        r = self.run_script("demo-topic")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        t = self.repo.path("topics/demo-topic")
        for rel in ["README.html", "01-research.html", "07-production.html", "results/env.md",
                    "system/pom.xml", "experiments/Makefile", "results/raw/.gitkeep", "deploy/.gitkeep"]:
            self.assertTrue((t / rel).exists(), rel)
        # package directory renamed from __PKG__ to the slug without dashes
        self.assertTrue((t / "system/src/main/java/lab/demotopic").is_dir())
        self.assertFalse(list(t.rglob("__PKG__")))

    def test_02_no_placeholders_left_and_go_templates_kept(self):
        t = self.repo.path("topics/demo-topic")
        leftovers = []
        for f in t.rglob("*"):
            if f.is_file() and f.suffix in {".html", ".md", ".xml", ".yml", ".yaml", ".java", ".sql", ".js", ".py", ".sh"} \
                    or f.name in {"Makefile", "Dockerfile", ".env"}:
                if TOKENS.search(f.read_text(encoding="utf-8", errors="replace")):
                    leftovers.append(str(f.relative_to(t)))
        self.assertEqual(leftovers, [])
        makefile = (t / "experiments/Makefile").read_text(encoding="utf-8")
        self.assertIn("{{.Server.Version}}", makefile)
        self.assertIn('"../../shared/docs/lab.css"', (t / "01-research.html").read_text(encoding="utf-8"))
        self.assertIn("<artifactId>demo-topic</artifactId>", (t / "system/pom.xml").read_text(encoding="utf-8"))

    def test_02b_question_pages_rendered(self):
        t = self.repo.path("topics/demo-topic")
        for name, title in (("questions.html", "Hỏi đáp"), ("suggested-questions.html", "Câu hỏi nên hỏi")):
            with self.subTest(name):
                html = (t / name).read_text(encoding="utf-8")
                self.assertIsNone(TOKENS.search(html))
                self.assertIn(f"<title>Demo Topic — {title}</title>", html)
                self.assertIn("<code>demo-topic</code>", html)
                self.assertIn('"../../shared/docs/lab.css"', html)
                self.assertIn('"../../shared/docs/lab.js"', html)
                self.assertNotIn('"../shared/', html)
        self.assertIn('<section id="qa-log">', (t / "questions.html").read_text(encoding="utf-8"))
        self.assertIn('<section id="ask-list">', (t / "suggested-questions.html").read_text(encoding="utf-8"))

    def test_03_readme_row_added(self):
        readme = self.repo.path("README.md").read_text(encoding="utf-8")
        self.assertIn("| demo-topic | 0 — chưa bắt đầu | [README](topics/demo-topic/README.html) |", readme)
        self.assertLess(readme.index("demo-topic"), readme.index("<!-- topics:end -->"))

    def test_04_rejects_bad_and_duplicate_slugs(self):
        for bad in ("Bad_Slug", "-lead", "trail-", "a--b", ""):
            with self.subTest(bad):
                self.assertNotEqual(self.run_script(bad).returncode, 0)
        self.assertNotEqual(self.run_script("demo-topic").returncode, 0)

    def test_05_original_repo_untouched(self):
        self.assertNotIn("demo-topic", (REPO / "README.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
