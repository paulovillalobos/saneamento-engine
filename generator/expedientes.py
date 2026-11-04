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

MEM_TITLES = ["Memória descritiva e justificativa", "Memória Descritiva", "MEMÓRIA DESCRITIVA E JUSTIFICATIVA", "Memória Descritiva e Justificativa"]
ATELIERS = ["DUPLODECIMETRO, ATELIER DE ARQUITECTOS", "TRAÇO VIVO - Arquitetura e Urbanismo, Lda.", "Gabinete de Projetos do Tâmega, Lda.", "ARQ+ENG Celorico, Unipessoal Lda.",
            "DEL | DEPARTAMENTO DE ESTUDOS E PROJETOS", "Atelier Basto Arquitetura"]
MONTHS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "setembro", "outubro"]
INDEX_HEADINGS = ["1. INTRODUÇÃO", "2. ÁREA DE INTERVENÇÃO", "3. ENQUADRAMENTO", "3.1. ENQUADRAMENTO JURÍDICO", "3.2. ENQUADRAMENTO NOS OBJETIVOS DE DESENVOLVIMENTO SUSTENTÁVEL",
                  "3.3. ENQUADRAMENTO URBANÍSTICO", "3.4. ANTECEDENTES PROCEDIMENTAIS", "3.4.1. CONSULTAS A ENTIDADES", "3.4.1.1. CONSULTAS DAS UNIDADES ORGÂNICAS DO UNIVERSO MUNICIPAL",
                  "3.4.1.2. CONSULTAS A ENTIDADES EXTERNAS AOS SERVIÇOS MUNICIPAIS", "3.4.2. ESCLARECIMENTOS ADICIONAIS", "4. PROGRAMA DE INTERVENÇÃO", "4.1. PROPOSTA ARQUITETÓNICA",
                  "4.2. INTEGRAÇÃO NA MORFOLOGIA E TECIDO URBANO ENVOLVENTE", "4.3. VIAS, ACESSOS E ESTACIONAMENTO", "4.4. INFRAESTRUTURAS", "4.5. ESPAÇOS VERDES",
                  "4.6. GESTÃO DE RESÍDUOS SÓLIDOS", "4.7. ACESSIBILIDADES", "4.8. SEGURANÇA CONTRA INCÊNDIOS", "5. QUADRO SINÓPTICO", "6. ANEXOS"]

