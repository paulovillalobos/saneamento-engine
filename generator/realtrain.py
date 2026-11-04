"""Training rows from REAL public documents (sources/real/train), keyed by hand, apart from the stranger test (D17).

    python -I generator/realtrain.py                 # writes training/data/real/train.jsonl (+ INDEX.md with the key table)
    python -I generator/realtrain.py --check         # keys only: every key inside the scaffold language, no file shared with the test

Same prompts, same whole-document view and same scaffold gate as the generated rows (generator/d1d2.py): a key the reader could
not give is never a row. Each document yields one D1 row under its real name, one under an uninformative name, and one with
extractor damage under a stranger name (the three shapes r6/D11 taught us real submissions take); each hand-keyed fact yields a D2
row (quote code-aligned on the page), and two absent-fact questions per document yield null rows. HARD RULE: a file whose sha256
equals any file of the stranger test (sources/real/{memorias,modelos,normas,wave2,wave3}) stops the script. The test never trains.
"""
import argparse
import hashlib
import importlib.util
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("d1d2", ROOT / "generator" / "d1d2.py"); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
sys.path.insert(0, str(ROOT / "generator"))
from ocr import pages_text  # noqa: E402

T = "sources/real/train"
P = "portaria-320-2026-1:anexo-V."
TEST_DIRS = ["memorias", "modelos", "normas", "wave2", "wave3"]

