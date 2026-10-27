"""The stranger test: real public documents nobody in this repo wrote, with keys written by hand (generator/stranger.py KEYS).
D1 rows (which element is this file, against the CPEDI shortlist) and D2 rows (a fact with its page, or null when absent).

    .venv-of-rjue/bin/python -I generator/stranger.py     # -> sealed/stranger-test.jsonl
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.argv = ["x"]
import importlib.util  # noqa: E402
spec = importlib.util.spec_from_file_location("d1d2", ROOT / "generator" / "d1d2.py"); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
from pypdf import PdfReader  # noqa: E402

R = "sources/real"
V9, V11, V12 = "portaria-320-2026-1:anexo-V.9", "portaria-320-2026-1:anexo-V.11", "portaria-320-2026-1:anexo-V.12"
# (file, D1 element or None, D1 tipo, [D2 (field, value or None)], note)
KEYS = [
    (f"{R}/memorias/valongo_74l2023_md.pdf", V9, "escrito", [("area_parcela", "49 977,00 m2"), ("custo_total", None)], "real memória descritiva e justificativa (loteamento, Valongo 2025)"),
    (f"{R}/memorias/cascais_md_loteamento_1145.pdf", V9, "escrito", [("validade_seguro_fim", None)], "real memória descritiva (Cascais DLOT, alvará 1145)"),
    (f"{R}/memorias/cascais_md_loteamento_1032.pdf", V9, "escrito", [], "real memória descritiva (Cascais DLOT, alvará 1032)"),
    (f"{R}/memorias/cascais_md_loteamento_1037.pdf", V9, "escrito", [], "real memória descritiva (Cascais DLOT, alvará 1037)"),
    (f"{R}/modelos/OA_TR_autor_projeto.pdf", V11, "escrito", [("wording_annex_vii", "Observa as normas legais e regulamentares aplicáveis, designadamente as normas técnicas de construção em vigor"), ("area_total_construcao", None)],
     "Ordem dos Arquitectos minuta, termo do autor do projeto (71-A wording)"),
    (f"{R}/modelos/OA_TR_coordenador.pdf", V12, "escrito", [("apolice", None)], "Ordem dos Arquitectos minuta, termo do coordenador"),
    (f"{R}/modelos/macedo_fichas_CP_edificacao.pdf", None, "nao_e_elemento", [("custo_total", None)], "a municipal checklist form, not an element"),
    (f"{R}/modelos/OA_analise_portaria.pdf", None, "nao_e_elemento", [], "an analysis of the Portaria, not an element"),
    (f"{R}/normas/alcacer_lista_elementos_nomeacao_ficheiros_2026.pdf", None, "nao_e_elemento", [], "a municipal file-naming list"),
    (f"{R}/normas/torresvedras_regulamento_instrucao_digital.pdf", None, "nao_e_elemento", [], "a municipal regulation"),
    (f"{R}/normas/torresvedras_manual_construtor_eurb2023.pdf", None, "nao_e_elemento", [], "a platform manual"),
]


def rid(*parts):
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def main():
    rows = []
    for path, elem, tipo, facts, note in KEYS:
        r = PdfReader(str(ROOT / path)); pages = [(p.extract_text() or "").strip() for p in r.pages]
        text = "\n".join(f"[página {i + 1}]\n{t}" for i, t in enumerate(pages))[:M.MAXCH]
        name = Path(path).name
        ans = {"elemento": elem, "citacao": M.PORT[elem]["text"] if elem else "", "tipo": tipo}
        rows.append({"id": f"d1:{rid('stranger', name)}", "task": "d1_elemento", "prompt": M.D1_PROMPT.format(shortlist=M.SHORTLIST, name=name, pages=len(pages), text=text), "answer": json.dumps(ans, ensure_ascii=False), "note": note})
        for field, value in facts:
            if value is None:
                a = {"valor": None, "pagina": None, "citacao": ""}
            else:
                page = next((i + 1 for i, t in enumerate(pages) if value in " ".join(t.split())), None)
                assert page, (name, value)
                a = {"valor": value, "pagina": page, "citacao": M.line_with([" ".join(t.split()) for t in pages], page, value)}
            rows.append({"id": f"d2:{rid('stranger', name, field)}", "task": "d2_facto", "prompt": M.D2_FACT.format(question=M.QUESTIONS[field], name=name, pages=len(pages), text=text), "answer": json.dumps(a, ensure_ascii=False), "note": note})
    out = ROOT / "sealed" / "stranger-test.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"{out.relative_to(ROOT)}: {len(rows)} rows ({sum(r['task'] == 'd1_elemento' for r in rows)} D1, {sum(r['task'] == 'd2_facto' for r in rows)} D2)")


if __name__ == "__main__":
    main()
