"""The verdict layer's tests (stdlib unittest):   python3 -I -m unittest discover -s tests -v

Unit rules (numbers, dates, the quote-names-the-fact rule, the declarant, the signing certificate) and the two acceptance sets
replayed from the stored reader answers: the exam (11/11, 0 false alarms, 9/9 honest) and the sealed expedientes (55/55, 0, 20/20).
A change that moves any of those numbers fails here before it reaches a commit (tools/check.sh).
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine import application as A  # noqa: E402

EXAM = ROOT / "exam"


class Rules(unittest.TestCase):
    def test_number_words_and_formats(self):
        self.assertEqual(A.number("dois"), 2)
        self.assertEqual(A.number("um fogo"), None)  # a sentence is not a number word; the value the reader gives is the token itself
        self.assertEqual(A.number("1.200"), 1200)
        self.assertEqual(A.number("320 000,00 €"), 320000)
        self.assertEqual(A.number("7,2"), 7.2)
        self.assertEqual(A.number("554 m2"), 554)
        self.assertIsNone(A.number("sem valor"))

    def test_dates(self):
        self.assertEqual(A.iso_date("2026-09-30"), "2026-09-30")
        self.assertEqual(A.iso_date("30/09/2026"), "2026-09-30")
        self.assertEqual(A.iso_date("31 de dezembro de 2026"), "2026-12-31")
        self.assertIsNone(A.iso_date("até ao fim da obra"))

    def test_quote_must_name_the_fact(self):
        q = "Quadro sinóptico: superfície do terreno 1200 m2; área da parcela 1200 m2; área de implantação de 277 m2"
        self.assertFalse(A.names_fact("area_implantacao", "1200", q))
        self.assertTrue(A.names_fact("area_implantacao", "277", q))
        self.assertTrue(A.names_fact("area_parcela", "1200", q))
        self.assertTrue(A.names_fact("pisos_acima_soleira", "dois", "A edificação desenvolve-se em dois pisos acima da cota de soleira"))

    def test_declarant(self):
        pages = ["Termo de responsabilidade\nOlga Exemplo Vasco, com domicílio em Caminho da Lameira, n.º 45, declara que"]
        self.assertEqual(A.declarant_of(pages), "Olga Exemplo Vasco")
        self.assertEqual(A.declarant_of(["Eu, Tiago Simulado, arquiteto, com domicílio em X"]), "Tiago Simulado")
        self.assertIsNone(A.declarant_of(["Estimativa do custo total da obra: 320 000 €"]))

    def test_signer_certificate(self):
        pdf = (EXAM / "dossiers" / "A" / "TRPARQ-termo-arquitetura.pdf").read_bytes()
        s = A.signer_of(pdf)
        self.assertIsNotNone(s)
        self.assertIn("Simulado", s["cn"])
        self.assertEqual(len(s["sha256"]), 16)
        self.assertIsNone(A.signer_of(b"%PDF-1.4 no signature here"))


class Exam(unittest.TestCase):
    """exam/score.py's own matching over check(), replayed from engine/reads (no GPU)."""

    def score(self, name):
        sys.path.insert(0, str(EXAM))
        import score as S  # noqa: E402
        answers = json.loads((EXAM / "answers.json").read_text(encoding="utf-8"))
        return S.score_dossier(answers["dossiers"][name], A.check(EXAM / "dossiers" / name))

    def test_exam_abc(self):
        total = {"found": 0, "expected": 0, "false_alarms": 0, "honest": 0, "honesty_items": 0}
        for name in "ABC":
            r = self.score(name)
            self.assertTrue(r["ran"])
            for k in total:
                total[k] += r[k]
        self.assertEqual((total["found"], total["expected"]), (11, 11), total)
        self.assertEqual(total["false_alarms"], 0, total)
        self.assertEqual((total["honest"], total["honesty_items"]), (9, 9), total)

    def test_reads_present(self):
        for name in "ABC":
            self.assertIsNotNone(A.load_reads(EXAM / "dossiers" / name), f"engine/reads for dossier {name} missing")


class Sealed(unittest.TestCase):
    def test_sealed_55(self):
        from engine import score_sealed as S
        folders = sorted(p for p in (ROOT / "sealed" / "expedientes").iterdir() if p.is_dir() and (p / "key.json").exists())
        if len(folders) < 20 or not all(any(p.suffix == ".pdf" for p in f.iterdir()) for f in folders):
            self.skipTest("sealed PDFs not on this machine (gitignored)")
        rows = [S.score_one(f) for f in folders]
        found, expected = sum(r["found"] for r in rows), sum(r["expected"] for r in rows)
        alarms = sum(len(r["false_alarms"]) for r in rows)
        self.assertEqual((found, expected), (55, 55), [r for r in rows if r["missed"]])
        self.assertEqual(alarms, 0, [r["false_alarms"] for r in rows if r["false_alarms"]])
        self.assertEqual(sum(r["honest"] for r in rows), 20)


class Verdict(unittest.TestCase):
    def test_shape_and_files(self):
        v = A.verdict(EXAM / "dossiers" / "C")
        for k in ("findings", "not_assessed", "provisional", "review", "not_read", "absent", "elements", "facts", "files", "counts"):
            self.assertIn(k, v)
        self.assertEqual(v["counts"]["finding"], len(v["findings"]))
        self.assertTrue(all(f.get("law") or f["type"] in ("value_mismatch", "impossible_value") for f in v["findings"]), "every finding carries the law or a fact comparison")
        html = A.page(v)
        self.assertIn("Deficiências", html)
        text = A.convite(v)
        self.assertIn("Convite ao aperfeiçoamento", text)
        self.assertEqual(text.count("\n1. "), 1)

    def test_table_is_the_source(self):
        self.assertIn("V.27.g", A.TABLE["elements"])
        self.assertEqual(A.WORDS["dois"], 2)
        self.assertEqual(A.MONTHS["dezembro"], 12)
        self.assertIn("fogos", A.KEYWORD)


if __name__ == "__main__":
    unittest.main()