# (file, element id or None, tipo, [(field, value or None)], note). Element ids: P + "9", P + "27.i.i" …; None = not an element.
KEYS = [
    ("angra_alteracao_loteamento_proposta.pdf", P + "9", "escrito", [], "MDJ, alteração de loteamento (lote 219), Angra do Heroísmo"),
    ("angra_aviso_94_alteracao_lote1.pdf", None, "nao_e_elemento", [], "municipal aviso announcing a loteamento alteration (public discussion)"),
    ("angra_loteamento_mdj.pdf", P + "9", "escrito", [], "peças escritas bundle whose body is the MDJ of an industrial loteamento (index, termo, declaração, MDJ, quadros de áreas), Angra"),
    ("apa_siaia_drenagem_aguas_residuais_memoria.pdf", P + "27.i.v", "escrito", [], "MDJ of a wastewater drainage project, estudo prévio (public AIA archive)"),
    ("arganil_anexo_i_portaria320.pdf", None, "nao_e_elemento", [], "blank Portaria 320/2026 Anexo I form, Arganil"),
    ("arganil_anexo_iv_portaria320.pdf", None, "nao_e_elemento", [], "blank Portaria 320/2026 Anexo IV form, Arganil"),
    ("arganil_legalizacao_lista_elementos.pdf", None, "nao_e_elemento", [], "legalisation request form with element list, Arganil"),
    ("arganil_minuta_rcd.pdf", None, "nao_e_elemento", [], "blank PPGRCD minuta, Arganil"),
    ("arganil_rececao_obras_urbanizacao.pdf", None, "nao_e_elemento", [], "request form for reception of urbanisation works, Arganil"),
    ("aveiro_parque_infantil_bicicleta_memoria.pdf", P + "9", "escrito", [], "memória descritiva, projeto de execução of a playground (Aveiro, Viva a Cidade)"),
    ("borba_comunicacao_inicio_trabalhos.pdf", None, "nao_e_elemento", [], "blank form, comunicação de início dos trabalhos, Borba"),
    ("borba_cp_obras_demolicao.pdf", None, "nao_e_elemento", [], "blank form, comunicação prévia de demolição, Borba"),
    ("borba_cp_utilizacao.pdf", None, "nao_e_elemento", [], "blank form, comunicação prévia para utilização, Borba"),
    ("borba_informacao_instrumentos_planeamento.pdf", None, "nao_e_elemento", [], "blank request form for planning information, Borba"),
    ("borba_licenca_edificacao_arquitetura.pdf", None, "nao_e_elemento", [('custo_total', None)], "blank form listing the elements of a licence request (trap: names termo, calendarização, estimativa), Borba"),
    ("borba_requerimento_loteamento.pdf", None, "nao_e_elemento", [], "blank form, licenciamento de loteamento, Borba"),
    ("ccdrlvt_norma_01_ot_revisao_pdm.pdf", None, "nao_e_elemento", [], "CCDR procedure norm on PDM revisions"),
    ("cimaveiro_estrada_florestal_breve_mdj.pdf", P + "9", "escrito", [], "brief MDJ, forest road improvement, projeto de execução (CIM Aveiro)"),
    ("condeixa_alteracao_loteamento_01_2013_memoria.pdf", P + "9", "escrito", [], "memória descritiva, alteração de alvará de loteamento, Condeixa (table of lot areas on p.1)"),
    ("fcr_norma_comprev_edificacao.pdf", None, "nao_e_elemento", [], "list of elementos instrutórios, comunicação prévia de edificação, Figueira de Castelo Rodrigo"),
    ("fcr_norma_comprev_loteamento.pdf", None, "nao_e_elemento", [], "list of elementos instrutórios, comunicação prévia de loteamento, Figueira de Castelo Rodrigo"),
    ("fcr_norma_infprev_alt_utilizacao.pdf", None, "nao_e_elemento", [], "list of elementos instrutórios, informação prévia / alteração de utilização"),
    ("feira_mercado_municipal_mdj_arquitetura.pdf", P + "9", "escrito", [], "MDJ anteprojeto de arquitetura, market rehabilitation, Santa Maria da Feira (digitally signed)"),
    ("figueirovinhos_guia_23_energia_renovaveis.pdf", None, "nao_e_elemento", [], "requester guide for a renewable-energy request"),
    ("fronteira_caderno_encargos_projeto_ponte.pdf", None, "nao_e_elemento", [('custo_total', None)], "caderno de encargos for design services (trap: preço base 50.000,00 €)"),
    ("ilhavo_av_fernao_magalhaes_mdj.pdf", P + "9", "escrito", [], "MDJ, avenue requalification, Ílhavo"),
    ("jfalvalade_caderno_encargos_auditorio.pdf", None, "nao_e_elemento", [], "caderno de encargos of a works tender, JF Alvalade"),
    ("jfalvalade_caderno_encargos_praca.pdf", None, "nao_e_elemento", [('prazo_meses', None)], "caderno de encargos of a works tender (trap: prazo 150 dias, valor máximo € 156.000)"),
    ("jfalvalade_cave_conde_arnoso_mtq.pdf", None, "nao_e_elemento", [('custo_total', None)], "unpriced mapa de trabalhos e quantidades (0,00 € columns): quantities without cost are not the estimate"),
    ("jfalvalade_conservacao_2019_mtq.pdf", None, "nao_e_elemento", [], "unpriced mapa de trabalhos e quantidades"),
    ("jfalvalade_md_sede_gdcfc.pdf", P + "9", "escrito", [], "MDJ, club building rehabilitation, JF Alvalade"),
    ("jfalvalade_mdj_rua_silva_albuquerque.pdf", P + "9", "escrito", [], "MDJ, street requalification, JF Alvalade"),
    ("jfalvalade_memoria_arquitetura_cave_conde_arnoso.pdf", P + "9", "escrito", [], "MDJ, projeto de arquitetura, basement requalification, JF Alvalade"),
    ("jfalvalade_orcamento_enocivil.pdf", P + "27.f", "escrito", [('prazo_meses', None)], "priced orçamento by items and quantities (trap: prazo 30 dias → null)"),
    ("jfalvalade_parque_gomes_ferreira_mapa_medicoes.pdf", None, "nao_e_elemento", [], "mapa de medições (unpriced measurements)"),
    ("jfalvalade_parque_gomes_ferreira_mapa_quantidades.pdf", None, "nao_e_elemento", [('custo_total', None)], "unpriced mapa de quantidades (- € columns)"),
    ("jfalvalade_rua_antonio_ferreira_lista_precos_unitarios.pdf", P + "27.f", "escrito", [], "priced lista de preços unitários with totals per item (as Vagos LPU in the test)"),
    ("jfalvalade_sede_gdcfc_mtq.pdf", None, "nao_e_elemento", [], "unpriced mapa de quantidades with chapter index"),
    ("jfesgueira_prospecao_geotecnica_taboeira.pdf", None, "nao_e_elemento", [], "proposal for geotechnical prospecting services"),
    ("jfestrela_academia_contencao_mqt.pdf", None, "nao_e_elemento", [], "unpriced medições (0,00 €)"),
    ("jfestrela_ruas_2021_caderno_encargos.pdf", None, "nao_e_elemento", [], "caderno de encargos, 92 pages, JF Estrela"),
    ("lisboa_almada_negreiros_md_paisagista.pdf", P + "27.i.vii", "escrito", [], "landscape (PAI) speciality volume of an SRU street requalification — ambiguous: speciality of a multi-volume project, not the ordering memória"),
    ("lisboa_ciclovia_passeio_herois_mar_md.pdf", P + "9", "escrito", [], "MDJ, cycleway extension, projeto de execução, Lisboa"),
    ("lisboa_emel_ciclovia_cesar_oliveira_mdj.pdf", P + "9", "escrito", [], "MDJ rede viária, cycleway, EMEL 2021 (39 pages)"),
    ("lisboa_emel_ciclovia_rotunda_relogio_mdj.pdf", P + "9", "escrito", [], "MDJ rede viária, cycleway, EMEL 2026 (34 pages)"),
    ("lisboa_jardim_praca_imperio_mdj_paisagista.pdf", P + "9", "escrito", [], "MDJ, garden renovation where the landscape project is the operation (34 pages, firm letterhead)"),
    ("lisboa_memoria_paisagista_parque_vale_montanha.pdf", P + "9", "escrito", [], "MDJ, urban park phase 2, CML in-house landscape project (25 pages; 4 image pages)"),
    ("lnec_guia_avaliacao_acustica_2025.pdf", None, "nao_e_elemento", [], "LNEC guide on acoustic assessment criteria"),
    ("lousa_anexo_ie_especialidades.pdf", None, "nao_e_elemento", [], "blank municipal annex identifying speciality projects"),
    ("lousa_anexo_ii_inicio_trabalhos.pdf", None, "nao_e_elemento", [], "blank Portaria 320/2026 Anexo II form (Lousã)"),
    ("lousa_guia_pratico_procedimentos_urbanisticos.pdf", None, "nao_e_elemento", [], "practical guide of urban procedures, Lousã 2026"),
    ("lousa_normas_apresentacao_projetos_rjue.pdf", None, "nao_e_elemento", [], "norms for presenting projects digitally, Lousã"),
    ("lousa_rmue.pdf", None, "nao_e_elemento", [], "DR pages with the RMUE of Lousã"),
    ("lousa_sol016_juncao_elementos.pdf", None, "nao_e_elemento", [], "blank form, junção de elementos"),
    ("lousa_sol111_prorrogacao_prazo.pdf", None, "nao_e_elemento", [('prazo_meses', None)], "blank form, prorrogação de prazo (trap: the word prazo)"),
    ("madeira_dre_ligacao_quebradas_amparo_mdj.pdf", P + "9", "escrito", [], "MDJ of a road project, 124 pages (regional roads directorate) — only the first ~65k chars are shown"),
    ("mealhada_imp_gu_60.pdf", None, "nao_e_elemento", [], "blank certidão request form, Mealhada"),
    ("melgaco_alteracao_loteamento_sra_graca_mdj.pdf", P + "9", "escrito", [('fogos', '17')], "MDJ + regulamento, alteração de loteamento of a municipal bairro (17 fogos, p.3)"),
    ("melgaco_boucas_md_infraestruturas_eletricas.pdf", P + "27.i.iii", "escrito", [], "memória descritiva, electrical infrastructure of an industrial loteamento, Melgaço"),
    ("melgaco_zea_md_abastecimento_agua.pdf", P + "27.i.v", "escrito", [], "MDJ, water supply and irrigation network of the ZEA loteamento (urbanisation network, keyed as the water-and-sewage project)"),
    ("melgaco_zea_md_aguas_residuais.pdf", P + "27.i.v", "escrito", [], "MDJ, wastewater drainage network of the ZEA loteamento"),
    ("melgaco_zea_md_eletricidade_ip.pdf", P + "27.i.iii", "escrito", [], "MDJ, electrical infrastructure and public lighting of the ZEA loteamento"),
    ("melgaco_zea_mdj_itur.pdf", P + "27.i.viii", "escrito", [], "ITUR telecommunications project (ficha técnica + memória), Melgaço"),
    ("melgaco_zea_mdj_rede_viaria.pdf", P + "9", "escrito", [], "MDJ rede viária of the ZEA loteamento — urbanisation memória as item 9 (D12, as Amadora/Marinha Grande in the test)"),
    ("mogadouro_panfleto_medidas_autoprotecao.pdf", None, "nao_e_elemento", [], "municipal leaflet on self-protection measures (SCIE)"),
    ("mogadouro_panfleto_projeto_scie.pdf", None, "nao_e_elemento", [], "municipal leaflet on SCIE projects vs fichas"),
    ("murtosa_pp_zona_industrial.pdf", None, "nao_e_elemento", [], "DR aviso approving a plano de pormenor"),
    ("oaz_edital_normas_desmaterializacao.pdf", None, "nao_e_elemento", [], "edital with technical norms for digital processes, Oliveira de Azeméis"),
    ("oeiras_ciclovia_lombos_programa_preliminar.pdf", None, "nao_e_elemento", [], "programa preliminar for a design-services tender (not a project memória)"),
    ("peniche_gnr_mdj_aguas_pluviais.pdf", P + "27.i.vi", "escrito", [], "MDJ, public stormwater drainage network of a loteamento, Peniche"),
    ("peniche_gnr_pecas_escritas_eletricidade.pdf", P + "27.i.iii", "escrito", [], "peças escritas (memória + condições técnicas) of the electrical project of a loteamento, Peniche (41 pages)"),
    ("peniche_marginal_norte_memoria_estudo_previo.pdf", P + "9", "escrito", [], "memória descritiva, estudo prévio of a road relocation (40 pages)"),
    ("peniche_smas_ferrel_ppgrcd_1664_2013.pdf", None, "nao_e_elemento", [], "PPGRCD volume of a sewer tender (scanned-looking text)"),
    ("peniche_smas_ferrel_ppgrcd_2fase.pdf", None, "nao_e_elemento", [], "PPGRCD of a sewer and water-main tender"),
    ("peniche_smas_ferrel_pss.pdf", None, "nao_e_elemento", [], "plano de segurança e saúde, 67 pages"),
    ("pontedabarca_normas_tecnicas_submissao.pdf", None, "nao_e_elemento", [], "technical norms for digital submission, Ponte da Barca"),
    ("portodemos_normas_tecnicas_submissao_digital.pdf", None, "nao_e_elemento", [], "technical norms for digital submission, Porto de Mós"),
    ("portodemos_pss_tipo.pdf", None, "nao_e_elemento", [], "PSS template of the municipality, 64 pages"),
    ("povoalanhoso_erpi_memoria_descritiva.pdf", P + "9", "escrito", [], "memória descritiva of an ERPI construction filed for a certidão de interesse municipal — memória of the operation under another procedure (D12); OCR-like text without spaces"),
    ("povoalanhoso_normas_tecnicas_ou.pdf", None, "nao_e_elemento", [], "norms for digital urban processes, Póvoa de Lanhoso"),
    ("praiavitoria_tabela_taxas_urbanismo_2025.pdf", None, "nao_e_elemento", [], "municipal fee table"),
    ("provedor_parecer_r3149_05.pdf", None, "nao_e_elemento", [], "Ombudsman opinion on an urbanism complaint (46 pages) — a parecer about a case, not an external entity's opinion on the operation"),
    ("sabrosa_caderno_encargos_rua_mae_dagua.pdf", None, "nao_e_elemento", [], "caderno de encargos of a street rehabilitation tender"),
    ("sabugal_ppgrcd_memoria_descritiva.pdf", None, "nao_e_elemento", [], "PPGRCD memória of the ZLE loteamento (consultancy letterhead on every page)"),
    ("sabugal_req020_projetos_especialidades.pdf", None, "nao_e_elemento", [], "blank request form for speciality projects, Sabugal"),
    ("sabugal_req022_inicio_obra.pdf", None, "nao_e_elemento", [], "blank request form, início de obra, Sabugal"),
    ("sabugal_zle_md_acessibilidades.pdf", P + "27.b.vi", "escrito", [], "memória of the plano de acessibilidades of the ZLE loteamento (as Anadia in the test)"),
    ("sabugal_zle_md_acustica.pdf", P + "27.i.xii", "escrito", [], "acoustic project memória of the ZLE loteamento"),
    ("sabugal_zle_md_agua_esgotos.pdf", P + "27.i.v", "escrito", [], "water, sewage and stormwater networks memória of the ZLE loteamento"),
    ("sabugal_zle_md_arquitetura_paisagista.pdf", P + "27.i.vii", "escrito", [], "landscape (green space) speciality memória of the ZLE loteamento"),
    ("sabugal_zle_md_eletricidade_ip.pdf", P + "27.i.iii", "escrito", [], "electrical infrastructure memória of the ZLE loteamento (23 pages)"),
    ("sabugal_zle_md_gas.pdf", P + "27.i.iv", "escrito", [], "gas network memória of the ZLE loteamento (26 pages)"),
    ("sabugal_zle_md_infraestrutura_viaria.pdf", P + "9", "escrito", [], "road infrastructure memória of the ZLE loteamento — urbanisation memória as item 9 (D12)"),
    ("sabugal_zle_md_itur.pdf", P + "27.i.viii", "escrito", [], "ITUR telecommunications memória of the ZLE loteamento"),
    ("sardoal_req_vistoria_71_ebf.pdf", None, "nao_e_elemento", [], "blank vistoria request form"),
    ("sardoal_rmue.pdf", None, "nao_e_elemento", [], "DR pages with the RMUE of Sardoal"),
    ("satao_plpa_comunicacao.pdf", None, "nao_e_elemento", [], "municipal accessibility plan volume (communication), not a project's plano de acessibilidades"),
    ("sernancelhe_anexo_ii_inicio_trabalhos_especialidades.pdf", None, "nao_e_elemento", [], "blank Portaria 320/2026 Anexo II form (Sernancelhe)"),
    ("sines_zil2_rua_d_mdj_arranjos_exteriores.pdf", P + "9", "escrito", [], "MDJ, street exterior works as the operation itself, Sines"),
    ("sjm_rcd_eficiencia_energetica_ip.pdf", None, "nao_e_elemento", [], "PPGRCD of a public-lighting work"),
    ("sjm_rcd_pavimentacao.pdf", None, "nao_e_elemento", [], "PPGRCD of a paving work"),
    ("sjm_rotunda_av_liberdade_memoria_conceptual.pdf", P + "9", "escrito", [], "memória descritiva, estudo conceptual of a roundabout redesign (32 pages) — ambiguous: early stage"),
    ("tomar_normas_instrucao_digital_proposta.pdf", None, "nao_e_elemento", [], "proposed norms for digital instruction, Tomar"),
    ("vfxira_ifrru_modelo_parecer_vinculativo.pdf", None, "nao_e_elemento", [], "blank model of a municipal binding opinion (IFRRU)"),
    ("vianacastelo_parecer_apa_pu.pdf", P + "27.h", "escrito", [], "APA (external entity) opinion letter, 24 pages — ambiguous: an external entity's parecer, here on a plan rather than on a building operation"),
    ("vianacastelo_parecer_apa_s046221.pdf", P + "27.h", "escrito", [], "APA (external entity) opinion letter, 20 pages — same ambiguity"),
    ("angra_mercado_duque_braganca_memoria_descritiva.pdf", P + "9", "escrito", [], "memória descritiva of a design-build market tender (conceção-construção), 57 pages, Angra — the memória of the works"),
    ("pcoura_eb23_programa_procedimento.pdf", None, "nao_e_elemento", [], "programa do procedimento of a school rehabilitation tender, Paredes de Coura"),
    ("pcoura_eb23_caderno_encargos.pdf", None, "nao_e_elemento", [], "caderno de encargos of the school rehabilitation tender"),
    ("pcoura_eb23_relatorio_final.pdf", None, "nao_e_elemento", [], "final evaluation report of the tender jury (image first page)"),
    ("pcoura_cct_caderno_encargos.pdf", None, "nao_e_elemento", [], "caderno de encargos of a bus-station rehabilitation tender"),
]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def test_hashes():
    return {sha(f): f.name for d in TEST_DIRS for f in (ROOT / "sources" / "real" / d).glob("*.pdf")}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); ap.add_argument("--seed", type=int, default=11)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    tests = test_hashes()
    rows, index, dropped = [], [], []
    for path, elem, tipo, facts, note in KEYS:
        f = ROOT / T / path
        if sha(f) in tests:
            raise SystemExit(f"{path} is the test file {tests[sha(f)]}: the test never trains")
        pages = pages_text(f)
        text, shown = M.window(pages)
        cpages = [M.guard.collapse(t) for t in pages]
        name = Path(path).name
        ans = {"elemento": elem, "citacao": M.PORT[elem]["text"] if elem else "", "tipo": tipo}
        if elem and elem not in M.SHORTLIST_IDS:
            raise SystemExit(f"{path}: {elem} is not on the CPEDI shortlist")
        variants = [(name, text, shown), (M.opaque_name(rng), text, shown)]
        dtext, dshown = M.window([M.damage(t, rng) for t in pages])
        variants.append((M.stranger_name("DOC", Path(path).stem, rng), dtext, dshown))
        for k, (nm, tx, sh) in enumerate(variants):
            prompt = M.D1_PROMPT.format(shortlist=M.SHORTLIST, name=nm, pages=len(pages), shown=sh, text=tx)
            why = M.guard.check("d1_elemento", prompt, json.dumps(ans, ensure_ascii=False))
            if why:
                dropped.append((name, "d1", k, why)); continue
            rows.append({"id": f"d1:{M.rid('real', name, str(k))}", "task": "d1_elemento", "prompt": prompt, "answer": json.dumps(ans, ensure_ascii=False), "expediente": "real"})
        have = set()
        for field, value in facts:
            if field not in M.QUESTIONS:
                raise SystemExit(f"{path}: unknown fact field {field}")
            have.add(field)
            if value is None:
                ans2 = {"valor": None, "pagina": None, "citacao": ""}
            else:
                page = next((i + 1 for i, t in enumerate(cpages) if M.guard.aligned(t, value)), None)
                if not page:
                    dropped.append((name, field, value, "value is not a whole token of any page")); continue
                ans2 = {"valor": value, "pagina": page, "citacao": M.quote_for(cpages[page - 1], value, field)}
            prompt = M.D2_FACT.format(question=M.QUESTIONS[field], name=name, pages=len(pages), shown=shown, text=text)
            why = M.guard.check("d2_facto", prompt, json.dumps(ans2, ensure_ascii=False))
            if why:
                dropped.append((name, field, value, why)); continue
            rows.append({"id": f"d2:{M.rid('real', name, field)}", "task": "d2_facto", "prompt": prompt, "answer": json.dumps(ans2, ensure_ascii=False), "expediente": "real"})
        for field in rng.sample([q for q in M.QUESTIONS if q not in have and q != "wording_annex_vii"], 2):
            # absent-fact rows: a question this document does not answer → null (hand check: the keyer lists every fact the document DOES state)
            prompt = M.D2_FACT.format(question=M.QUESTIONS[field], name=name, pages=len(pages), shown=shown, text=text)
            rows.append({"id": f"d2:{M.rid('real', name, field, 'absent')}", "task": "d2_facto", "prompt": prompt, "answer": json.dumps({"valor": None, "pagina": None, "citacao": ""}, ensure_ascii=False), "expediente": "real"})
        index.append((name, len(pages), elem or "—", tipo, ", ".join(f"{k}={v}" for k, v in facts) or "—", note))
    for d in dropped:
        print("dropped:", d)
    print(f"{len(KEYS)} documents → {len(rows)} rows ({sum(r['task'] == 'd1_elemento' for r in rows)} D1, {sum(r['task'] == 'd2_facto' for r in rows)} D2), {len(dropped)} keys dropped")
    if a.check:
        return
    out = ROOT / "training" / "data" / "real"; out.mkdir(parents=True, exist_ok=True)
    with open(out / "train.jsonl", "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    lines = ["# Real training documents (sources/real/train) — keys", "", "| file | pages | element | tipo | facts | note |", "|---|---|---|---|---|---|"]
    lines += [f"| {n} | {p} | {e.replace('portaria-320-2026-1:anexo-', '')} | {t} | {fa} | {no} |" for n, p, e, t, fa, no in index]
    (out / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}/train.jsonl and INDEX.md")


if __name__ == "__main__":
    main()
