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
V9, V11, V12, V27K = "portaria-320-2026-1:anexo-V.9", "portaria-320-2026-1:anexo-V.11", "portaria-320-2026-1:anexo-V.12", "portaria-320-2026-1:anexo-V.27.k"
W = "sources/real/wave2"
W3 = "sources/real/wave3"
# (file, D1 element or None, D1 tipo, [D2 (field, value or None)], note)
KEYS = [
    (f"{R}/memorias/valongo_74l2023_md.pdf", V9, "escrito", [("area_parcela", "49 977,00"), ("custo_total", None)], "real memória descritiva e justificativa (loteamento, Valongo 2025)"),
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
    # ---- wave 2 (2026-10-28): 33 more public files, real names kept; sources in sources/real/PROVENANCE.md ----
    (f"{R}/modelos/OA_TR_dir_obra_fisc.pdf", None, "nao_e_elemento", [("apolice", None)], "OA minuta of the termo signed at the CONCLUSION of the works (art. 63): not the item k termo (assumption of the function)"),
    (f"{W}/OA_TR_dir_obra_inicio.pdf", V27K, "escrito", [("apolice", None)], "OASRN minuta, termo do diretor de obra for the START of works = item k"),
    (f"{W}/valpacos_memoria_pr_1678_22.pdf", "portaria-320-2026-1:anexo-V.27.i.xi", "escrito", [("uso", "ESTRUTURA RESIDENCIAL PARA PESSOAS IDOSAS"), ("custo_total", None)], "real SCIE project memória (ERPI, Valpaços 2022)"),
    (f"{W}/uminho_memoria_estabilidade_braga.pdf", "portaria-320-2026-1:anexo-V.27.i.i", "escrito", [("custo_total", None)], "real memória of a stability project (UMinho, Centro de Solidariedade de Braga)"),
    (f"{W}/anadia_memoria_acessibilidades.pdf", "portaria-320-2026-1:anexo-V.27.b.vi", "escrito", [("fogos", None)], "real memória of a plano de acessibilidades (Anadia)"),
    (f"{W}/viladoconde_memoria_pluviais.pdf", "portaria-320-2026-1:anexo-V.27.i.vi", "escrito", [("area_parcela", None)], "real memória of a stormwater project (Vila do Conde 2017)"),
    (f"{W}/valpacos_memoria_ited.pdf", "portaria-320-2026-1:anexo-V.27.i.viii", "escrito", [("custo_total", None)], "real ITED project memória (Valpaços 2024)"),
    (f"{W}/viladoconde_estimativa.pdf", "portaria-320-2026-1:anexo-V.27.f", "escrito", [], "real estimativa orçamental (Caxinas community centre, SPMR 2016)"),
    (f"{W}/ipcb_memoria_reabilitacao_escola.pdf", V9, "escrito", [("custo_total", None)], "memória descritiva e justificativa of a rehabilitation project (IPCB 2023, student work in the real format)"),
    (f"{W}/dgt_planta_localizacao.pdf", "portaria-320-2026-1:anexo-V.2", "desenhado", [], "DGT planta de localização printed from SNIT (ortofoto, PT-TM06)"),
    (f"{W}/loures_PDF20241114175831728.pdf", None, "nao_e_elemento", [("apolice", None)], "Loures termo for utilização sem operação urbanística prévia (art. 63): not an Annex V item"),
    (f"{W}/pontedelima_mod_166.pdf", None, "nao_e_elemento", [], "termo diretor de obra, receção provisória de obras de urbanização (loteamento): not a CPEDI item"),
    (f"{W}/pontedelima_mod_167.pdf", None, "nao_e_elemento", [], "termo diretor de obra, receção definitiva (loteamento): not a CPEDI item"),
    (f"{W}/funchal_minuta_memoria_viveiro_lojas.pdf", None, "nao_e_elemento", [("area_total_construcao", None)], "a business-incubator applicant memo called 'memória descritiva': not the project memória"),
    (f"{W}/alfandegadafe_competencia_tecnicos.pdf", None, "nao_e_elemento", [], "an internal municipal information note"),
    (f"{W}/alijo_ficha_projeto_escola.pdf", None, "nao_e_elemento", [("custo_total", None)], "a funded-project summary sheet"),
    (f"{W}/amarante_termos_comunicacoes_utilizacao.pdf", None, "nao_e_elemento", [], "a municipal explanatory note about termos"),
    (f"{W}/anepc_nt03_2020.pdf", None, "nao_e_elemento", [], "ANEPC technical note on SCIE projects"),
    (f"{W}/arcos_ine_q3_instrucoes.pdf", None, "nao_e_elemento", [("fogos", None)], "INE Q3 filling instructions (not the ficha itself)"),
    (f"{W}/loures_ine_q3_instrucoes.pdf", None, "nao_e_elemento", [], "INE Q3 filling instructions, Loures copy"),
    (f"{W}/benavente_deliberacao_minutas_tr.pdf", None, "nao_e_elemento", [], "a council deliberation approving termo minutas"),
    (f"{W}/caminha_caderno_encargos.pdf", None, "nao_e_elemento", [("prazo_meses", None)], "a tender specification for topography services"),
    (f"{W}/cascais_anexo_iv.pdf", None, "nao_e_elemento", [], "a municipal regulation annex (obras de urbanização)"),
    (f"{W}/castrodaire_manual_normas_digitais.pdf", None, "nao_e_elemento", [], "a digital-submission manual"),
    (f"{W}/estarreja_elementos_2020.pdf", None, "nao_e_elemento", [], "a list of elements for a forest-defence opinion"),
    (f"{W}/figfoz_nip12_licenciamento.pdf", None, "nao_e_elemento", [], "a process-instruction norm"),
    (f"{W}/gouveia_guia_redes_prediais.pdf", None, "nao_e_elemento", [], "a technical guide for building-network projects"),
    (f"{W}/leiria_anexoiv_levantamentos.pdf", None, "nao_e_elemento", [], "criteria for topographic surveys (annex of a tender)"),
    (f"{W}/macedo_obras_edificacao_arquitetura.pdf", None, "nao_e_elemento", [], "a municipal checklist (Mod. 331)"),
    (f"{W}/maia_levantamento_acessibilidade.pdf", None, "nao_e_elemento", [], "a municipal accessibility diagnostic"),
    (f"{W}/seixal_postura_aguas_residuais.pdf", None, "nao_e_elemento", [], "a municipal postura"),
    (f"{W}/seixal_postura_estabilidade.pdf", None, "nao_e_elemento", [], "a municipal postura"),
    (f"{W}/viseu_norma_pip.pdf", None, "nao_e_elemento", [], "a process-instruction norm (PIP)"),
    (f"{W}/vncerveira_normas_levantamentos.pdf", None, "nao_e_elemento", [], "municipal norms for surveys and planta de implantação"),
    # wave 3 (2026-11-03): keys written and committed BEFORE any reader output was seen; never used to fix data. "ambiguous" = a second reader could defend the other key.
    (f"{W3}/amadora_parque_urbano_neudel_memoria_descritiva.pdf", V9, "escrito", [], "w3 MDJ, road infrastructure of an urban park (obras de urbanização) — ambiguous: urbanisation memória as item 9 (D12)"),
    (f"{W3}/lagos_alteracao_loteamento_memoria_descritiva.pdf", V9, "escrito", [("area_parcela", "1.900,00")], "w3 MDJ, alteração de loteamento, Lagos 2025"),
    (f"{W3}/matosinhos_herois_de_franca_pecas_escritas.pdf", V9, "escrito", [], "w3 MDJ, estudo prévio of a street reordering — ambiguous: urbanisation memória as item 9 (D12)"),
    (f"{W3}/mgrande_15001_muros_eb_praia_vieira_mdj.pdf", V9, "escrito", [], "w3 MDJ, school boundary walls, Marinha Grande 2015 (cover + index + body)"),
    (f"{W3}/mgrande_cantina_embra_mdj.pdf", V9, "escrito", [], "w3 MDJ, canteen rehabilitation, Marinha Grande"),
    (f"{W3}/mgrande_memoria_em242_estrada_atlantica.pdf", V9, "escrito", [], "w3 MDJ, road conservation project — ambiguous: urbanisation memória as item 9 (D12)"),
    (f"{W3}/mgrande_vol_iii_mapa_quantidades.pdf", None, "nao_e_elemento", [], "w3 unpriced mapa de quantidades — ambiguous: quantities without cost are not the estimate (27.f)"),
    (f"{W3}/moimenta_memoria_descritiva_pacos_fase02.pdf", V9, "escrito", [], "w3 MDJ, town-hall roof and façades, Moimenta da Beira"),
    (f"{W3}/nazare_pe_347_pavilhao_famalicao_mdj.pdf", V9, "escrito", [], "w3 MDJ, sports pavilion energy rehabilitation, Nazaré 2016"),
    (f"{W3}/nazare_pe_365_escola_amadeu_gaudencio_mdj.pdf", V9, "escrito", [("custo_total", None)], "w3 MDJ, six classrooms extension, Nazaré 2017"),
    (f"{W3}/nazare_pe_365_indice_pecas_desenhadas.pdf", None, "nao_e_elemento", [], "w3 index of drawn pieces (a list)"),
    (f"{W3}/nazare_pe_365_arq_021_mapa_bancadas.pdf", "portaria-320-2026-1:anexo-V.27.b.iv", "desenhado", [], "w3 drawn sheet 1:20, bench detail of the architecture project — ambiguous: construction detail (27.b.iv)"),
    (f"{W3}/pombal_casa_varela_memoria_descritiva_arquitectura.pdf", V9, "escrito", [], "w3 MDJ, historic house rehabilitation, Pombal 2016 (firm letterhead repeated)"),
    (f"{W3}/resende_memoria_descritiva_centro_informacao_carquere.pdf", V9, "escrito", [], "w3 MDJ anteprojeto, parish residence conversion, Resende 2016"),
    (f"{W3}/santiagocacem_memoria_descritiva_loteamento_piaget.pdf", V9, "escrito", [("area_parcela", "181.182,57")], "w3 MDJ, operação de loteamento, Santiago do Cacém 2017"),
    (f"{W3}/sever_memoria_descritiva_arquitetura.pdf", V9, "escrito", [], "w3 MDJ, ecocentre, Sever do Vouga (text extracts broken into fragments)"),
    (f"{W3}/setubal_tr_autor_do_projeto.pdf", V11, "escrito", [], "w3 blank minuta, termo do autor do projeto (Portaria 113/2015 annex), Setúbal"),
    (f"{W3}/setubal_tr_diretor_de_obra.pdf", V27K, "escrito", [("apolice", None)], "w3 blank minuta, termo do diretor de obra, Setúbal"),
    (f"{W3}/vagos_9_lpu_lista_precos_unitarios.pdf", "portaria-320-2026-1:anexo-V.27.f", "escrito", [("custo_total", "2.963.691,24 €")], "w3 priced bill of quantities with chapter totals and TOTAL — ambiguous: estimate based on quantities (27.f)"),
    (f"{W3}/alcoutim_cp_obras_edificacao.pdf", None, "nao_e_elemento", [("custo_total", None)], "w3 blank municipal form, comunicação prévia"),
    (f"{W3}/braga_insturb0502_licenciamento_obra_edificacao.pdf", None, "nao_e_elemento", [], "w3 list of elementos instrutórios, Braga"),
    (f"{W3}/evora_edital_384_2010_rmeu.pdf", None, "nao_e_elemento", [], "w3 DR pages with a municipal regulation (Évora RMEU 2010)"),
    (f"{W3}/guimaraes_estimativa_orcamental_valores_referencia.pdf", None, "nao_e_elemento", [("custo_total", None)], "w3 reference €/m2 values for the estimate, Guimarães (trap: €/m2 table)"),
    (f"{W3}/lamego_normas_tecnicas_instrucao.pdf", None, "nao_e_elemento", [], "w3 technical norms for digital instruction, Lamego"),
    (f"{W3}/mesaofrio_aviso_253_2025_rmue.pdf", None, "nao_e_elemento", [], "w3 Aviso with the RMUE of Mesão Frio"),
    (f"{W3}/moimenta_caderno_encargos_cg.pdf", None, "nao_e_elemento", [("prazo_meses", None)], "w3 caderno de encargos, cláusulas gerais (trap: prazo 90 dias)"),
    (f"{W3}/oe_parecer_coordenacao_projeto_urbanizacao.pdf", None, "nao_e_elemento", [], "w3 Ordem dos Engenheiros opinion on project coordination"),
    (f"{W3}/oe_projeto_acustico_nota_tecnica.pdf", None, "nao_e_elemento", [], "w3 Ordem dos Engenheiros technical note on the acoustic project"),
    (f"{W3}/pontadelgada_prefixos_urbanismo.pdf", None, "nao_e_elemento", [], "w3 table of file-name prefixes per document, Ponta Delgada"),
    (f"{W3}/prociv_azores_map_edificios_escolares_2018.pdf", None, "nao_e_elemento", [], "w3 civil-protection guide on self-protection measures for schools"),
    (f"{W3}/scflores_fs035_comunicacao_previa_obras_edificacao.pdf", None, "nao_e_elemento", [], "w3 service sheet for comunicação prévia, Santa Cruz das Flores"),
    (f"{W3}/vilareal_anexoii_normas_instrucao_formato_digital.pdf", None, "nao_e_elemento", [], "w3 Anexo II, norms for digital instruction, Vila Real"),
]


