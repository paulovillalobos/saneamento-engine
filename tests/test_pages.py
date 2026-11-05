"""The screens render from their static files with every placeholder filled, inline previews included."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine import ui  # noqa: E402


class Pages(unittest.TestCase):
    def test_lei(self):
        h = ui.lei()
        self.assertIn("const INLINE=null;", h)
        self.assertIn("Pergunte à lei", h)
        self.assertNotIn("__", h.split("<script>")[0].replace("__proto__", ""))
        h2 = ui.lei(inline={"pergunta": "x", "passagens": [], "escolhida": None, "leitor": None})
        self.assertIn('"pergunta": "x"', h2)

    def test_app(self):
        h = ui.app(pdf_base="C/", back="../inbox.html")
        self.assertIn('const PDF="C/"', h)
        self.assertIn('href="../inbox.html"', h)
        self.assertIn("Pré-visualização do documento", h)
        v = json.loads((ROOT / "engine" / "verdicts" / "dossiers-C" / "verdict.json").read_text(encoding="utf-8"))
        h2 = ui.app(inline={"verdict": v, "convite": "c"})
        self.assertIn("const INLINE={", h2)

    def test_inbox(self):
        h = ui.inbox()
        self.assertIn("const INLINE=null;", h)
        self.assertIn('"novo"', h)
        h2 = ui.inbox(rows=[{"id": "20260101-000000-abcdef", "label": "x", "at": "2026-01-01T00:00:00", "files": 3, "counts": {"finding": 1, "not_assessed": 0}}], municipality="m")
        self.assertIn('"municipio": "m"', h2)

    def test_css_inlined_and_no_grey_text(self):
        css = (ROOT / "engine" / "static" / "app.css").read_text(encoding="utf-8")
        self.assertIn(".bp5-text-muted", css)
        self.assertIn("font:500", css)
        self.assertIn(css[:40], ui.lei())

    def test_missing_placeholder_is_an_error(self):
        with self.assertRaises(ValueError):
            ui.render("app.html", __DATA__="null")  # __PDF_BASE__ and __BACK__ left unfilled


if __name__ == "__main__":
    unittest.main()
