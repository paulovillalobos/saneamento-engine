"""The service's pure parts: ids, the zip intake, the listing, the work state, the shared hourly budget."""
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine import web  # noqa: E402

STATES = [("novo", "Novo"), ("em_analise", "Em análise")]


def zip_of(entries):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in entries:
            z.writestr(name, data)
    return buf.getvalue()


class Web(unittest.TestCase):
    def test_ids(self):
        i = web.new_id("x")
        self.assertEqual(web.safe_id(i), i)
        self.assertIsNone(web.safe_id("../etc/passwd"))
        self.assertIsNone(web.safe_id(""))
        self.assertIsNone(web.safe_id(None))

    def test_unzip_flattens_and_filters(self):
        with tempfile.TemporaryDirectory() as d:
            n = web.unzip_to(zip_of([("folder/REQ-requerimento.pdf", b"%PDF"), ("__MACOSX/._x.pdf", b"x"), (".hidden.pdf", b"x"), ("sub/dir/", b""), ("bad|name.pdf", b"x")]), Path(d) / "files")
            self.assertEqual(n, 1)
            self.assertEqual(sorted(p.name for p in (Path(d) / "files").iterdir()), ["REQ-requerimento.pdf"])
            with self.assertRaises(zipfile.BadZipFile):
                web.unzip_to(b"not a zip", Path(d) / "x")

    def test_listing_and_status(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "20260101-000001-aaaaaa").mkdir()
            (root / "20260101-000001-aaaaaa" / "meta.json").write_text(json.dumps({"id": "20260101-000001-aaaaaa", "label": "A", "at": "2026-01-01T00:00:01", "files": 3, "counts": {"finding": 2}}))
            (root / "20260101-000002-bbbbbb").mkdir()
            (root / "20260101-000002-bbbbbb" / "pending.json").write_text(json.dumps({"label": "B", "at": "2026-01-01T00:00:02"}))
            (root / "20260101-000003-cccccc").mkdir()
            (root / "20260101-000003-cccccc" / "error.json").write_text(json.dumps({"erro": "boom", "at": "2026-01-01T00:00:03"}))
            rows = web.listing(root)
            self.assertEqual([r["id"] for r in rows], ["20260101-000003-cccccc", "20260101-000002-bbbbbb", "20260101-000001-aaaaaa"])
            self.assertEqual(rows[1]["estado"], "a_processar")
            (root / "20260101-000001-aaaaaa" / "meta.json").write_text(json.dumps({"id": "20260101-000001-aaaaaa", "label": "A", "at": "2026-01-01T00:00:01", "files": 3, "counts": {"finding": 2}, "estado": "saneado"}))
            st = web.status_of(root / "20260101-000001-aaaaaa")
            self.assertEqual((st["estado"], st["trabalho"]), ("pronto", "saneado"))
            self.assertEqual(web.status_of(root / "20260101-000002-bbbbbb")["estado"], "a processar")
            self.assertEqual(web.status_of(root / "20260101-000003-cccccc")["estado"], "erro")
            self.assertIsNone(web.status_of(root / "nope"))
            self.assertEqual(web.listing(root / "nope"), [])

    def test_work_state(self):
        with tempfile.TemporaryDirectory() as d:
            m = Path(d) / "meta.json"
            m.write_text(json.dumps({"id": "x"}))
            meta = web.set_work(m, {"estado": "em_analise", "responsavel": "Ana"}, STATES)
            self.assertEqual((meta["estado"], meta["responsavel"]), ("em_analise", "Ana"))
            self.assertEqual(len(meta["historico"]), 1)
            with self.assertRaises(ValueError):
                web.set_work(m, {"estado": "xx"}, STATES)
            self.assertEqual(json.loads(m.read_text())["estado"], "em_analise")

    def test_budget_is_shared_per_hour(self):
        with tempfile.TemporaryDirectory() as d:
            now = 3600 * 1000
            self.assertTrue(web.take_budget(d, 2, now))
            self.assertTrue(web.take_budget(d, 2, now))
            self.assertFalse(web.take_budget(d, 2, now))
            self.assertTrue(web.take_budget(d, 2, now + 3600))


if __name__ == "__main__":
    unittest.main()
