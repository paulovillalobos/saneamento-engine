"""Simulated CPEDI expedientes for Celorico de Basto, written from the law with planted errors, each with its answer key and
the per-file labels the reader trains on (D1: which element is this file; D2: which facts does it state, on which page).

    .venv-of-rjue/bin/python -I generator/expedientes.py --n 3 --out training/expedientes --seed 1
    ... --sealed            # writes to sealed/expedientes with the sealed seed and never overlaps the training seeds

Every expediente: a folder with one PDF per NoPaper slot (Celorico codes), submission.json (what the installation delivers),
key.json (facts, planted errors, the Annex V findings a correct saneamento reports), labels.jsonl (one row per file).
All people are fictional, NIF 999999990, every page carries the SIMULADO banner. Nothing is read from any citizen file.
"""
import argparse
import hashlib
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from generator import pdfgen as G  # noqa: E402

NIF = "999999990"
DOCS = {d["code"]: d for d in json.loads((ROOT / "celorico" / "mapping" / "documents.json").read_text(encoding="utf-8"))["documents"]}
PACK = json.loads((ROOT / "law" / "cp-edificacao.json").read_text(encoding="utf-8"))
QUOTES = {r["passage"]: r["quote"] for r in PACK["rules"]}
QUOTES.update({k: v["quote"] for k, v in PACK["general_provisions"].items()})
PORT = {p["id"]: p for p in json.loads((ROOT / "structure" / "portaria-320-2026-1.json").read_text(encoding="utf-8"))["passages"]}
WORDING_I = "observa as normas legais e regulamentares aplicáveis à pretensão"
WORDING_II = "Observa as normas legais e regulamentares aplicáveis, com exceção de nenhuma"
FREGUESIAS = ["Arnoia", "Basto (São Clemente)", "Borba de Montanha", "Caçarilhe", "Canedo de Basto", "Carvalho", "Codeçoso", "Corgo",
              "Fervença", "Gagos", "Infesta", "Moreira do Castelo", "Ourilhe", "Rego", "Ribas", "Vale de Bouro", "Veade", "Britelo", "Molares", "Agilde"]
FIRST = ["Ana", "Bruno", "Carla", "Diogo", "Eva", "Filipe", "Gonçalo", "Helena", "Inês", "João", "Leonor", "Miguel", "Nuno", "Olga", "Pedro",
         "Rita", "Sérgio", "Teresa", "Vasco", "Xavier"]
LAST = ["Simulado", "Fictício", "de Teste", "Exemplo", "Modelo", "Amostra"]
STREETS = ["Rua da Escola", "Travessa do Souto", "Lugar de Vilar", "Rua do Outeiro", "Caminho da Lameira", "Lugar da Devesa", "Rua das Tílias", "Lugar de Carvalhal"]
WORKS = [("construção de moradia unifamiliar", "Habitação unifamiliar", 1, (1, 2)), ("construção de edifício de habitação bifamiliar", "Habitação bifamiliar", 2, (2, 3)),
         ("ampliação de moradia unifamiliar", "Habitação unifamiliar", 1, (1, 2)), ("construção de armazém agrícola", "Armazém agrícola", 0, (1, 1)),
         ("construção de edifício de comércio e serviços", "Comércio e serviços", 0, (1, 3)), ("alteração e ampliação de moradia unifamiliar", "Habitação unifamiliar", 1, (2, 2))]
SPECIALTIES = [("TREECP", "SRCEST", "MDEECP", "PDEECP", "estabilidade, de escavação e contenção periférica"),
               ("TRPIE", "SRCIE", "MDPIE", "PDPIE", "instalações elétricas"), ("TRRPAE", "SRCPAE", "MDRPAE", "PDRPAE", "redes prediais de água e esgotos"),
               ("TRPAP", "SRCAP", "MDPAP", "PDPAP", "águas pluviais"), ("TRITED", "SRITED", "MDITED", "PDITED", "infraestruturas de telecomunicações (ITED)"),
               ("TRPCT", "SRCCT", "MDPCT", "PDPCT", "comportamento térmico"), ("TRPCA", "SRCCA", "MDPCA", "PDPCA", "condicionamento acústico")]
REQUIRED_ALWAYS = ["REQ", "CRP", "TRPARQ", "SRCARQ", "TRCP", "SRCCP", "FOTO", "MDARQ", "CEO", "EOCT", "OUTDOC", "P10000", "LEVT", "PI", "PLANT", "ALC", "CORTES", "PC", "FEE", "IMPIC", "ASAT"]
ERRORS = ["missing_required", "template_wording_missing", "unsigned", "not_pdf", "not_pdfa", "value_mismatch", "impossible_value", "wrong_site", "expired_insurance", "wrong_signer"]


