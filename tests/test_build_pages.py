"""scripts/build_pages.py: README.md → index.html, CLAUDE.md → hub/rules.html (Markdown subset)."""
import re
import unittest

from _helpers import TempRepo

README = """# backend-lab

Giới thiệu `code *not em*` và **đậm**, xem [quy tắc](CLAUDE.md#mục-tiêu-học--nơi-trả-lời).

## Cách dùng

- Mục một
  - Mục con
- Mục hai [home](README.md)

| A | B |
|---|---|
| 1 | `x` |

```bash
echo "<tag>"
```

<!-- topics:start -->
| Topic | Link |
|---|---|
<!-- topics:end -->
"""

CLAUDE = """# Quy tắc

## Mục tiêu học → nơi trả lời

Xem [README](README.md) và [đồ thị](CLAUDE.md#Đồ-thị), tài liệu [ngoài](https://example.com/a#b).

### Đồ thị

1. một
2. hai
"""

RULE = """---
paths:
  - "topics/**/*.html"
---

## Quy tắc chi tiết

- chỉ nạp khi cần
"""


class BuildPagesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = TempRepo(scripts=["build_pages.py"])
        cls.repo.write("README.md", README)
        cls.repo.write("CLAUDE.md", CLAUDE)
        cls.repo.write(".claude/rules/detail.md", RULE)
        r = cls.repo.py("build_pages.py")
        assert r.returncode == 0, r.stdout + r.stderr
        cls.index = cls.repo.path("index.html").read_text(encoding="utf-8")
        cls.rules = cls.repo.path("hub/rules.html").read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.repo.cleanup()

    def test_headings_get_ids_without_diacritics(self):
        self.assertIn('<h2 id="cach-dung">Cách dùng</h2>', self.index)
        self.assertIn('<h2 id="muc-tieu-hoc-noi-tra-loi">', self.rules)
        self.assertIn('<h3 id="do-thi">Đồ thị</h3>', self.rules)
        self.assertIn("<h1>backend-lab</h1>", self.index)  # first H1 becomes the page title, not a section

    def test_tables_lists_and_code(self):
        self.assertIn("<th>A</th><th>B</th>", self.index)
        self.assertIn("<td>1</td><td><code>x</code></td>", self.index)
        self.assertRegex(self.index, r"<ul><li>Mục một<ul><li>Mục con</li></ul></li><li>Mục hai ")
        self.assertIn("<ol><li>một</li><li>hai</li></ol>", self.rules)
        self.assertIn('<pre><code class="language-bash">echo "&lt;tag&gt;"</code></pre>', self.index)
        self.assertIn("<code>code *not em*</code>", self.index)  # nothing formatted inside code spans
        self.assertIn("<strong>đậm</strong>", self.index)

    def test_html_comments_are_hidden(self):
        self.assertNotIn("topics:start", self.index)

    def test_links_are_rewritten_per_page_location(self):
        self.assertIn('href="hub/rules.html#muc-tieu-hoc-noi-tra-loi"', self.index)   # CLAUDE.md#… from root
        self.assertIn('<a href="index.html">home</a>', self.index)                      # README.md from root
        self.assertIn('<a href="../index.html">README</a>', self.rules)                 # README.md from hub/
        self.assertIn('<a href="rules.html#do-thi">', self.rules)                       # CLAUDE.md#… inside hub/
        self.assertIn('href="https://example.com/a#b"', self.rules)                     # external left alone

    def test_assets_resolve_from_each_location(self):
        self.assertIn('href="shared/docs/lab.css"', self.index)
        self.assertIn('href="../shared/docs/lab.css"', self.rules)
        self.assertNotRegex(self.index + self.rules, r'href="[^"]*(?:README|CLAUDE)\.md')

    def test_check_detects_stale_output(self):
        self.assertEqual(self.repo.py("build_pages.py", "--check").returncode, 0)
        self.repo.write("README.md", README + "\nThêm một dòng.\n")
        try:
            r = self.repo.py("build_pages.py", "--check")
            self.assertEqual(r.returncode, 1)
            self.assertIn("index.html", r.stdout)
            self.assertNotIn("hub/rules.html", r.stdout)
            # --check never writes
            self.assertEqual(self.repo.path("index.html").read_text(encoding="utf-8"), self.index)
        finally:
            self.repo.write("README.md", README)

    def test_rules_files_appended_to_rules_page_without_front_matter(self):
        self.assertIn('<h2 id="quy-tac-chi-tiet">Quy tắc chi tiết</h2>', self.rules)
        self.assertIn("chỉ nạp khi cần", self.rules)
        self.assertNotIn("paths:", self.rules)
        self.assertNotIn("Quy tắc chi tiết", self.index)


if __name__ == "__main__":
    unittest.main()
