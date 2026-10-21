"""prom_export.py: pure helpers (no network) and overwrite refusal."""
import argparse
import unittest
from datetime import datetime, timezone

from _helpers import TempRepo, load_module

pe = load_module("prom_export")
NOW = datetime(2026, 10, 21, 12, 0, 0, tzinfo=timezone.utc).timestamp()


class TimeParsingTest(unittest.TestCase):
    def test_relative_now_unix_and_rfc3339(self):
        self.assertEqual(pe.parse_time("now", NOW), NOW)
        self.assertEqual(pe.parse_time("-15m", NOW), NOW - 900)
        self.assertEqual(pe.parse_time("-1h", NOW), NOW - 3600)
        self.assertEqual(pe.parse_time("1792584000", NOW), 1792584000.0)
        self.assertEqual(pe.parse_time("2026-10-21T12:00:00Z", NOW), NOW)
        self.assertEqual(pe.parse_time("2026-10-21T14:00:00+02:00", NOW), NOW)

    def test_naive_rfc3339_is_utc(self):
        self.assertEqual(pe.parse_time("2026-10-21T12:00:00", NOW), NOW)

    def test_invalid_inputs_raise(self):
        for bad in ("yesterday", "-15x", "2026-13-40"):
            with self.subTest(bad):
                with self.assertRaises(argparse.ArgumentTypeError):
                    pe.parse_time(bad, NOW)

    def test_durations(self):
        self.assertEqual(pe.parse_duration("500ms"), 0.5)
        self.assertEqual(pe.parse_duration("5s"), 5)
        self.assertEqual(pe.fmt_duration(30.0), "30s")
        self.assertEqual(pe.fmt_duration(0.25), "250ms")


class PresetRenderingTest(unittest.TestCase):
    def test_label_injection_into_selector(self):
        sel = pe.build_selector(["compose_project=obs-test", 'note=a"b'])
        self.assertEqual(sel, 'compose_project="obs-test",note="a\\"b"')
        q = pe.render('rate(x_total{__SEL__}[__RANGE__])', sel, "30s")
        self.assertEqual(q, 'rate(x_total{compose_project="obs-test",note="a\\"b"}[30s])')

    def test_no_labels_leaves_valid_selector(self):
        self.assertEqual(pe.render('up{job="a",__SEL__}', "", "30s"), 'up{job="a"}')
        self.assertEqual(pe.render("up{__SEL__}", "", "30s"), "up{}")

    def test_every_preset_renders_without_placeholders(self):
        sel = pe.build_selector(["compose_project=p"])
        for preset, queries in pe.PRESETS.items():
            for name, tpl in queries.items():
                with self.subTest(f"{preset}.{name}"):
                    q = pe.render(tpl, sel, "30s")
                    self.assertNotIn("__SEL__", q)
                    self.assertNotIn("__RANGE__", q)

    def test_bad_label_rejected(self):
        for bad in ("novalue", "1bad=x", "has space=x"):
            with self.subTest(bad):
                with self.assertRaises(argparse.ArgumentTypeError):
                    pe.build_selector([bad])


class OverwriteRefusalTest(unittest.TestCase):
    def test_existing_output_is_not_overwritten_without_force(self):
        repo = TempRepo(scripts=["prom_export.py"])
        try:
            repo.write("out.csv", "keep me\n")
            # Unreachable Prometheus: refusal must happen before any network access.
            r = repo.py("prom_export.py", "--prom", "http://127.0.0.1:9", "--start", "-5m",
                        "--query", "u=up", "--out", "out.csv")
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertEqual(repo.path("out.csv").read_text(encoding="utf-8"), "keep me\n")
        finally:
            repo.cleanup()


if __name__ == "__main__":
    unittest.main()