def person(rng, role, title=None, body=None):
    name = f"{rng.choice(FIRST)} {rng.choice(LAST)} {rng.choice(FIRST)}"
    return {"name": name, "role": role, "title": title, "body": body, "number": f"{rng.randrange(1000, 99999):05d}-SIM",
            "address": f"{rng.choice(STREETS)}, n.º {rng.randrange(1, 120)}, {rng.choice(['4000-000 Porto', '4700-000 Braga', '4890-000 Celorico de Basto', '4800-000 Guimarães'])}",
            "policy": f"SIM-RC-{rng.randrange(1, 9999):04d}"}


def make_case(rng, cid):
    work, use, fogos, (pmin, pmax) = rng.choice(WORKS)
    plot = rng.randrange(300, 4000, 10)
    pisos = rng.randrange(pmin, pmax + 1)
    impl = int(plot * rng.uniform(0.12, 0.45) // 1)
    built = int(impl * pisos * rng.uniform(0.85, 1.0))
    imperm = min(plot, impl + rng.randrange(20, 200))
    height = round(pisos * 3 + rng.uniform(0.6, 1.8), 1)
    cost = int(built * rng.randrange(650, 1300) / 100) * 100
    submitted = f"2026-{rng.randrange(10, 13):02d}-{rng.randrange(1, 29):02d}"
    site = f"{rng.choice(STREETS)}, n.º {rng.randrange(1, 300)}, {rng.choice(FREGUESIAS)}, 4890-000 Celorico de Basto"
    c = {"id": cid, "work": work, "use": use, "fogos": fogos, "pisos": pisos, "plot": plot, "impl": impl, "built": built, "imperm": imperm,
         "perm": plot - imperm, "volume": int(built * 3.1), "height": height, "facade": round(height - 0.7, 1), "parking": max(1, fogos * 2 or 2),
         "cost": cost, "submitted": submitted, "site": site, "start": "janeiro de 2027", "months": rng.randrange(8, 24),
         "insurance_from": "2026-01-01", "insurance_to": "2026-12-31",
         "people": {"requerente": person(rng, "requerente"), "arquiteto": person(rng, "arquiteto", "arquiteto", "Ordem dos Arquitectos"),
                    "engenheiro": person(rng, "engenheira", "engenheira civil", "Ordem dos Engenheiros"),
                    "diretor": person(rng, "diretor de obra", "engenheiro civil", "Ordem dos Engenheiros")}}
    c["people"]["requerente"]["address"] = site
    return c


def eur(n):
    return f"{n:,.2f} €".replace(",", " ").replace(".", ",").replace(" ", ".", 0) if False else f"{n:,}".replace(",", " ") + ",00 €"


def sig(doc, c, p, when=None):
    doc.gap(4)
    doc.text(f"Celorico de Basto, {when or c['submitted']}. Assinado digitalmente por {p['name']} (certificado de teste).", size=9)


# ---- document bodies: each returns (Doc, facts) where facts = [(field, value, unit, page, tag)] ----------------------
def summary_rows(c, override=None):
    o = override or {}
    rows = [("superficie_total_terreno", "Superfície total do terreno objeto da operação urbanística", str(o.get("plot", c["plot"])), "m2"),
            ("area_parcela", "Área da parcela ou lote", str(o.get("plot", c["plot"])), "m2"),
            ("area_implantacao", "Área total de implantação", str(c["impl"]), "m2"),
            ("area_impermeabilizacao", "Área total de impermeabilização", str(c["imperm"]), "m2"),
            ("area_permeavel", "Área total permeável", str(c["perm"]), "m2"),
            ("area_total_construcao", "Área total de construção", str(o.get("built", c["built"])), "m2"),
            ("volume_total", "Volume total", str(c["volume"]), "m3"), ("altura_edificacao", "Altura da edificação", str(c["height"]).replace(".", ","), "m"),
            ("altura_fachada", "Altura da fachada", str(c["facade"]).replace(".", ","), "m"),
            ("pisos_acima_soleira", "N.º de pisos acima da cota de soleira", str(c["pisos"]), ""), ("pisos_abaixo_soleira", "N.º de pisos abaixo da cota de soleira", "0", ""),
            ("uso", "Uso a que se destina a edificação", c["use"], ""), ("fogos", "N.º total de fogos", str(c["fogos"]), ""),
            ("lugares_estacionamento", "N.º total de lugares de estacionamento", str(c["parking"]), "")]
    return rows


def doc_request(c, override=None):
    req = c["people"]["requerente"]
    d = G.Doc("Requerimento de comunicação prévia (modelo do Anexo I)")
    d.text("Exmo. Senhor Presidente da Câmara Municipal de Celorico de Basto")
    d.text(f"{req['name']}, contribuinte n.º {NIF}, com morada em {req['address']}, vem apresentar comunicação prévia de obras de edificação "
           f"({c['work']}) no prédio sito em {c['site']}, nos termos do Regime Jurídico da Urbanização e da Edificação.")
    d.gap(); d.text("Síntese urbanística (Anexo I-C)", bold=True)
    facts = []
    for field, label, value, unit in summary_rows(c, override):
        pg = d.text(f"{label}: {value} {unit}".strip(), tag=field)
        facts.append((field, value, unit, pg, f"{label}: {value} {unit}".strip()))
    sig(d, c, req)
    return d, facts


def doc_memory(c, override=None):
    o = override or {}
    a = c["people"]["arquiteto"]
    d = G.Doc("Memória descritiva e justificativa")
    d.text(f"A presente memória descritiva e justificativa respeita à {c['work']}, localizada em {c['site']}, concelho de Celorico de Basto, "
           f"em prédio com a área de {o.get('plot', c['plot'])} m2.")
    d.text("A pretensão insere-se em Solo Urbano, conforme a Planta de Ordenamento do Plano Diretor Municipal de Celorico de Basto "
           "(2.ª revisão, Aviso n.º 14352/2025/2). Não incide sobre áreas da Reserva Ecológica Nacional nem da Reserva Agrícola Nacional.")
    pg_b = d.text(f"A edificação desenvolve-se em {c['pisos']} piso(s) acima da cota de soleira, com área de implantação de {c['impl']} m2 e área total de "
                  f"construção de {o.get('built', c['built'])} m2, destinada a {c['use'].lower()}" + (f" ({c['fogos']} fogo(s))" if c["fogos"] else "") +
                  f", com {c['parking']} lugar(es) de estacionamento no interior da parcela.", tag="area_total_construcao")
    d.text("Enquadramento urbanístico: a operação cumpre os parâmetros de edificabilidade do PDM para a categoria de solo em causa, nomeadamente o índice de "
           "ocupação, o número máximo de pisos e a altura da fachada, e respeita os afastamentos regulamentares. O arranjo exterior prevê a manutenção da "
           "permeabilidade do solo na parte não edificada da parcela.")
    pg_q = d.text(f"Quadro sinóptico: superfície do terreno {o.get('plot', c['plot'])} m2; área de implantação {c['impl']} m2; área total de construção "
                  f"{o.get('built', c['built'])} m2; área permeável {c['perm']} m2; área impermeabilizada {c['imperm']} m2; volume {c['volume']} m3; "
                  f"altura da edificação {str(c['height']).replace('.', ',')} m; altura da fachada {str(c['facade']).replace('.', ',')} m.", tag="quadro")
    sig(d, c, a)
    return d, [("area_total_construcao", str(o.get("built", c["built"])), "m2", pg_b, None), ("area_parcela", str(o.get("plot", c["plot"])), "m2", pg_q, None),
               ("pisos_acima_soleira", str(c["pisos"]), "", pg_b, None)]


def doc_term_author(c, p, project, kind="I", site=None, wording=True):
    d = G.Doc(f"Termo de responsabilidade do autor do projeto de {project}")
    head = (f"{p['name']}, {p['title']}, com domicílio em {p['address']}, contribuinte n.º {NIF}, inscrito na {p['body']} sob o n.º {p['number']}, declara, "
            f"para efeitos do disposto no n.º 1 do artigo 10.º do Decreto-Lei n.º 555/99, de 16 de dezembro, na sua redação atual, que o projeto de {project}, "
            f"de que é autor, relativo à obra de {c['work']}, localizada em {site or c['site']}, cuja comunicação prévia foi apresentada por {c['people']['requerente']['name']}")
    if kind == "I":
        pg = d.text(head + (", " + WORDING_I + "." if wording else " e que o mesmo foi elaborado com todo o cuidado."), tag="wording")
    else:
        pg = d.text(head + ":")
        d.text(WORDING_II + ";" if wording else "Foi elaborado com cuidado;")
        d.text("Está conforme com os planos municipais ou intermunicipais de ordenamento do território aplicáveis à pretensão, nos termos do disposto no n.º 2 do "
               "artigo 10.º do RJUE, bem como com o Regulamento do PDM de Celorico de Basto.")
    d.text(f"Declara ainda, para efeitos do n.º 1 do artigo 24.º da Lei n.º 31/2009, de 3 de julho, na sua redação atual, que o seguro de responsabilidade civil "
           f"extracontratual com a Apólice n.º {p['policy']} cujo tomador é {p['name']} abrange a elaboração e subscrição do presente projeto, de acordo com a "
           f"estimativa de custo total da obra, cujo valor é de {eur(c['cost'])}.")
    sig(d, c, p)
    phrase = WORDING_I if kind == "I" else WORDING_II
    return d, [("wording_annex_vii", phrase if wording else "", "", pg, "presente" if wording else "ausente"), ("custo_total", eur(c["cost"]), "", pg, None)]


def doc_term_coordinator(c, p):
    d = G.Doc("Termo de responsabilidade do coordenador de projeto")
    d.text(f"{p['name']}, com domicílio em {p['address']}, contribuinte n.º {NIF}, inscrito na {p['body']} sob o n.º {p['number']}, na qualidade de coordenador, relativo à "
           f"obra de {c['work']}, localizada em {c['site']}, cuja comunicação prévia foi apresentada por {c['people']['requerente']['name']}, declara, para efeitos do "
           "disposto no n.º 1 do artigo 10.º do Decreto-Lei n.º 555/99, de 16 de dezembro, na sua redação atual, a compatibilidade entre os diversos projetos e as "
           "condições necessárias para o cumprimento das disposições legais e regulamentares aplicáveis a cada especialidade e a respeitar por cada autor de projeto.")
    d.text(f"Declara ainda que o seguro de responsabilidade civil extracontratual com a Apólice n.º {p['policy']} cujo tomador é {p['name']} abrange a coordenação dos "
           f"presentes projetos, de acordo com a estimativa de custo total da obra, cujo valor é de {eur(c['cost'])}.")
    sig(d, c, p)
    return d, []


def doc_term_director(c, p):
    d = G.Doc("Termo de responsabilidade pela assunção da função de diretor de obra")
    d.text(f"{p['name']}, com domicílio em {p['address']}, contribuinte n.º {NIF}, inscrito na {p['body']} sob o n.º {p['number']}, declara, para efeitos do disposto no "
           f"artigo 21.º, n.º 4 da Lei n.º 31/2009, de 3 de julho, relativamente à obra de {c['work']}, localizada em {c['site']}, cujo titular é "
           f"{c['people']['requerente']['name']}, que se responsabiliza pelo exercício da função de diretor de obra.")
    d.text(f"Declara ainda que o seguro de responsabilidade civil extracontratual com a Apólice n.º {p['policy']} cujo tomador é {p['name']} abrange a direção da obra, "
           f"de acordo com a estimativa de custo total da obra, cujo valor é de {eur(c['cost'])}.")
    sig(d, c, p)
    return d, []


def doc_insurance(c, p, scope, to=None):
    d = G.Doc("Comprovativo de seguro de responsabilidade civil profissional")
    pg = d.text(f"Certifica-se que {p['name']} é tomador da apólice n.º {p['policy']}, de seguro de responsabilidade civil profissional, que abrange {scope} relativos à obra de "
                f"{c['work']}, localizada em {c['site']}, com período de validade de {c['insurance_from']} a {to or c['insurance_to']}.", tag="validade")
    d.text("Emitido por Seguradora Exemplo, S.A. (entidade fictícia).")
    sig(d, c, {"name": "Seguradora Exemplo, S.A."})
    return d, [("validade_seguro_fim", to or c["insurance_to"], "", pg, None), ("apolice", p["policy"], "", pg, None)]


def doc_plain(c, title, p, *texts, facts=()):
    d = G.Doc(title)
    pages = [d.text(t) for t in texts]
    sig(d, c, p)
    return d, [(f, v, u, pages[i], None) for f, v, u, i in facts]


def doc_drawing(c, title, number, scale, p, kind):
    d = G.Doc(title)
    d.rect(80, 420, 435, 300)
    if kind == "plan":
        d.rect(150, 470, 300, 200); d.line(300, 470, 300, 670); d.line(150, 570, 300, 570)
        for x, y, s in ((190, 620, "Sala"), (340, 620, "Cozinha"), (190, 510, "Quarto"), (340, 510, "Quarto")):
            d.cur.append(("text", x, y, 10, False, s))
    elif kind == "section":
        d.line(150, 470, 450, 470); d.line(150, 470, 150, 610); d.line(450, 470, 450, 610); d.line(150, 610, 300, 680); d.line(300, 680, 450, 610)
        d.cur.append(("text", 455, 472, 8, False, "cota de soleira 0,00")); d.cur.append(("text", 455, 612, 8, False, f"+{str(c['facade']).replace('.', ',')}"))
    else:
        d.rect(100, 440, 400, 260); d.rect(220, 520, 160, 110, filled=True)
        d.cur.append(("text", 105, 705, 9, False, f"limite da parcela ({c['plot']} m2)")); d.cur.append(("text", 230, 570, 9, False, f"implantação {c['impl']} m2"))
    d.y = 400
    d.text(f"Requerente: {c['people']['requerente']['name']}    Desenho n.º {number}    Escala {scale}", size=9)
    d.text(f"Localização: {c['site']}    Especificação: {title}    Data: {c['submitted']}", size=9)
    d.text(f"Autor: {p['name']}", size=9)
    sig(d, c, p)
    return d, []


def doc_photo(c, p):
    d = G.Doc("Registo fotográfico da situação existente")
    d.text("Registo fotográfico da situação existente, abrangendo o imóvel e as edificações adjacentes (imagens sintéticas).")
    d.image(G.png(160, 100, 40), 80, 480, 220, 140); d.image(G.png(160, 100, 160), 320, 480, 220, 140)
    d.y = 460
    sig(d, c, p)
    return d, []


def documents(c, plan):
    """All documents of the expediente as (code, stem, title, kind, signer, Doc, facts); `plan` holds the planted errors."""
    P = c["people"]; arq, eng, dire, req = P["arquiteto"], P["engenheiro"], P["diretor"], P["requerente"]
    ov_req = {"plot": plan.get("typo_plot")} if "typo_plot" in plan else {}
    ov_mem = {"built": plan["mismatch_built"]} if "mismatch_built" in plan else {}
    docs = [("REQ", "requerimento", "Requerimento de comunicação prévia (modelo do Anexo I)", "written", "requerente", *doc_request(c, ov_req)),
            ("CRP", "certidao-permanente", "Código de acesso à certidão permanente do registo predial", "written", "requerente",
             *doc_plain(c, "Código de acesso à certidão permanente do registo predial", req, f"Código de acesso à certidão permanente do registo predial: {random.Random(c['id']).randrange(1000, 9999)}-0000-0000 (fictício).")),
            ("TRPARQ", "termo-arquitetura", "Termo de responsabilidade do autor do projeto de arquitetura", "written", "arquiteto",
             *doc_term_author(c, arq, "arquitetura", "I", site=plan.get("wrong_site"), wording="wording" not in plan)),
            ("SRCARQ", "seguro-arquiteto", "Comprovativo de seguro de responsabilidade civil do autor do projeto de arquitetura", "written", "seguradora",
             *doc_insurance(c, arq, "a elaboração e subscrição do projeto de arquitetura", to=plan.get("expired"))),
            ("TRCP", "termo-coordenador", "Termo de responsabilidade do coordenador de projeto", "written", "arquiteto", *doc_term_coordinator(c, arq)),
            ("SRCCP", "seguro-coordenador", "Comprovativo de seguro de responsabilidade civil do coordenador de projeto", "written", "seguradora", *doc_insurance(c, arq, "a coordenação dos projetos")),
            ("TRPLAC", "termo-acessibilidades", "Termo de responsabilidade do autor do plano de acessibilidades", "written", "arquiteto", *doc_term_author(c, arq, "plano de acessibilidades")),
            ("TRDO", "termo-diretor-obra", "Termo de responsabilidade pela assunção da função de diretor de obra", "written", plan.get("wrong_signer", "diretor"), *doc_term_director(c, dire)),
            ("SRCDO", "seguro-diretor-obra", "Comprovativo de seguro de responsabilidade civil do diretor de obra", "written", "seguradora", *doc_insurance(c, dire, "a direção da obra")),
            ("CCDO", "contrato-diretor-obra", "Comprovativo de contratação do diretor de obra", "written", "requerente",
             *doc_plain(c, "Comprovativo de contratação do diretor de obra", req, f"Declara-se que {dire['name']} foi contratado para exercer a função de diretor de obra da {c['work']}, por contrato de 1 de outubro de 2026 (fictício).")),
            ("FOTO", "registo-fotografico", "Registo fotográfico da situação existente", "written", "arquiteto", *doc_photo(c, arq)),
            ("MDARQ", "memoria-descritiva", "Memória descritiva e justificativa", "written", "arquiteto", *doc_memory(c, ov_mem)),
            ("CEO", "calendarizacao", "Calendarização da execução da obra", "written", "arquiteto",
             *doc_plain(c, "Calendarização da execução da obra", arq, f"Início previsto dos trabalhos: {c['start']}. Duração prevista: {c['months']} meses.", facts=[("prazo_meses", str(c["months"]), "meses", 0)])),
            ("EOCT", "estimativa-custo", "Estimativa do custo total da obra", "written", "arquiteto",
             *doc_plain(c, "Estimativa do custo total da obra", arq, f"Estimativa do custo total da obra, baseada em quantidades e tipologias de trabalhos: {eur(c['cost'])} (valor fictício).", facts=[("custo_total", eur(c["cost"]), "", 0)])),
            ("OUTDOC", "estimativa-encargos", "Estimativa dos encargos urbanísticos", "written", "requerente",
             *doc_plain(c, "Estimativa dos encargos urbanísticos", req, f"Estimativa dos encargos urbanísticos, incluindo a taxa pela realização, manutenção e reforço de infraestruturas urbanísticas: {eur(int(c['cost'] * 0.013))} (simulação).")),
            ("MDPLAC", "memoria-acessibilidades", "Memória descritiva do plano de acessibilidades", "written", "arquiteto",
             *doc_plain(c, "Memória descritiva do plano de acessibilidades", arq, "O plano de acessibilidades demonstra a conformidade da operação com o regime jurídico da acessibilidade: percurso acessível desde a via pública até à entrada principal.")),
            ("PDPLAC", "pecas-acessibilidades", "Peças desenhadas do plano de acessibilidades", "drawn", "arquiteto", *doc_drawing(c, "Plano de acessibilidades", "ACS-01", "1:100", arq, "plan")),
            ("P10000", "planta-localizacao", "Planta de localização", "drawn", "arquiteto", *doc_drawing(c, "Planta de localização", "LOC-01", "1:1000", arq, "site")),
            ("LEVT", "levantamento-topografico", "Levantamento topográfico georreferenciado", "drawn", "engenheiro", *doc_drawing(c, "Levantamento topográfico georreferenciado", "TOP-01", "1:200", eng, "site")),
            ("PI", "planta-implantacao", "Planta de implantação", "drawn", "arquiteto", *doc_drawing(c, "Planta de implantação", "IMP-01", "1:200", arq, "site")),
            ("PLANT", "plantas", "Plantas", "drawn", "arquiteto", *doc_drawing(c, "Planta do piso 0", "ARQ-01", "1:100", arq, "plan")),
            ("ALC", "alcados", "Alçados", "drawn", "arquiteto", *doc_drawing(c, "Alçado principal", "ARQ-02", "1:100", arq, "section")),
            ("CORTES", "cortes", "Cortes", "drawn", "arquiteto", *doc_drawing(c, "Corte longitudinal", "ARQ-03", "1:100", arq, "section")),
            ("PC", "pormenores", "Pormenores de construção", "drawn", "arquiteto", *doc_drawing(c, "Pormenor de fachada e cobertura", "ARQ-04", "1:20", arq, "section"))]
    for term, ins, mem, drw, name in SPECIALTIES:
        docs += [(term, f"termo-{drw.lower()}", f"Termo de responsabilidade do autor do projeto de {name}", "written", "engenheiro", *doc_term_author(c, eng, name, "II")),
                 (ins, f"seguro-{drw.lower()}", f"Comprovativo de seguro do autor do projeto de {name}", "written", "seguradora", *doc_insurance(c, eng, f"a elaboração do projeto de {name}")),
                 (mem, f"memoria-{drw.lower()}", f"Memória descritiva do projeto de {name}", "written", "engenheiro",
                  *doc_plain(c, f"Memória descritiva do projeto de {name}", eng, f"Memória descritiva e justificativa do projeto de {name}, relativo à {c['work']} em {c['site']} (conteúdo sintético).")),
                 (drw, f"pecas-{drw.lower()}", f"Peças desenhadas do projeto de {name}", "drawn", "engenheiro", *doc_drawing(c, f"Projeto de {name}", f"{drw}-01", "1:100", eng, "plan"))]
    docs += [("TRFSCI", "termo-sci", "Termo de responsabilidade do autor da ficha de segurança contra incêndios", "written", "engenheiro", *doc_term_author(c, eng, "segurança contra incêndios em edifícios (ficha de segurança)", "II")),
             ("FSCI", "ficha-sci", "Ficha de segurança contra incêndios", "written", "engenheiro", *doc_plain(c, "Ficha de segurança contra incêndios", eng, "Ficha de segurança contra incêndios: utilização-tipo I (habitacional), 1.ª categoria de risco (conteúdo sintético).")),
             ("FEE", "ficha-estatistica", "Ficha de elementos estatísticos", "written", "requerente",
              *doc_plain(c, "Ficha de elementos estatísticos", req, f"Ficha de elementos estatísticos (Portaria n.º 235/2013): {c['work']}, {c['fogos']} fogo(s), {c['built']} m2 (sintético).")),
             ("ASAT", "apolice-acidentes", "Apólice de seguro de acidentes de trabalho", "written", "seguradora",
              *doc_plain(c, "Apólice de seguro de acidentes de trabalho", {"name": "Seguradora Exemplo, S.A."}, "Apólice de seguro de acidentes de trabalho n.º SIM-AT-0001, Empresa de Construção Exemplo, Lda. (fictícia), válida em 2026-2027.")),
             ("IMPIC", "alvara-impic", "Número do alvará emitido pelo IMPIC, I. P.", "written", "diretor",
              *doc_plain(c, "Número do alvará emitido pelo IMPIC, I. P.", dire, "Empresa de Construção Exemplo, Lda. (fictícia): alvará de empreiteiro n.º 00000-PUB-SIM (fictício), classe 3."))]
    return docs


def noise_doc(c, rng):
    """A file that is no element at all (the reader must say so)."""
    kind = rng.choice(["fatura", "cv", "carta"])
    p = c["people"]["requerente"]
    if kind == "fatura":
        return ("OUTDOC", "fatura-agua", "Fatura de água", doc_plain(c, "Fatura", p, f"Águas de Basto (fictícia). Consumidor {p['name']}. Período 2026-08. Consumo 23 m3. Total 31,40 €.")[0])
    if kind == "cv":
        return ("OUTDOC", "curriculo", "Curriculum vitae", doc_plain(c, "Curriculum vitae", p, f"{p['name']}. Formação: licenciatura (fictícia). Experiência: 12 anos (fictícia).")[0])
    return ("OUTDOC", "carta", "Carta", doc_plain(c, "Carta", p, f"Exmos. Senhores, venho por este meio juntar os elementos em falta ao meu pedido. Com os melhores cumprimentos, {p['name']}.")[0])


def plant(rng, c, n_err):
    plan, findings = {}, []
    choices = rng.sample(ERRORS, n_err)
    for e in choices:
        if e == "missing_required":
            code = rng.choice([x for x in REQUIRED_ALWAYS if x not in ("REQ", "OUTDOC")])
            plan.setdefault("omit", set()).add(code)
            ref = DOCS[code]["passages"][0].replace("anexo-", "")
            findings.append({"type": "missing_required", "target": {"slot": code}, "law": {"ref": ref, "quote": QUOTES.get(ref) or PORT[f"portaria-320-2026-1:anexo-{ref}"]["text"]}})
        elif e == "template_wording_missing":
            plan["wording"] = True
            findings.append({"type": "template_wording_missing", "target": {"slot": "TRPARQ"}, "law": {"ref": "VII.I", "quote": WORDING_I}})
        elif e == "unsigned":
            code = rng.choice(["TRDO", "TRCP", "TRPLAC", "TREECP"])
            plan.setdefault("unsigned", set()).add(code)
            findings.append({"type": "unsigned", "target": {"slot": code}, "law": {"ref": "VI.1", "quote": QUOTES["VI.1"]}})
        elif e == "not_pdf":
            code = rng.choice(["CORTES", "ALC", "PLANT", "FOTO"])
            plan.setdefault("not_pdf", set()).add(code)
            findings.append({"type": "not_pdf", "target": {"slot": code}, "law": {"ref": "VI.1.a", "quote": QUOTES["VI.1.a"]}})
        elif e == "not_pdfa":
            code = rng.choice(["MDPAP", "MDARQ", "CEO", "FSCI"])
            plan.setdefault("no_pdfa", set()).add(code)
            findings.append({"type": "not_pdfa", "target": {"slot": code}, "law": {"ref": "VI.1.a", "quote": QUOTES["VI.1.a"]}})
        elif e == "value_mismatch":
            plan["mismatch_built"] = c["built"] + rng.choice([-1, 1]) * rng.randrange(30, 120)
            findings.append({"type": "value_mismatch", "target": {"field": "area_total_construcao", "slots": ["REQ", "MDARQ"]}, "basis": "documents",
                             "values": {"REQ": f"{c['built']} m2", "MDARQ": f"{plan['mismatch_built']} m2"}})
        elif e == "impossible_value":
            plan["typo_plot"] = int(str(c["plot"])[:-1]) if c["plot"] >= 1000 else c["plot"] * 10
            findings.append({"type": "impossible_value", "target": {"field": "area_parcela", "slot": "REQ"}, "basis": "documents",
                             "values": {"area_parcela": f"{plan['typo_plot']} m2", "area_implantacao": f"{c['impl']} m2", "MDARQ": f"{c['plot']} m2"}})
        elif e == "wrong_site":
            plan["wrong_site"] = f"{rng.choice(STREETS)}, n.º {rng.randrange(1, 300)}, {rng.choice(FREGUESIAS)}, 4890-000 Celorico de Basto"
            findings.append({"type": "wrong_site", "target": {"slot": "TRPARQ"}, "basis": "documents", "values": {"REQ": c["site"], "TRPARQ": plan["wrong_site"]}})
        elif e == "expired_insurance":
            plan["expired"] = "2026-09-30"
            findings.append({"type": "expired_insurance", "target": {"slot": "SRCARQ"}, "basis": "documents", "values": {"validade_fim": "2026-09-30", "submetido": c["submitted"]},
                             "law": {"ref": "V.14", "quote": QUOTES["V.14"]}})
        elif e == "wrong_signer":
            plan["wrong_signer"] = "arquiteto"
            findings.append({"type": "wrong_signer", "target": {"slot": "TRDO"}, "basis": "documents", "values": {"declarante": c["people"]["diretor"]["name"], "assinante": c["people"]["arquiteto"]["name"]}})
    return plan, findings


def build_one(rng, cid, out_dir, n_err, with_noise):
    c = make_case(rng, cid)
    plan, findings = plant(rng, c, n_err)
    folder = out_dir / cid
    folder.mkdir(parents=True, exist_ok=True)
    files, labels = [], []
    docs = documents(c, plan)
    if with_noise:
        code, stem, title, d = noise_doc(c, rng)
        docs.append((code, stem, title, "written", "requerente", d, []))
    for code, stem, title, kind, signer, d, facts in docs:
        if code in plan.get("omit", set()):
            continue
        fname = f"{code}-{stem}.pdf"
        if code in plan.get("not_pdf", set()):
            data = G.png(640, 400, 90)
        else:
            fields = [(f"sintese.{k}", v) for k, _, v, _ in summary_rows(c, {"plot": plan.get("typo_plot")} if "typo_plot" in plan else {})] if code == "REQ" else None
            pdf = G.finish(d.render(), title, pdfa=code not in plan.get("no_pdfa", set()), fields=fields)
            data = pdf if code in plan.get("unsigned", set()) else G.sign(pdf, signer if signer != "seguradora" else "arquiteto")
        (folder / fname).write_bytes(data)
        signed_by = None if code in plan.get("unsigned", set()) or code in plan.get("not_pdf", set()) else signer
        files.append({"slot": code, "file": fname, "title": title, "kind": kind, "signed_by": signed_by})
        passages = DOCS.get(code, {}).get("passages", []) if stem not in ("fatura-agua", "curriculo", "carta") else []
        labels.append({"expediente": cid, "file": fname, "slot": code, "title": title, "kind": kind, "pages": len(d.pages), "is_pdf": code not in plan.get("not_pdf", set()),
                       "pdfa": code not in plan.get("no_pdfa", set()) and code not in plan.get("not_pdf", set()), "signed": signed_by is not None, "signer": signed_by,
                       "element": (f"portaria-320-2026-1:{passages[0]}" if passages else None), "elements": [f"portaria-320-2026-1:{p}" for p in passages],
                       "noise": stem in ("fatura-agua", "curriculo", "carta"),
                       "facts": [{"field": f, "value": v, "unit": u, "page": pg, "line": ln} for f, v, u, pg, ln in facts]})
    submission = {"expediente": cid, "simulated": True, "procedure": "cp-edificacao", "request": "CPEDI", "municipality": "Celorico de Basto",
                  "form_subject": "form:nopaper:celorico-de-basto:CP:CPEDI", "applicant": {"name": c["people"]["requerente"]["name"], "nif": NIF},
                  "site": c["site"], "operation": c["work"], "submitted_at": c["submitted"], "files": files}
    (folder / "submission.json").write_text(json.dumps(submission, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    key = {"expediente": cid, "case": c, "planted": sorted(findings, key=lambda f: f["type"]), "n_planted": len(findings),
           "always": [{"type": "missing_complement", "target": {"slot": "PI"}, "law": {"ref": "VI.1.b", "quote": QUOTES["VI.1.b"]}, "note": "no DWG can be produced here"},
                      {"status": "not_assessed", "type": "signature_qualification", "note": "test certificates"}]}
    (folder / "key.json").write_text(json.dumps(key, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    with open(folder / "labels.jsonl", "w", encoding="utf-8") as f:
        for l in labels:
            f.write(json.dumps(l, ensure_ascii=False) + "\n")
    return len(files), len(findings)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3); ap.add_argument("--seed", type=int, default=1); ap.add_argument("--out", default="training/expedientes")
    ap.add_argument("--sealed", action="store_true"); ap.add_argument("--max-errors", type=int, default=4)
    a = ap.parse_args()
    seed = 777_000 if a.sealed else a.seed
    out = ROOT / ("sealed/expedientes" if a.sealed else a.out)
    rng = random.Random(seed)
    tag = "S" if a.sealed else "T"
    tot_files = tot_err = 0
    for i in range(a.n):
        cid = f"{tag}{seed}-{i:04d}"
        n_err = rng.choice([0, 1, 1, 2, 2, 3, a.max_errors])
        nf, ne = build_one(rng, cid, out, n_err, with_noise=rng.random() < 0.5)
        tot_files += nf; tot_err += ne
        print(f"{cid}: {nf} files, {ne} planted")
    print(f"{a.n} expedientes in {out.relative_to(ROOT)}: {tot_files} files, {tot_err} planted errors")


if __name__ == "__main__":
    main()