def _real_sentences():
    """Sentences of the real public memórias (sources/real/memorias), texture for long generated memórias; loaded once, no PDF text reused as a key."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return []
    out = []
    for f in sorted((ROOT / "sources" / "real" / "memorias").glob("*.pdf")):
        try:
            t = " ".join((pg.extract_text() or "") for pg in PdfReader(str(f)).pages)
        except Exception:
            continue
        for sent in re.split(r"(?<=[.;])\s+", " ".join(t.split())):
            if 60 <= len(sent) <= 260 and len(sent.split()) >= 8 and sum(ch.isupper() for ch in sent) < 0.2 * sum(ch.isalpha() for ch in sent) \
                    and not re.search(r"\d{2,}\s?m2|m²|fogos|€|\.{4,}|www\.|@|\|", sent):
                out.append(sent.strip())
    return out


REAL = _real_sentences()

# D16 (round 10): documents as long as the real ones. Real memórias run 5–34 pages, real norms, manuals and regulations 4–40; ours ran 1–6.
# stretch() lengthens a document with numbered chapters of plain text until it reaches a target page count; the facts keep their pages.
MEM_CHAPTERS = ["SOLUÇÕES CONSTRUTIVAS E MATERIAIS", "ACESSIBILIDADES", "SEGURANÇA CONTRA INCÊNDIO", "COMPORTAMENTO TÉRMICO E ENERGIA", "CONDICIONAMENTO ACÚSTICO",
                "REDES DE ÁGUAS E ESGOTOS", "REDE ELÉTRICA E TELECOMUNICAÇÕES", "ARRANJOS EXTERIORES", "GESTÃO DE RESÍDUOS DE CONSTRUÇÃO E DEMOLIÇÃO", "ESTALEIRO E FASEAMENTO",
                "CONDICIONANTES E SERVIDÕES", "ENQUADRAMENTO NO PDM", "DESCRIÇÃO DOS ESPAÇOS", "ÁREAS E ÍNDICES", "QUADRO SÍNTESE", "CONSIDERAÇÕES FINAIS", "ANEXOS"]
REG_TEMPLATES = ["Artigo {n}.º — Para efeitos do presente regulamento, entende-se por {X} o documento técnico que acompanha o pedido e identifica a solução adotada.",
                 "Artigo {n}.º — O pedido de comunicação prévia é instruído com os elementos previstos na Portaria n.º 320/2026/1, em formato digital, nos termos do artigo 8.º-A do RJUE.",
                 "Artigo {n}.º — A {X} é apresentada em ficheiro autónomo, assinado digitalmente pelo técnico autor, com termo de responsabilidade nos termos do artigo 10.º do RJUE.",
                 "Artigo {n}.º — Compete à Câmara Municipal de {M} verificar a instrução do pedido no prazo de {d} dias, convidando o requerente a corrigir ou completar os elementos em falta.",
                 "Artigo {n}.º — As peças desenhadas são apresentadas à escala adequada, georreferenciadas no sistema PT-TM06/ETRS89, em formato DWFx ou DWG.",
                 "{n}. Os projetos de especialidade, designadamente o projeto de {X}, são acompanhados dos respetivos termos de responsabilidade e das declarações das ordens profissionais.",
                 "{n}. O incumprimento do disposto no número anterior determina a rejeição liminar da comunicação prévia ou o convite ao aperfeiçoamento, nos termos do artigo 11.º do RJUE.",
                 "{n}. Nas operações urbanísticas em solo rústico aplicam-se, com as devidas adaptações, as regras constantes do Plano Diretor Municipal de {M} e do presente regulamento.",
                 "{n}. A estimativa do custo total da obra é calculada com base nos valores de referência fixados anualmente por deliberação da Câmara Municipal de {M}.",
                 "{n}. O prazo de execução das obras é fixado na comunicação prévia e pode ser prorrogado uma vez, por período não superior a metade do prazo inicial.",
                 "{n}. As taxas devidas pela realização, manutenção e reforço de infraestruturas urbanísticas são liquidadas nos termos do Regulamento Municipal de Taxas de {M}.",
                 "{n}. O requerente indica, no formulário, o técnico autor de cada peça e o diretor de obra, com os números de inscrição nas respetivas ordens profissionais.",
                 "Secção {n} — Disposições relativas ao {X}: aplicam-se as normas técnicas em vigor, nomeadamente as normas europeias EN e as disposições do RGEU.",
                 "{n}. Os ficheiros são nomeados de acordo com o manual de instrução digital em vigor, com o prefixo correspondente ao tipo de peça e o número de ordem.",
                 "{n}. A Câmara Municipal de {M} pode solicitar pareceres a entidades externas quando a operação urbanística incida sobre áreas sujeitas a servidões ou restrições de utilidade pública.",
                 "{n}. Os elementos instrutórios são apresentados em formato PDF/A, com resolução mínima de 300 dpi quando resultem de digitalização, e não podem exceder 20 MB por ficheiro."]
REG_HEADINGS = ["CAPÍTULO I — DISPOSIÇÕES GERAIS", "CAPÍTULO II — INSTRUÇÃO DOS PEDIDOS", "CAPÍTULO III — ELEMENTOS INSTRUTÓRIOS", "CAPÍTULO IV — PEÇAS DESENHADAS", "CAPÍTULO V — PROJETOS DE ESPECIALIDADE",
                "CAPÍTULO VI — PRAZOS E TRAMITAÇÃO", "CAPÍTULO VII — TAXAS", "CAPÍTULO VIII — FISCALIZAÇÃO", "CAPÍTULO IX — DISPOSIÇÕES FINAIS E TRANSITÓRIAS", "ANEXO I — MODELOS", "ANEXO II — NORMAS DE NOMEAÇÃO DE FICHEIROS"]


def reg_sentence(rng, n):
    return rng.choice(REG_TEMPLATES).format(n=n, X=rng.choice(ELEMENT_NAMES), M=rng.choice(MUNIS_PT), d=rng.choice([8, 10, 15, 20, 30]))


def stretch(d, rng, target_pages, pool="memoria", first=8, header=None):
    """Add numbered chapters until the document has at least target_pages pages (each chapter 3–9 paragraphs). pool: 'memoria' draws from the
    real memória sentences, 'regulamento' from article templates. header (if given) is printed small at the top of each new chapter, as the
    letterheads and footers that real documents repeat on every page."""
    k, n = first, rng.randrange(10, 40)
    heads = MEM_CHAPTERS if pool == "memoria" else REG_HEADINGS
    while len(d.pages) < target_pages:
        if header:
            d.text(header, size=7)
        d.text(f"{k}. {heads[(k - first) % len(heads)]}" if pool == "memoria" else heads[(k - first) % len(heads)], bold=True)
        for _ in range(rng.randrange(3, 10)):
            if pool == "memoria":
                d.text(rng.choice(REAL) if REAL else "Texto descritivo da solução adotada.")
            else:
                d.text(reg_sentence(rng, n)); n += 1
        k += 1
    return d
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


def doc_memory(c, override=None, long=False, rng=None):
    o = override or {}
    a = c["people"]["arquiteto"]
    title = rng.choice(MEM_TITLES) if (long and rng) else "Memória descritiva e justificativa"
    d = G.Doc(title)
    if long and REAL and rng:
        atelier = rng.choice(ATELIERS)
        other = rng.random() < 0.3   # the header names another operation (loteamento, alteração de alvará, obras de urbanização): still the item-9 piece (D12)
        if rng.random() < 0.35:
            # the memória written as the reply to the council's ofício (real pattern: company header, "Resposta ao ofício", date, atelier footer)
            d.text(f"{c['people']['requerente']['name']}", size=9)
            op = rng.choice(["Licenciamento de operação de loteamento", "Alteração à licença de loteamento", "Obras de urbanização"]) if other else "Comunicação prévia de obras de edificação"
            d.text(f"{op} - Resposta ao ofício n.º {rng.randrange(1000, 9999)}/DGU.SAA, de {rng.randrange(1, 28):02d}/{rng.randrange(1, 12):02d}/2026", size=9)
            d.text(f"{c['site']}, Celorico de Basto", size=9)
            d.text(f"{title}                                       {rng.choice(MONTHS)} de 2026", size=9)
            d.text(f"{atelier}                                                                                                     1", size=7)
            d.text("1. NOTA EXPLICATIVA", bold=True)
            if other:
                d.text("A proposta de operação de loteamento não foi alterada no que respeita ao traçado, número de lotes e as suas características, áreas de construção e "
                       "implantação, ocupação e áreas de cedência, assim como todos os restantes indicadores urbanísticos. No entanto, considera-se útil a transcrição dos dados caracterizadores desta proposta.")
            d.text(f"Para cumprimento do ofício acima referido, procedeu-se à reformulação dos elementos instrutórios da operação urbanística pretendida ({c['work']}).")
            for _ in range(rng.randrange(2, 5)):
                d.text(rng.choice(REAL))
            d.text("2. DESCRIÇÃO DA OPERAÇÃO", bold=True)
        else:
            # cover page, then an index with dotted leaders and sub-numbering, then the body (real pattern: Cascais/Valongo memórias)
            if other:
                d.text(rng.choice([f"Alteração à Licença de Loteamento titulada pelo alvará de loteamento n.º {rng.randrange(100, 1300)}",
                                   f"Operação de loteamento - {c['site']}", f"Obras de urbanização - {c['site']}"]))
                d.text(rng.choice([f"Requerente: MUNICÍPIO DE {rng.choice(MUNIS_PT).upper()}", f"Requerente: {c['people']['requerente']['name']}"]))
                d.gap(40)
                d.text("DEL I Departamento de Estudos e Loteamentos", size=9)
                d.text("DLOT I Divisão de Loteamentos", size=9)
                atelier = "DEL | DEPARTAMENTO DE ESTUDOS E LOTEAMENTOS"
            else:
                d.text(f"{c['work']} - {c['site']}")
                d.text(f"Requerente: {c['people']['requerente']['name']}")
                d.gap(40)
                d.text(atelier, size=9)
            d._new_page()
            d.text(f"{atelier}    |    {title}", size=7)
            d.text(f"{atelier[:3].upper()} | {rng.choice(['DIVISÃO DE PROJETO', 'DEPARTAMENTO DE ARQUITETURA', 'GABINETE TÉCNICO'])}", size=7)
            d.text("2", size=7)
            d.text("ÍNDICE", bold=True)
            page_no = 3
            for h in INDEX_HEADINGS[: rng.randrange(14, len(INDEX_HEADINGS) + 1)]:
                dots = "." * rng.randrange(40, 90)
                d.text(f"{h} {dots} {page_no}", size=9)
                page_no += rng.randrange(0, 3)
            d._new_page()
            d.text(f"{atelier}    |    {title}", size=7)
            d.text("3", size=7)
            d.text("1.  INTRODUÇÃO", bold=True)
            d.text(f"O presente documento constitui o enquadramento e a fundamentação técnica do pedido de {c['work'].lower()}, sito em {c['site']}, freguesia do concelho de "
                   f"Celorico de Basto, requerido por {c['people']['requerente']['name']}, ao abrigo do disposto no Regime Jurídico da Urbanização e da Edificação.")
            for _ in range(rng.randrange(2, 5)):
                d.text(rng.choice(REAL))
            d.text("2.  ÁREA DE INTERVENÇÃO", bold=True)
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
    if long and REAL and rng:
        for h in ("3. ENQUADRAMENTO", "3.1. ENQUADRAMENTO JURÍDICO", "3.2. ENQUADRAMENTO URBANÍSTICO", "4. PROGRAMA DE INTERVENÇÃO"):
            d.text(h, bold=True)
            for _ in range(rng.randrange(3, 8)):
                d.text(rng.choice(REAL))
        d.text("5. QUADRO SINÓPTICO", bold=True)
    pg_q = d.text(f"Quadro sinóptico: superfície do terreno {o.get('plot', c['plot'])} m2; área de implantação {c['impl']} m2; área total de construção "
                  f"{o.get('built', c['built'])} m2; área permeável {c['perm']} m2; área impermeabilizada {c['imperm']} m2; volume {c['volume']} m3; "
                  f"altura da edificação {str(c['height']).replace('.', ',')} m; altura da fachada {str(c['facade']).replace('.', ',')} m.", tag="quadro")
    extra = []
    if rng:
        # D14: the body goes on (the cost and the prazo land on later pages of a long memória); a prazo written in DAYS carries no
        # prazo_meses fact — the question "em meses" is then answered null (the days-vs-months trap of the fresh batch)
        if long and REAL:
            for h in ("6. SOLUÇÕES CONSTRUTIVAS", "7. REDES E INFRAESTRUTURAS"):
                d.text(h, bold=True)
                for _ in range(rng.randrange(4, 9)):
                    d.text(rng.choice(REAL))
            # D16: as long as the real ones (5–34 pages); the cost and the prazo land somewhere in the second half, not always on the last page
            target = rng.randrange(6, 25)
            stretch(d, rng, max(len(d.pages), target - rng.randrange(0, 4)), header=f"{title}    |    {c['site']}" if rng.random() < 0.6 else None)
            if rng.random() < 0.3:
                d.text("8. ESTIMATIVA DO CUSTO DA OBRA", bold=True)
                pg_c = d.text(f"O custo total da obra estima-se em {eur(c['cost'])}, com base nas áreas acima e nos valores de referência de custo por m2.", tag="custo")
                extra.append(("custo_total", eur(c["cost"]), "", pg_c, None))
        r2 = rng.random()
        if r2 < 0.25:
            pg_p = d.text(f"O prazo de execução previsto para a obra é de {c['months']} meses.", tag="prazo")
            extra.append(("prazo_meses", str(c["months"]), "meses", pg_p, None))
        elif r2 < 0.5:
            d.text(f"O prazo de execução previsto para a obra é de {rng.choice([60, 90, 120, 180, 240, 365])} dias a contar da data de início dos trabalhos.")
        if long and REAL:
            stretch(d, rng, len(d.pages) + rng.randrange(0, 4), first=20)   # a few more chapters after the facts (quadro síntese, anexos)
    sig(d, c, a)
    return d, [("area_total_construcao", str(o.get("built", c["built"])), "m2", pg_b, None), ("area_parcela", str(o.get("plot", c["plot"])), "m2", pg_q, None),
               ("pisos_acima_soleira", str(c["pisos"]), "", pg_b, None)] + extra


def doc_term_author(c, p, project, kind="I", site=None, wording=True):
    d = G.Doc(f"Termo de responsabilidade do autor do projeto de {project}")
    r_ = random.Random(c["id"] + project + kind + "blank")
    if r_.random() < 0.12:
        d.text("A presente minuta de termo de responsabilidade de autoria de projeto transcreve a redação prevista no anexo VII da Portaria n.º 320/2026/1.", size=9)
        d.text("… (a) … (b), morador na …, contribuinte n.º …, inscrito na ... (c) sob o n.º …, declara, para efeitos do disposto no n.º 1 do artigo 10.º do Decreto-Lei n.º 555/99, "
               "de 16 de dezembro, na sua redação atual, que o projeto de … (a), de que é autor, relativo à obra de … (e), localizada em … (f), cujo … (g) foi … (h) por … (i):")
        d.text("a) Observa as normas legais e regulamentares aplicáveis, designadamente as normas técnicas de construção em vigor … (j);")
        d.text("b) Está conforme com os planos municipais ou intermunicipais de ordenamento do território aplicáveis à pretensão, bem como com … (k).")
        d.text("(a) Indicar o tipo de projeto. (b) Indicar nome e habilitação do autor. (c) Indicar associação pública de natureza profissional.", size=8)
        return d, []
    if random.Random(c["id"] + project + kind).random() < 0.15:
        d.text("A presente minuta de termo de responsabilidade de autoria de projeto transcreve a redação prevista no anexo VII, a que se refere o artigo 7.º, "
               "da Portaria n.º 320/2026/1, de 2 de setembro.", size=9)
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
    if random.Random(c["id"] + "coordblank").random() < 0.12:
        d.text("A presente minuta de termo de responsabilidade do coordenador de projetos transcreve a redação presente no anexo VII da Portaria n.º 320/2026/1.", size=9)
        d.text("Termo de responsabilidade do coordenador do projeto de … (a) … (b), morador na …, contribuinte n.º …, inscrito na … (c) sob o n.º …, declara, para efeitos "
               "do disposto no n.º 1 do artigo 10.º do Decreto-Lei n.º 555/99, de 16 de dezembro, na sua redação atual, que o projeto de … (a), de que é coordenador, "
               "relativo à obra de … (d), localizada em … (e), cujo … (f) foi … (g) por … (h):")
        d.text("a) Observa as normas legais e regulamentares aplicáveis, designadamente … (i); b) Está conforme com os planos municipais ou intermunicipais de ordenamento "
               "do território aplicáveis à pretensão, bem como com (j); c) Atesta a compatibilidade entre os projetos necessários à execução da operação urbanística.")
        d.text("… (data). … (assinatura) (k). (l) Código de verificação das competências profissionais.")
        d.text("Instruções de preenchimento: (a) Identificar o tipo de operação urbanística. (b) Indicar nome e habilitação do autor do projeto. (c) Indicar associação "
               "pública de natureza profissional, quando for o caso. (d) Indicar a natureza da operação urbanística a realizar.", size=8)
        return d, []
    if random.Random(c["id"] + "coord").random() < 0.15:
        d.text("A presente minuta de termo de responsabilidade do coordenador de projeto transcreve a redação prevista no anexo VII da Portaria n.º 320/2026/1, de 2 de setembro.", size=9)
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
            ("MDARQ", "memoria-descritiva", "Memória descritiva e justificativa", "written", "arquiteto", *doc_memory(c, ov_mem, long=plan.get("long_memoria", False), rng=random.Random(c["id"] + "m"))),
            ("CEO", "calendarizacao", "Calendarização da execução da obra", "written", "arquiteto",
             *doc_plain(c, "Calendarização da execução da obra", arq, f"Início previsto dos trabalhos: {c['start']}. Duração prevista: {c['months']} meses.", facts=[("prazo_meses", str(c["months"]), "meses", 0)])),
            ("EOCT", "estimativa-custo", "Estimativa do custo total da obra", "written", "arquiteto", *doc_estimate(c, arq, random.Random(c["id"] + "eoct"))),
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
                  *doc_special_memory(c, name, eng, random.Random(c["id"] + mem))),
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
    """A file that is no element at all (the reader must say so): invoice, CV, letter, a municipal checklist, a regulation extract, a file-naming list."""
    kind = rng.choice(["fatura", "cv", "carta", "ficha", "regulamento", "lista"])
    p = c["people"]["requerente"]
    if kind == "ficha":
        d = G.Doc("Ficha de verificação de elementos instrutórios")
        d.text("Conjuntamente com o requerimento, o pedido deve ser instruído com os seguintes elementos (assinale):")
        for i, el in enumerate(["Certidão da descrição e de todas as inscrições em vigor", "Delimitação da área objeto da operação em planta de localização", "Memória descritiva e justificativa",
                                "Termos de responsabilidade dos autores dos projetos", "Levantamento topográfico", "Estimativa do custo total da obra", "Calendarização da execução"], 1):
            d.text(f"{i}) {el}   Sim [ ]  Não [ ]")
        return ("OUTDOC", "ficha-verificacao", "Ficha de verificação", d)
    if kind == "regulamento":
        d = G.Doc("Regulamento municipal de instrução de processos em formato digital (extrato)")
        for i, t in enumerate(["A apresentação de pedidos é realizada informaticamente através de plataforma eletrónica disponibilizada na página do município.",
                               "Os elementos são apresentados sob a forma de ficheiros em formato digital nos termos do presente regulamento.",
                               "O nome dos ficheiros não pode ter mais de 40 caracteres alfanuméricos, sem espaços nem caracteres especiais.",
                               "Os ficheiros individuais que constituem o processo não podem ultrapassar os tamanhos máximos fixados no anexo."], 1):
            d.text(f"Artigo {i}.º", bold=True); d.text(t)
        return ("OUTDOC", "regulamento-extrato", "Regulamento municipal (extrato)", d)
    if kind == "lista":
        d = G.Doc("Lista de elementos instrutórios com nomeação dos ficheiros")
        d.text("Designação do elemento instrutório | Nome do ficheiro | Formato", bold=True)
        for el, nm in [("Requerimento", "01_requerimento.pdf"), ("Memória descritiva e justificativa", "02_memoria.pdf"), ("Planta de localização", "03_planta_loc.pdf"),
                       ("Projeto de arquitetura - plantas", "04_plantas.dwfx"), ("Termo de responsabilidade do autor do projeto de arquitetura", "05_tr_arq.pdf")]:
            d.text(f"{el} | {nm} | PDF/A")
        return ("OUTDOC", "lista-elementos", "Lista de elementos instrutórios", d)
    if kind == "fatura":
        return ("OUTDOC", "fatura-agua", "Fatura de água", doc_plain(c, "Fatura", p, f"Águas de Basto (fictícia). Consumidor {p['name']}. Período 2026-08. Consumo 23 m3. Total 31,40 €.")[0])
    if kind == "cv":
        return ("OUTDOC", "curriculo", "Curriculum vitae", doc_plain(c, "Curriculum vitae", p, f"{p['name']}. Formação: licenciatura (fictícia). Experiência: 12 anos (fictícia).")[0])
    return ("OUTDOC", "carta", "Carta", doc_plain(c, "Carta", p, f"Exmos. Senhores, venho por este meio juntar os elementos em falta ao meu pedido. Com os melhores cumprimentos, {p['name']}.")[0])


ELEMENT_NAMES = ["memória descritiva e justificativa", "levantamento topográfico", "planta de implantação", "projeto de estabilidade e fundações",
                 "plano de acessibilidades", "projeto de segurança contra incêndio em edifícios", "projeto de águas pluviais", "projeto de redes prediais de água e esgotos",
                 "projeto de infraestruturas de telecomunicações (ITED)", "estimativa do custo total da obra", "calendarização da execução da obra", "planta de localização",
                 "termos de responsabilidade dos autores dos projetos", "registo fotográfico", "projeto de condicionamento acústico", "projeto de comportamento térmico"]
MUNIS_PT = ["Seixal", "Viseu", "Leiria", "Gouveia", "Figueira da Foz", "Estarreja", "Benavente", "Loures", "Castro Daire", "Vila Nova de Cerveira", "Alfândega da Fé", "Anadia", "Amarante", "Valpaços"]
NOISE_PREFIX = "x-"


def slug(title):
    t = title.lower()
    for a_, b_ in (("á", "a"), ("à", "a"), ("ã", "a"), ("â", "a"), ("é", "e"), ("ê", "e"), ("í", "i"), ("ó", "o"), ("ô", "o"), ("õ", "o"), ("ú", "u"), ("ç", "c")):
        t = t.replace(a_, b_)
    return re.sub(r"[^a-z0-9 ]", " ", t)


def noise_about(c, rng):
    """A document ABOUT an element (norm, postura, guide, technical note, criteria, deliberation, internal note, project sheet, filling instructions, manual,
    diagnostic, tender spec) or a termo of ANOTHER procedure: real expedientes carry these, and none of them is the element it talks about."""
    kind = rng.choice(["norma", "postura", "guia", "nota", "criterios", "deliberacao", "informacao", "ficha-projeto", "instrucoes", "termo-outro", "termo-outro",
                       "memoria-empresa", "manual", "diagnostico", "caderno", "anexo-regulamento", "analise", "nota-explicativa", "memoria-candidatura",
                       "indice-pecas", "indice-pecas", "parecer-externo"])   # D14: an index of pieces is not the pieces; an opinion's element list is not an element
    X = rng.choice(ELEMENT_NAMES); M = rng.choice(MUNIS_PT); n = rng.randrange(1, 40)
    X = re.sub(r"^projeto de ", "", X)  # "Postura referente a projetos de estabilidade", not "de projeto de estabilidade"
    if kind == "norma":
        d = G.Doc(f"NORMA DE INSTRUÇÃO DE PROCESSO NIP-{n:02d}")
        d.text(f"Revisão: A{rng.randrange(1, 9)}    Data: {rng.randrange(1, 28):02d}/{rng.randrange(1, 12):02d}/2026    CÂMARA MUNICIPAL DE {M.upper()}    Proc. N.º:", size=9)
        d.text("COMUNICAÇÃO PRÉVIA DE OBRAS DE EDIFICAÇÃO", bold=True)
        d.text("OBJETIVO E ÂMBITO DE APLICAÇÃO", bold=True)
        d.text("Definir o modo de instruir o processo de comunicação prévia de obras de edificação ao abrigo do Regime Jurídico da Urbanização e da Edificação e da Portaria n.º 320/2026/1.")
        d.text("ELEMENTOS A APRESENTAR", bold=True)
        for i, el in enumerate(rng.sample(ELEMENT_NAMES, 6), 1):
            d.text(f"{i}. {el[0].upper() + el[1:]}, em formato PDF/A" + (", assinado digitalmente pelo autor" if i % 2 else ", georreferenciado no sistema PT-TM06/ETRS89") + ";")
        d.text(f"A {X} deve ser apresentada em ficheiro autónomo, com o nome normalizado previsto no manual de instrução digital.")
        if rng.random() < 0.5:
            d.text("ELEMENTOS ESPECÍFICOS", bold=True)
            for i, el in enumerate(ELEMENT_NAMES, 7):
                d.text(f"{i}. {el[0].upper() + el[1:]}: " + rng.choice(["em PDF/A, assinado digitalmente;", "à escala adequada, em DWFx;", "quando exigível nos termos da lei;",
                                                                        "com termo de responsabilidade do autor;", "georreferenciado, em DWG;"]))
            d.text("DISPOSIÇÕES FINAIS", bold=True)
            d.text("A falta de qualquer dos elementos determina a rejeição liminar ou o convite ao aperfeiçoamento, nos termos do artigo 11.º do RJUE.")
    elif kind == "postura":
        d = G.Doc(f"Postura Municipal Referente a Projetos de {X[0].upper() + X[1:]}")
        d.text(f"MUNICÍPIO DE {M.upper()}    CÂMARA MUNICIPAL    Data: 2026/{rng.randrange(1, 12):02d}/{rng.randrange(1, 28):02d}    Página 1 de 1", size=9)
        d.text(f"Os projetos de {X} devem ser instruídos com os seguintes elementos:")
        d.text("1. Planta topográfica, a fornecer pelo departamento competente, onde se assinale o lote onde se pretende executar a obra;")
        d.text(f"2. Memória descritiva e justificativa contendo a identificação do requerente, a localização, a composição e o tipo de utilização do edifício e a descrição da solução adotada para o {X};")
        d.text("3. Peças desenhadas em escala adequada, com a indicação dos materiais, diâmetros, secções e cotas;")
        d.text("4. Termo de responsabilidade do autor do projeto, nos termos do artigo 10.º do RJUE.")
    elif kind == "guia":
        d = G.Doc(f"Guia Técnico para Projetos de {X[0].upper() + X[1:]}")
        d.text(f"GTPP_Rev.:{rng.randrange(1, 5):02d}    01/01/2026", size=9)
        d.text("1. ÂMBITO DE APLICAÇÃO E OBJETIVOS", bold=True)
        d.text(f"O presente guia tem como objetivo definir as normas para elaboração e instrução dos projetos particulares de {X}, com vista à sua apreciação pelos serviços municipais de {M}.")
        d.text("2. INSTRUÇÃO DO PROJETO", bold=True)
        d.text(f"O projeto deve incluir: a) memória descritiva, da qual constem a descrição da conceção do sistema, materiais e acessórios; b) cálculos justificativos; c) peças desenhadas; d) termo de responsabilidade do autor.")
        d.text("3. NORMAS APLICÁVEIS", bold=True)
        d.text("Decreto Regulamentar n.º 23/95, de 23 de agosto; Decreto-Lei n.º 194/2009, de 20 de agosto; normas europeias EN aplicáveis.")
        if rng.random() < 0.5:
            for i, h in enumerate(["CONCEÇÃO DO SISTEMA", "MATERIAIS E ACESSÓRIOS", "DIMENSIONAMENTO", "PEÇAS DESENHADAS", "ENTREGA E APRECIAÇÃO"], 4):
                d.text(f"{i}. {h}", bold=True)
                for _ in range(rng.randrange(1, 3)):
                    d.text(rng.choice(REAL) if REAL else "Disposição aplicável.")
    elif kind == "nota":
        d = G.Doc(f"NOTA TÉCNICA N.º {n:02d} — PROJETOS DE {X.upper()}")
        d.text(f"PÁGINA 1/{rng.randrange(4, 12)}", size=8)
        d.text("OBJETIVO", bold=True)
        d.text(f"De acordo com a legislação em vigor, a presente nota técnica estabelece o conteúdo mínimo dos projetos de {X} apresentados para apreciação, nomeadamente a memória descritiva e justificativa e as peças desenhadas.")
        d.text("QUADRO I — PEÇAS ESCRITAS", bold=True)
        d.text("Memória descritiva e justificativa | Cálculos | Termo de responsabilidade | Ficha de segurança (quando aplicável)")
        d.text("QUADRO II — PEÇAS DESENHADAS", bold=True)
        d.text("Planta de localização 1:1000 | Plantas 1:100 | Cortes 1:100 | Pormenores")
    elif kind == "criterios":
        d = G.Doc("ANEXO IV — Critério para elaboração dos Levantamentos Topográficos e Cadastrais")
        d.text(f"Município de {M} • N.I.P.C.: 5{rng.randrange(10000000, 99999999)} • Sítio: www.cm-{M.lower().replace(' ', '')}.pt", size=8)
        d.text("1. O levantamento topográfico será efetuado à escala 1:500, podendo determinados pormenores justificar a escala 1:200.")
        d.text("2. Todas as peças desenhadas em formato DWG ou DXF, em planimetria e altimetria, deverão estar referenciadas ao sistema de coordenadas PT-TM06/ETRS89.")
        d.text("3. O levantamento inclui muros, lancis, caixas de visita, postes, árvores e todas as infraestruturas visíveis, com layers independentes.")
        d.text("4. A planta de implantação é desenhada sobre o levantamento topográfico e identifica a parcela, as confrontações e a implantação proposta.")
    elif kind == "deliberacao":
        d = G.Doc(f"Cópia de parte da ata da reunião de 2026-{rng.randrange(1, 12):02d}-{rng.randrange(1, 28):02d}")
        d.text(f"Ponto {n} – MINUTAS DOS TERMOS DE RESPONSABILIDADE", bold=True)
        d.text(f"Parecer da Divisão de Obras Particulares, de {rng.randrange(1, 28):02d}.{rng.randrange(1, 12):02d}.2026")
        d.text("Com a publicação da Portaria n.º 320/2026/1, que identifica os elementos instrutórios dos procedimentos previstos no Regime Jurídico da Urbanização e Edificação, "
               "foram elaboradas as minutas dos termos de responsabilidade do autor do projeto, do coordenador de projeto, do autor do plano de acessibilidades e do diretor de obra.")
        d.text("DELIBERAÇÃO: Deliberado por unanimidade validar as minutas dos termos de responsabilidade, que ficam arquivadas em anexo à presente ata.", bold=True)
    elif kind == "informacao":
        d = G.Doc(f"INFORMAÇÃO n.º {n}/2026")
        d.text(f"Município de {M} — Câmara Municipal    DIVISÃO DE URBANISMO E TERRITÓRIO    DATA: {rng.randrange(1, 28):02d}/{rng.randrange(1, 12):02d}/2026    NIPG: {rng.randrange(100, 999)}/26", size=9)
        d.text("DE: Chefe de Divisão    PARA: Vereador do Urbanismo", size=9)
        d.text(f"ASSUNTO: Competência dos técnicos para subscrever {X}", bold=True)
        d.text(f"Tendo presente o modelo de termo de responsabilidade do anexo VII da Portaria n.º 320/2026/1, coloca-se a questão de saber se a {X} pode ser subscrita por engenheiro técnico ou apenas por arquiteto ou engenheiro, nos termos da Lei n.º 31/2009.")
        d.text("Propõe-se que os serviços aceitem a subscrição por qualquer técnico habilitado nos termos da lei, mediante declaração da respetiva associação pública profissional.")
    elif kind == "ficha-projeto":
        d = G.Doc("Ficha de Projeto")
        d.text(f"Designação do Projeto | Reabilitação da Escola Básica de {rng.choice(['Favaios', 'Vilela', 'Fornos', 'Codeçoso', 'Gémeos'])}")
        d.text(f"Código do Projeto | NORTE-08-{rng.randrange(1000, 9999)}-FEDER-{rng.randrange(100000, 999999)}")
        d.text("Objetivo Principal | Adequar a construção antiga às novas exigências funcionais do edifício como estabelecimento de ensino")
        d.text(f"Entidade Beneficiária | Município de {M}    Data de aprovação | 2026-{rng.randrange(1, 12):02d}-{rng.randrange(1, 28):02d}")
        d.text(f"Custo elegível | {eur(rng.randrange(80, 900) * 1000)}    Apoio Financeiro da União Europeia | {eur(rng.randrange(60, 700) * 1000)}")
    elif kind == "instrucoes":
        d = G.Doc("Instruções Preenchimento_Q3")
        d.text("OBJETIVO E ENQUADRAMENTO LEGAL", bold=True)
        d.text("INQUÉRITO AOS PROJETOS DE OBRAS DE EDIFICAÇÃO E DEMOLIÇÃO DE EDIFÍCIOS (Q3). Por favor, leia com atenção as instruções que se seguem e cumpra o prazo estabelecido para o preenchimento do questionário.")
        d.text("Informações Gerais: Processo Interno (A0410/A0420/A0430/A0431)    Tipo de Procedimento (A0600)    LICENÇA DE OPERAÇÕES URBANÍSTICAS (conceito 3084)    COMUNICAÇÃO PRÉVIA DE OPERAÇÕES URBANÍSTICAS (conceito 3083)")
        d.text("Campos a preencher: número de fogos, área bruta de construção, número de pisos, tipo de obra, uso principal. Estes campos devem corresponder à informação registada no projeto.")
    elif kind == "termo-outro":
        which = rng.choice(["utilizacao", "conclusao", "rececao-prov", "rececao-def"])
        who = c["people"]["diretor"]
        if which == "utilizacao":
            d = G.Doc("Termo de Responsabilidade")
            d.text(f"Exmo. Senhor Presidente da Câmara Municipal de {M}")
            d.text(f"{who['name']}, morador na {who['address']}, contribuinte n.º {NIF}, inscrito na {who['body']} sob o n.º {who['number']}, declara, para efeitos do disposto no artigo 63.º do "
                   f"Decreto-Lei n.º 555/99, de 16 de dezembro, na sua redação atual, na qualidade de técnico, que a utilização de edifício ou fração, sem operação urbanística prévia, localizado em {c['site']}, pressupõe:")
            d.text("A conformidade da utilização prevista com as normas legais e regulamentares que fixam os usos e utilizações admissíveis; e a idoneidade do edifício ou fração para o fim pretendido.")
            d.text("Mais se declara que foram efetuados os ensaios e obtidos os certificados previstos na legislação aplicável.")
        elif which == "conclusao":
            d = G.Doc("Termo de responsabilidade do diretor de obra ou do diretor de fiscalização de obra")
            d.text("A presente minuta de termo de responsabilidade do diretor de obra e do diretor de fiscalização de obra, a subscrever aquando da conclusão da obra, transcreve a redação prevista no anexo VII da Portaria n.º 320/2026/1.", size=9)
            d.text(f"{who['name']}, morador na {who['address']}, contribuinte n.º {NIF}, inscrito na {who['body']} sob o n.º {who['number']}, declara, para efeitos do disposto no n.º 1 do artigo 63.º do RJUE, "
                   f"na qualidade de diretor de obra, que a obra de {c['work']}, localizada em {c['site']}, se encontra concluída e foi executada de acordo com o projeto aprovado e com as condições da comunicação prévia.")
        else:
            fase = "Receção Provisória" if which == "rececao-prov" else "Receção Definitiva"
            d = G.Doc(f"Termo de Responsabilidade – Diretor de Obra/Diretor de Fiscalização de Obra (Operação de Loteamento – {fase} de Obras de Urbanização)")
            d.text(f"MPL/DOP-Mod.{rng.randrange(100, 199)}/SGQ.00    Pág. 1 de 1", size=8)
            d.text("Identificação do Técnico    Nome:    Morada:    Freguesia:    Código Postal:    Concelho:    NIF n.º:    E-mail:    Habilitações Académicas:    Associação:    N.º:")
            d.text(f"Declara, na qualidade de diretor de obra, que as obras de urbanização do loteamento sito em {c['site']} se encontram em condições de {fase.lower()}, nos termos do artigo 87.º do RJUE.")
        sig(d, c, who)
    elif kind == "indice-pecas":
        d = G.Doc(rng.choice(["ÍNDICE DE PEÇAS DESENHADAS", "LISTA DE PEÇAS", "ÍNDICE GERAL DO PROJETO", "PEÇAS ESCRITAS E DESENHADAS - ÍNDICE", "Índice de peças"]))
        d.text(f"{c['work']} - {c['site']}    Requerente: {c['people']['requerente']['name']}", size=9)
        if rng.random() < 0.6:
            d.text("PEÇAS ESCRITAS", bold=True)
            for i, nme in enumerate(["Memória descritiva e justificativa", "Termo de responsabilidade do autor do projeto", "Estimativa orçamental", "Calendarização da obra",
                                     "Projeto de estabilidade", "Projeto de redes de abastecimento de água e drenagem", "Projeto de comportamento térmico", "Projeto acústico", "ITED"], 1):
                d.text(f"{i:02d}  {nme} " + "." * rng.randrange(20, 60) + f" {rng.randrange(1, 40)} pág.", size=9)
        d.text("PEÇAS DESENHADAS", bold=True)
        for i, (nme, sc) in enumerate([("Planta de localização", "1:1000"), ("Planta de implantação", "1:200"), ("Plantas dos pisos", "1:100"), ("Alçados", "1:100"), ("Cortes", "1:100"),
                                       ("Pormenores construtivos", "1:20"), ("Levantamento topográfico", "1:500"), ("Planta de cobertura", "1:100"), ("Alçados e cortes - vermelhos e amarelos", "1:100")], 1):
            d.text(f"{i:02d}  {nme}    esc. {sc}    A{rng.choice([1, 2, 3])}    {rng.choice(['DWFx', 'PDF', 'DWG'])}", size=9)
    elif kind == "parecer-externo":
        d = G.Doc(rng.choice(["PARECER", "Parecer técnico", "PEDIDO DE PARECER - ELEMENTOS A REMETER", "Consulta a entidade externa"]))
        d.text(f"Entidade: {rng.choice(['Autoridade Nacional de Emergência e Proteção Civil', 'Infraestruturas de Portugal, S.A.', 'Direção-Geral do Património Cultural', 'Agência Portuguesa do Ambiente', 'Comissão de Coordenação e Desenvolvimento Regional do Norte'])}", size=9)
        d.text(f"Processo: {rng.randrange(100, 9999)}/2026    Requerente: {c['people']['requerente']['name']}    Local: {c['site']}", size=9)
        d.text("Para emissão de parecer, o pedido foi instruído com os seguintes elementos:")
        for i, el in enumerate(rng.sample(ELEMENT_NAMES, rng.randrange(4, 8)), 1):
            d.text(f"{i}. {el[0].upper() + el[1:]};")
        d.text(rng.choice(["Face aos elementos apresentados, emite-se parecer favorável condicionado ao cumprimento das disposições legais e regulamentares aplicáveis.",
                           "Os elementos remetidos não permitem a apreciação do pedido; solicita-se o envio das peças em falta no prazo de 10 dias úteis.", "Emite-se parecer favorável."]))
    elif kind == "anexo-regulamento":
        d = G.Doc(f"ANEXO {rng.choice(['II', 'III', 'IV', 'V'])} — {rng.choice(['OBRAS DE URBANIZAÇÃO', 'OBRAS DE EDIFICAÇÃO', 'ARRANJOS EXTERIORES', 'LOTEAMENTOS'])}")
        d.text("CAPÍTULO I — DOS PROJETOS", bold=True)
        d.text(f"Artigo 1.º — Projetos", bold=True)
        d.text(f"A realização das operações urbanísticas pressupõe a apresentação dos seguintes projetos: a) projeto de infraestruturas viárias; b) {X}; c) projeto de redes de abastecimento de água; d) projeto de arquitetura paisagística.")
        d.text("Artigo 2.º — Peças escritas", bold=True)
        d.text("Cada projeto é constituído por memória descritiva e justificativa, cálculos, medições e orçamento, e termo de responsabilidade do autor.")
        d.text("Artigo 3.º — Peças desenhadas", bold=True)
        d.text("Planta de localização à escala 1:1000, planta de implantação sobre levantamento topográfico, perfis longitudinais e transversais, pormenores.")
    elif kind == "analise":
        d = G.Doc(rng.choice(["Primeira Análise", "Análise", "Parecer técnico", "Apresentação"]) + f" — Portaria n.º 320/2026/1 e {X}")
        d.text(f"{rng.choice(['Ordem dos Arquitectos', 'Ordem dos Engenheiros', 'Associação Nacional de Municípios', 'Gabinete Jurídico'])} — {rng.choice(MONTHS)} de 2026", size=9)
        d.text(f"1. A Portaria n.º 320/2026/1 identifica os elementos instrutórios dos procedimentos do RJUE. Esta análise incide sobre o regime da {X} e sobre as dúvidas de aplicação suscitadas pelos associados.")
        d.text(f"2. Verifica-se que a {X} passa a ser exigida apenas quando aplicável, cabendo ao técnico declarar a sua não aplicabilidade no termo de responsabilidade.")
        d.text("3. Recomenda-se aos associados a leitura do anexo V e a utilização das minutas de termos publicadas.")
    elif kind == "nota-explicativa":
        d = G.Doc(rng.choice([f"Os termos de responsabilidade passados no âmbito das {rng.choice(['comunicações de utilização', 'comunicações prévias', 'legalizações'])}",
                              f"Esclarecimento sobre a {X}", f"Nota explicativa — {X}"]))
        d.text(f"Tendo presente que, tal como decorre do disposto no artigo 62.º-A do RJUE, e no que concerne à {X}, importa esclarecer os requerentes e os técnicos sobre o seguinte:")
        d.text("1. O termo de responsabilidade é subscrito por técnico habilitado nos termos da Lei n.º 31/2009, com assinatura digital qualificada;")
        d.text(f"2. A {X} é apresentada em ficheiro autónomo, nos termos do manual de instrução digital;")
        d.text("3. Os serviços municipais verificam a instrução no prazo de 10 dias e, havendo omissões, convidam o requerente a corrigi-las.")
    elif kind == "memoria-candidatura":
        d = G.Doc(rng.choice(["Memória descritiva da candidatura", "Memória descritiva e justificativa — Candidatura ao programa de apoio", "Memória descritiva do projeto empresarial"]))
        d.text(f"Promotor: {c['people']['requerente']['name']}    Programa: {rng.choice(['PRR — Bairros Comerciais', 'Portugal 2030', 'Reabilitar para Arrendar', 'Apoio ao comércio local'])}", size=9)
        d.text("1. Apresentação do promotor e do projeto empresarial. 2. Objetivos da candidatura e resultados esperados. 3. Plano de investimento e cronograma. 4. Mercado-alvo e modelo de negócio.")
        d.text(f"O presente documento descreve a candidatura ao apoio financeiro para a atividade a instalar em {c['site']}, não constituindo projeto de obra.")
    elif kind == "memoria-empresa":
        d = G.Doc("MINUTA DA MEMÓRIA DESCRITIVA")
        d.text("Página 1 de 1", size=8)
        d.text(f"Objetivos: Com este documento pretende-se que o empreendedor se apresente à Câmara Municipal de {M} e conte a sua história. Narre todo o processo de construção do trabalho, desde o momento inicial até à apresentação dos produtos finais.")
        d.text("Espera-se ainda que refira a sua visão, conceito, características distintivas, síntese do produto ou serviço, mercado-alvo e modelo de negócio (máximo 2 páginas).")
    elif kind == "manual":
        d = G.Doc("MANUAL DE NORMAS DE ORGANIZAÇÃO E INSTRUÇÃO DE PROCESSOS DE OPERAÇÕES URBANÍSTICAS EM FORMATO DIGITAL")
        d.text(f"Município de {M} – NIPC 50{rng.randrange(1000000, 9999999)} | geral@cm-{M.lower().replace(' ', '')}.pt", size=8)
        d.text("1. Os elementos são apresentados em ficheiros PDF/A, assinados digitalmente; as peças desenhadas em DWFx ou PDF/A; o levantamento topográfico e a planta de implantação em DWG georreferenciado.")
        d.text(f"2. A {X} constitui um ficheiro autónomo, com o nome normalizado indicado no anexo I.")
        d.text("3. Os ficheiros não podem ultrapassar 50 MB nem ter nomes com mais de 40 caracteres.")
        if rng.random() < 0.6:
            for i, el in enumerate(rng.sample(ELEMENT_NAMES, rng.randrange(6, len(ELEMENT_NAMES))), 4):
                d.text(f"{i}. {el[0].upper() + el[1:]}: nome do ficheiro {el.split()[0].upper()[:6]}_{rng.randrange(1, 40):02d}.pdf; " +
                       rng.choice(["uma peça por ficheiro.", "assinatura digital qualificada do autor.", "formato PDF/A ou DWFx.", "sem páginas em branco."]))
            d.text("ANEXO I — Lista de nomes normalizados", bold=True)
            for el in ELEMENT_NAMES[:8]:
                d.text(f"{el} | {el.split()[0].upper()[:6]}.pdf | PDF/A")
    elif kind == "diagnostico":
        d = G.Doc("Plano Municipal de Acessibilidade Para Todos — Capítulo II – Levantamento e Diagnóstico")
        d.text(f"Município de {M}    Entrega Final    {rng.randrange(40, 140)}", size=8)
        d.text(f"Edificado {rng.randrange(1, 9)} — {rng.choice(['Biblioteca Municipal', 'Centro de Saúde', 'Escola Básica', 'Junta de Freguesia', 'Piscinas Municipais'])}", bold=True)
        d.text("Registo Fotográfico — Diagnóstico do Edifício — Sinalética: ausente; Portão: cumpre o disposto no DL 163/2006 quanto à largura; Rampa: inclinação superior a 8 %, não cumpre; Balcão de atendimento: altura superior a 0,80 m.")
        d.text("Propostas de intervenção: rebaixamento do balcão, correção da rampa, colocação de sinalética.")
    else:
        d = G.Doc(f"MUNICÍPIO DE {M.upper()} — AQUISIÇÃO DE SERVIÇOS DE {rng.choice(['PROFISSIONAL DE TOPOGRAFIA', 'ELABORAÇÃO DE PROJETO', 'FISCALIZAÇÃO DE OBRA'])} — CONSULTA PRÉVIA — CADERNO DE ENCARGOS")
        d.text("Cláusula 1.ª Objeto", bold=True); d.text(f"O presente caderno de encargos compreende as cláusulas a incluir no contrato de aquisição de serviços de {X}.")
        d.text("Cláusula 2.ª Prazo", bold=True); d.text(f"O contrato mantém-se em vigor pelo prazo de {rng.randrange(6, 36)} meses a contar da data da sua celebração.")
        d.text("Cláusula 3.ª Preço e pagamento", bold=True); d.text("As quantias devidas deverão ser pagas no prazo de 30 dias após a receção das respetivas faturas.")
    words = [w for w in slug(d.title).split() if len(w) > 2 and w not in ("para", "dos", "das", "com", "por", "municipal", "referente")][:4] or [kind]
    stem = NOISE_PREFIX + rng.choice([lambda: "_".join(words), lambda: f"{M.lower().split()[0]}_{'_'.join(words[:2])}", lambda: f"{kind.replace('-', '_')}_{rng.randrange(1, 99):02d}",
                                      lambda: f"{'-'.join(words[:3])}-{rng.randrange(2019, 2027)}", lambda: f"PDF{rng.randrange(10**13, 10**14)}"])()
    return ("OUTDOC", stem, d.title[:60], d)


def doc_special_memory(c, name, p, rng):
    """A speciality memória as the engineers write them: index, numbered sections, figure captions, a table, references; always a WRITTEN piece."""
    d = G.Doc(f"Memória descritiva e justificativa do projeto de {name}")
    long = rng.random() < 0.5
    if long:
        d.text(f"{c['work'][0].upper() + c['work'][1:]} — {c['site']}    Edição Revisão A {rng.randrange(0, 3)}.0    Data {rng.choice(MONTHS)} 2026", size=9)
        d.text(f"Elaborado por: Técnico Responsável {p['name']} Ins. OE n.º {p['number']}    Página 1 de {rng.randrange(6, 20)}", size=8)
        d.text("ÍNDICE", bold=True)
        for i, h in enumerate(["INTRODUÇÃO", "OBJETIVO", "DESCRIÇÃO DO EDIFÍCIO", "LEGISLAÇÃO E NORMAS", "SOLUÇÕES ADOTADAS", "CÁLCULOS JUSTIFICATIVOS", "CONSIDERAÇÕES FINAIS"], 1):
            d.text(f"{i} – {h} {'.' * rng.randrange(50, 90)} {i + 2}", size=9)
    d.text("1 – INTRODUÇÃO", bold=True)
    d.text(f"A presente memória descritiva e justificativa refere-se ao projeto de {name} da {c['work']}, que o requerente {c['people']['requerente']['name']} pretende levar a efeito em {c['site']}, concelho de Celorico de Basto.")
    d.text("2 – DESCRIÇÃO", bold=True)
    d.text(f"O edifício é composto por {c['pisos']} piso(s) acima da cota de soleira, destinado a {c['use'].lower()}, com área total de construção de {c['built']} m2.")
    if long:
        d.text(f"Figura 1 – Localização do edifício. Figura 2 – Esquema da solução de {name}.", size=9)
        d.text("3 – SOLUÇÕES ADOTADAS", bold=True)
        for _ in range(rng.randrange(1, 4)):
            d.text(rng.choice(REAL) if REAL else "Solução adotada de acordo com a regulamentação em vigor.")
        d.text("Série: PVC    Descrição: Policloreto de vinilo    Coef. Manning: 0.009    Referências | Diâmetro interno: Ø32 29.6 | Ø40 37.6 | Ø50 47.6 | Ø75 72.0 | Ø90 86.8 | Ø110 105.6", size=9)
        d.text("4 – CÁLCULOS JUSTIFICATIVOS", bold=True)
        d.text("Os valores de cálculo foram determinados pela fórmula Qc = C x I x A, sendo C o coeficiente aplicável, I a intensidade de referência e A a área em projeção horizontal (ver peças desenhadas).")
    if long:
        stretch(d, rng, rng.randrange(4, 17), first=5)   # D16: real speciality memórias run 10–20 pages (SCIE, ITED)
    d.text("5 – LEGISLAÇÃO E NORMAS", bold=True)
    d.text("Foram consideradas as disposições legais e regulamentares aplicáveis, nomeadamente o Regulamento Geral das Edificações Urbanas, as normas europeias EN e as normas técnicas de construção em vigor.")
    sig(d, c, p)
    return d, []


def doc_estimate(c, p, rng):
    """The cost estimate: a table, or (40 %) the architects' narrative 'estimativa preliminar' with a nota introdutória and per-m2 reasoning; the total line is the fact."""
    if rng.random() < 0.6:
        return doc_plain(c, "Estimativa do custo total da obra", p, f"Estimativa do custo total da obra, baseada em quantidades e tipologias de trabalhos: {eur(c['cost'])} (valor fictício).", facts=[("custo_total", eur(c["cost"]), "", 0)])
    d = G.Doc("Estimativas Orçamentais")
    if rng.random() < 0.5:
        # the architects' letter to the dono de obra (real pattern: expectations of cost vs programme, areas per space, cost per m2, total)
        atelier = rng.choice(ATELIERS)
        d.text(f"{atelier}", size=9)
        d.text("Estimativas Orçamentais", bold=True)
        d.text(f"Exmo. Senhor {c['people']['requerente']['name']}, Dono de Obra da {c['work']}, em {c['site']}.")
        d.text("Um projeto é o resultado de um processo de decisão em que o Dono de Obra é confrontado com diferentes solicitações, permitindo-lhe fazer opções de forma "
               "refletida e informada. Os projetistas, com a sua experiência e conhecimentos técnicos, constituem o principal apoio do Dono de Obra nesse processo.")
        d.text("Em nossa opinião, estamos perante uma situação de disparidade de expectativas entre custo e qualidade / quantidade, que passamos a explicar.")
        d.text("1 - A listagem de espaços presente no Programa Base não continha as áreas úteis dos mesmos. Assim, os projetistas atribuíram-lhes áreas no seu entender "
               "adequadas aos objetivos descritos, resultando nas seguintes áreas brutas de construção:")
        rest = c["built"]
        for name in rng.sample(["Zona de estar e refeições", "Quartos e instalações sanitárias", "Cozinha e lavandaria", "Garagem e arrumos", "Escritório", "Alpendre e varandas"], rng.randrange(2, 4)):
            part = max(10, int(rest * rng.uniform(0.2, 0.5))); rest -= part
            d.text(f"{name}  {part}m2")
        d.text(f"TOTAL AB CONSTRUÇÃO  {c['built']}m2")
        per = rng.randrange(600, 1400)
        d.text(f"Atribuindo um custo de construção por m2 de {per}€, teremos para o edificado um custo de construção de {eur(c['built'] * per)}.")
        d.text("No entanto, consideramos este valor por m2 baixo para as exigências que decorrem do Programa Base, nomeadamente a dimensão dos vãos e o nível de acabamentos pretendido.")
        d.text("2 - Quanto aos arranjos exteriores e às ligações às redes públicas, o seu custo foi estimado a partir de obras semelhantes já executadas pelo gabinete.")
        pg = d.text(f"Em conclusão, a estimativa do custo total da obra é de {eur(c['cost'])} (valor fictício).", tag="custo", bold=True)
        sig(d, c, p)
        return d, [("custo_total", eur(c["cost"]), "", pg, None)]
    d.text(f"{rng.choice(ATELIERS)}    ESTIMATIVA PRELIMINAR    {c['work'][0].upper() + c['work'][1:]} — {c['site']}    1 de {rng.randrange(3, 12)}", size=9)
    d.text("NOTA INTRODUTÓRIA", bold=True)
    d.text("No desenvolvimento da proposta foram tidos em conta os requisitos expressos pelo dono de obra. A estimativa baseia-se em quantidades e tipologias dos trabalhos necessários à execução da obra, com valores unitários praticados na região.")
    per = rng.randrange(600, 1400)
    d.text(f"1 – Área bruta de construção {c['built']} m2, a um custo de construção por m2 de {per} €, resulta para o edificado um custo de construção de {eur(c['built'] * per)}.")
    d.text(f"2 – Quanto à área exterior, considerou-se um valor de 60 €/m2 para {c['perm']} m2 de arranjos exteriores, num total de {eur(c['perm'] * 60)}.")
    d.text("3 – Acresce o custo das demolições das pré-existências e das ligações às redes públicas.")
    pg = d.text(f"Estimativa do custo total da obra: {eur(c['cost'])} (valor fictício).", tag="custo", bold=True)
    sig(d, c, p)
    return d, [("custo_total", eur(c["cost"]), "", pg, None)]