def rid(*parts):
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def main():
    rows = []
    for path, elem, tipo, facts, note in KEYS:
        r = PdfReader(str(ROOT / path)); pages = [(p.extract_text() or "").strip() for p in r.pages]
        text, shown = M.window(pages)
        cpages = [M.guard.collapse(t) for t in pages]
        name = Path(path).name
        ans = {"elemento": elem, "citacao": M.PORT[elem]["text"] if elem else "", "tipo": tipo}
        rows.append({"id": f"d1:{rid('stranger', name)}", "task": "d1_elemento", "prompt": M.D1_PROMPT.format(shortlist=M.SHORTLIST, name=name, pages=len(pages), shown=shown, text=text), "answer": json.dumps(ans, ensure_ascii=False), "note": note})
        for field, value in facts:
            if value is None:
                a = {"valor": None, "pagina": None, "citacao": ""}
            else:
                page = next((i + 1 for i, t in enumerate(cpages) if M.guard.aligned(t, value)), None)
                assert page, (name, value)
                a = {"valor": value, "pagina": page, "citacao": M.quote_for(cpages[page - 1], value, field)}
            prompt = M.D2_FACT.format(question=M.QUESTIONS[field], name=name, pages=len(pages), shown=shown, text=text)
            why = M.guard.check("d2_facto", prompt, json.dumps(a, ensure_ascii=False))
            assert not why, (name, field, why)   # a key outside the language = the window does not show that page: fix window(), not the key
            rows.append({"id": f"d2:{rid('stranger', name, field)}", "task": "d2_facto", "prompt": prompt, "answer": json.dumps(a, ensure_ascii=False), "note": note})
    out = ROOT / "sealed" / "stranger-test.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"{out.relative_to(ROOT)}: {len(rows)} rows ({sum(r['task'] == 'd1_elemento' for r in rows)} D1, {sum(r['task'] == 'd2_facto' for r in rows)} D2)")


if __name__ == "__main__":
    main()
