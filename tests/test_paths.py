"""scripts/_paths.py: hub page locations and hubify() link rewriting for pages that live in hub/."""
import unittest

from _helpers import load_module

paths = load_module("_paths")


class HubPathTest(unittest.TestCase):
    def test_hub_pages_are_lowercase_files_in_hub(self):
        for key in ("lab", "roadmap", "problems", "insights", "benchmarks", "glossary", "rules"):
            p = paths.hub_path(key)
            self.assertEqual(p.parent.name, "hub")
            self.assertEqual(p.name, p.name.lower())
            self.assertEqual(p.name, f"{key}.html")


class HubifyTest(unittest.TestCase):
    def test_root_relative_links_get_parent_prefix(self):
        cases = {
            '<link href="shared/docs/lab.css">': '<link href="../shared/docs/lab.css">',
            '<script src="shared/docs/lab.js"></script>': '<script src="../shared/docs/lab.js"></script>',
            '<a href="topics/x/README.html">': '<a href="../topics/x/README.html">',
            '<a href="templates/01-research.html">': '<a href="../templates/01-research.html">',
            '<a href="index.html">': '<a href="../index.html">',
        }
        for src, want in cases.items():
            with self.subTest(src):
                self.assertEqual(paths.hubify(src), want)

    def test_legacy_uppercase_hub_names_become_lowercase_siblings(self):
        self.assertEqual(paths.hubify('<a href="ROADMAP.html#idempotency-key">'),
                         '<a href="roadmap.html#idempotency-key">')
        for old, new in paths.LEGACY.items():
            with self.subTest(old):
                self.assertEqual(paths.hubify(f'<a href="{old}">'), f'<a href="{new}">')

    def test_external_fragment_mailto_and_parent_links_untouched(self):
        for html in ('<a href="https://example.com/shared/x">', '<a href="http://h/topics/a">',
                     '<a href="#topics">', '<a href="mailto:a@b.c">', '<a href="../shared/docs/lab.css">',
                     '<a href="../topics/x/README.html">', '<a href="roadmap.html#a">',
                     '<p>shared/docs và topics/ trong văn bản</p>'):
            with self.subTest(html):
                self.assertEqual(paths.hubify(html), html)

    def test_idempotent(self):
        page = ('<link href="shared/docs/lab.css"><a href="topics/a/README.html">a</a><a href="LAB.html">l</a>'
                '<a href="index.html">i</a><a href="https://x/shared/">e</a><a href="#s">s</a>')
        once = paths.hubify(page)
        self.assertEqual(paths.hubify(once), once)
        self.assertNotIn("../../", once)


if __name__ == "__main__":
    unittest.main()
