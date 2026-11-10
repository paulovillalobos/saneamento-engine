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
        c = L.card("portaria-320-2026-1:anexo-V.26.a.iv")   # another procedure's list: ranked down in search since 2026-11-10, still «não» when shown
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



class PlainQuestions(unittest.TestCase):
    """Ten questions in a person's words (2026-11-10 audit of lei.foaap.app: 4/10 right before the fix). The top passage must be
    one of the accepted ones, and an element of the CPEDI list must never be called «não exigido»."""
    CASES = [("o seguro do arquiteto é obrigatório?", {"anexo-V.14"}),
             ("preciso de licença para fazer um muro?", {"anexo.art6-A.1.b"}),
             ("quanto tempo a câmara tem para responder?", {"anexo.art11.2", "anexo.art11.5", "anexo.art23.1", "anexo.art23.1.a", "anexo.art20.3.a", "anexo.art35.10"}),
             ("preciso de projeto de gás numa moradia?", {"anexo-V.27.i.iv"}),
             ("o que tenho de entregar para construir uma casa?", {"anexo-V.27"}),
             ("preciso de levantamento topográfico?", {"anexo-V.7", "anexo-V.8"}),
             ("a estimativa de custo da obra é obrigatória?", {"anexo-V.27.f"}),
             ("posso entregar as plantas em pdf?", {"anexo-VI.1.a"}),
             ("termo de responsabilidade do diretor de obra", {"anexo-V.27.k"}),
             ("fotografias do terreno", {"anexo-V.15"})]

    def test_ten(self):
        for q, want in self.CASES:
            top = L.search(q)[0]
            self.assertIn(L.p[top["id"]]["path"], want, q)

    def test_estimate_is_required(self):
        top = L.search("a estimativa de custo da obra é obrigatória?")[0]
        self.assertEqual(top["exigido"], "sempre")

    def test_specialty_projects_inherit_the_group_condition(self):
        top = L.search("o projeto de eletricidade é obrigatório?")[0]
        self.assertEqual((top["exigido"], top["condicao"]), ("condicional", "em função do tipo de obra a executar"))


if __name__ == "__main__":
    unittest.main()