def plant(rng, c, n_err):
    plan, findings = {}, []
    if rng.random() < 0.5:
        plan["long_memoria"] = True
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
        seen = set()
        for _ in range(rng.randrange(3, 8)):
            code, stem, title, d = noise_about(c, rng) if rng.random() < 0.75 else noise_doc(c, rng)
            if rng.random() < 0.4:   # D16: real norms, manuals, regulations and avisos run 4–40 pages; a long document about an element is still not the element
                stretch(d, rng, rng.randrange(5, 31), pool="regulamento", header=f"{title}    —    Página" if rng.random() < 0.5 else None)
            if stem in seen:
                continue
            seen.add(stem)
            docs.append((code, stem, title, "written", "requerente", d, []))
    for code, stem, title, kind, signer, d, facts in docs:
        if code in plan.get("omit", set()):
            continue
        NOISE = ("fatura-agua", "curriculo", "carta", "ficha-verificacao", "regulamento-extrato", "lista-elementos")
        LEGACY_NAMES = {"fatura-agua": "fatura_agua_2026_08", "curriculo": "cv_requerente", "carta": "carta_cmcb", "ficha-verificacao": "ficha_verificacao_elementos",
                        "regulamento-extrato": "regulamento_instrucao_digital_extrato", "lista-elementos": "lista_elementos_nomeacao_ficheiros"}
        is_noise = stem in NOISE or stem.startswith(NOISE_PREFIX)
        fname = (f"{stem[len(NOISE_PREFIX):]}.pdf" if stem.startswith(NOISE_PREFIX) else f"{LEGACY_NAMES[stem]}.pdf") if is_noise else f"{code}-{stem}.pdf"
        if code in plan.get("not_pdf", set()):
            data = G.png(640, 400, 90)
        else:
            fields = [(f"sintese.{k}", v) for k, _, v, _ in summary_rows(c, {"plot": plan.get("typo_plot")} if "typo_plot" in plan else {})] if code == "REQ" else None
            pdf = G.finish(d.render(), title, pdfa=code not in plan.get("no_pdfa", set()), fields=fields)
            data = pdf if code in plan.get("unsigned", set()) else G.sign(pdf, signer if signer != "seguradora" else "arquiteto")
        (folder / fname).write_bytes(data)
        signed_by = None if code in plan.get("unsigned", set()) or code in plan.get("not_pdf", set()) else signer
        files.append({"slot": code, "file": fname, "title": title, "kind": kind, "signed_by": signed_by})
        passages = DOCS.get(code, {}).get("passages", []) if not is_noise else []
        labels.append({"expediente": cid, "file": fname, "slot": code, "title": title, "kind": kind, "pages": len(d.pages), "is_pdf": code not in plan.get("not_pdf", set()),
                       "pdfa": code not in plan.get("no_pdfa", set()) and code not in plan.get("not_pdf", set()), "signed": signed_by is not None, "signer": signed_by,
                       "element": (f"portaria-320-2026-1:{passages[0]}" if passages else None), "elements": [f"portaria-320-2026-1:{p}" for p in passages],
                       "noise": is_noise,
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
        nf, ne = build_one(rng, cid, out, n_err, with_noise=True)
        tot_files += nf; tot_err += ne
        print(f"{cid}: {nf} files, {ne} planted")
    print(f"{a.n} expedientes in {out.relative_to(ROOT)}: {tot_files} files, {tot_err} planted errors")


if __name__ == "__main__":
    main()
