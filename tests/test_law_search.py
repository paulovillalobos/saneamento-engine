"""«Pergunte à lei»: the code's answer to six técnico questions, and the checker that gates the reader's pick."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine import law_search as LS  # noqa: E402

L = LS.law()


class Search(unittest.TestCase):
    def top(self, q):
        return L.search(q)[0]

    def test_six_questions(self):
        cases = [("preciso de projeto de gás numa moradia?", "anexo-V.27.i.iv", "condicional"),
                 ("o levantamento topográfico é sempre obrigatório?", "anexo-V.7", "condicional"),
                 ("fotografias do terreno", "anexo-V.15", "condicional"),
                 ("a planta de implantação tem de ir em dwg?", "anexo-VI.1.b", "—"),
                 ("quando é que preciso de pareceres de entidades externas", None, None),
                 ("prazo para o convite ao aperfeiçoamento", None, None)]
        for q, path, exig in cases:
            cands = L.search(q)
            self.assertTrue(cands, q)
            if path:
                self.assertEqual(L.p[cands[0]["id"]]["path"], path, q)
                self.assertEqual(cands[0]["exigido"], exig, q)
        self.assertTrue(any("art13-B" in c["id"] or c["id"].endswith("anexo-V.27.h") for c in L.search("quando é que preciso de pareceres de entidades externas")[:3]))
        self.assertTrue(any("art11" in c["id"] for c in L.search("prazo para o convite ao aperfeiçoamento")[:3]))

    def test_other_list_is_not_required(self):
        c = next(c for c in L.search("projeto de instalação de gás") if L.p[c["id"]]["path"] == "anexo-V.26.a.iv")
        self.assertEqual(c["exigido"], "nao")

    def test_prompt_and_check(self):
        q = "preciso de projeto de gás?"
        cands = L.search(q)
        prompt = L.prompt(q, cands)
        self.assertTrue(prompt.startswith(LS.HEAD))
        self.assertIn(cands[0]["id"], prompt)
        good = json.dumps({"exigido": "sempre", "condicao": "", "passagem": cands[0]["id"], "citacao": cands[0]["text"]}, ensure_ascii=False)
        pick, why = L.check(good, cands)
        self.assertEqual(pick["id"], cands[0]["id"])
        self.assertIsNone(why)
        self.assertEqual(L.check(json.dumps({"passagem": "portaria-320-2026-1:anexo-V.1", "citacao": "x"}), cands)[0], None)
        self.assertEqual(L.check(json.dumps({"passagem": cands[0]["id"], "citacao": cands[0]["text"] + " e mais"}), cands)[0], None)
        self.assertEqual(L.check('{"resposta": "nao_sei"}', cands)[1], "o leitor diz não saber")
        self.assertEqual(L.check("not json", cands)[1], "não é JSON")

    def test_scope_and_labels(self):
        self.assertTrue(L.in_scope("portaria-320-2026-1:anexo-V.27.a", "CP/CPEDI"))
        self.assertFalse(L.in_scope("portaria-320-2026-1:anexo-V.26.a.iv", "CP/CPEDI"))
        self.assertEqual(LS.label_of("anexo-V.27.i.iv"), "Anexo V, n.º 27, alínea i), subalínea iv)")
        self.assertGreater(len(L.p), 600)


if __name__ == "__main__":
    unittest.main()
