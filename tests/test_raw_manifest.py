import gzip
import json
import unittest

from _helpers import TempRepo, load_module

raw_manifest = load_module("raw_manifest")

DIR = "topics/x/results/raw-samples"
NAME = "before-S1-1-20261021T101500Z.k6.csv"


class RawManifestTest(unittest.TestCase):
    def setUp(self):
        self.repo = TempRepo(scripts=["raw_manifest.py"])
        self.body = "metric_name,timestamp,metric_value\n" + "".join(
            f"http_req_duration,{1700000000 + i},{i}.5\n" for i in range(1000))
        self.repo.write(f"{DIR}/{NAME}", self.body)

    def tearDown(self):
        self.repo.cleanup()

    def manifest(self):
        return json.loads(self.repo.path(f"{DIR}/MANIFEST.json").read_text(encoding="utf-8"))

    def update(self, *extra):
        r = self.repo.py("raw_manifest.py", "update", DIR, *extra)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r

    def test_update_gzips_and_records(self):
        self.update("--cmd", "make run IMPL=before SCENARIO=S1 RUN=1")
        gz = self.repo.path(f"{DIR}/{NAME}.gz")
        self.assertFalse(self.repo.path(f"{DIR}/{NAME}").exists(), "plain CSV must be replaced by the gzip")
        self.assertEqual(gzip.decompress(gz.read_bytes()).decode(), self.body)
        [e] = self.manifest()["files"]
        self.assertEqual(e["name"], NAME + ".gz")
        self.assertEqual(e["rows"], 1000)
        self.assertEqual(e["bytes"], gz.stat().st_size)
        self.assertEqual(e["sha256"], raw_manifest.sha256(gz))
        self.assertEqual(e["testid"], "before-S1-1")
        self.assertEqual(e["command"], "make run IMPL=before SCENARIO=S1 RUN=1")
        self.assertRegex(e["created"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_update_is_idempotent_and_gzip_reproducible(self):
        self.update()
        first = self.repo.path(f"{DIR}/MANIFEST.json").read_bytes()
        self.update()
        self.assertEqual(self.repo.path(f"{DIR}/MANIFEST.json").read_bytes(), first)
        # gzip header carries no name/mtime, so the same CSV always gives the same sha256
        again = raw_manifest.gzip_file(self.repo.write("copy/other-name.csv", self.body))
        self.assertEqual(raw_manifest.sha256(again), self.manifest()["files"][0]["sha256"])

    def test_refuses_to_overwrite_existing_gzip(self):
        self.update()
        self.repo.write(f"{DIR}/{NAME}", self.body)  # same name produced again
        r = self.repo.py("raw_manifest.py", "update", DIR)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("refusing to overwrite", r.stderr)

    def test_verify_ok_missing_and_mismatch(self):
        self.update()
        ok = self.repo.py("raw_manifest.py", "verify", DIR)
        self.assertEqual(ok.returncode, 0, ok.stdout)
        gz = self.repo.path(f"{DIR}/{NAME}.gz")
        data = gz.read_bytes()
        gz.unlink()  # another machine: the manifest is committed, the sample is not
        missing = self.repo.py("raw_manifest.py", "verify", DIR)
        self.assertEqual(missing.returncode, 0, missing.stdout)
        self.assertIn("not present locally", missing.stdout)
        self.assertNotEqual(self.repo.py("raw_manifest.py", "verify", DIR, "--strict").returncode, 0)
        gz.write_bytes(data[:-1] + bytes([data[-1] ^ 1]))  # same size, different bytes
        bad = self.repo.py("raw_manifest.py", "verify", DIR)
        self.assertEqual(bad.returncode, 1)
        self.assertIn("MISMATCH", bad.stdout)

    def test_update_keeps_entries_of_absent_files(self):
        self.update()
        self.repo.path(f"{DIR}/{NAME}.gz").unlink()
        self.repo.write(f"{DIR}/a-S1-1-20261021T102000Z.k6.csv", "h\n1\n")
        self.update()
        names = [e["name"] for e in self.manifest()["files"]]
        self.assertEqual(names, ["a-S1-1-20261021T102000Z.k6.csv.gz", NAME + ".gz"])

    def test_verify_strict_flags_unlisted(self):
        self.update()
        self.repo.path(f"{DIR}/extra.csv.gz").write_bytes(gzip.compress(b"h\n"))
        self.assertEqual(self.repo.py("raw_manifest.py", "verify", DIR).returncode, 0)
        self.assertNotEqual(self.repo.py("raw_manifest.py", "verify", DIR, "--strict").returncode, 0)

    def test_count_rows_without_trailing_newline(self):
        p = self.repo.write("t.csv", "h\n1\n2")
        self.assertEqual(raw_manifest.count_rows(p), 2)


if __name__ == "__main__":
    unittest.main()
