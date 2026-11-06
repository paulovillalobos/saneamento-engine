"""Build the exam: three simulated applications for a building prior communication
(comunicação prévia de obras de edificação) in Celorico de Basto, and their answer key.

Everything here is fictional and marked SIMULADO on every page: names, NIF 999999990 (the
generic "consumidor final" number, not a person), addresses, policies, signatures. The test
certificates come from a test CA in exam/pki/ and are NOT qualified certificates.

    A  complete: everything the law asks for (one known limit of the generator, below)
    B  incomplete: no estimate of urban-planning charges (V.27.g), no photographs (V.15)
    C  traps: a ".pdf" that is not a PDF, a PDF without PDF/A identification, an unsigned
       declaration, a declaration without the official wording, a built-area mismatch
       between documents, and a plot area typed as 120 instead of 1200

Known limits of the generator (recorded in the answer key, not hidden):
    - no DWG of the site plan (Annex VI n.º 1 b)): DWG cannot be produced here
    - PDF/A conformance is claimed (identification + sRGB output intent), not validated:
      no reference validator (veraPDF needs Java) on this machine yet
    - signatures are cryptographically valid with test certificates, never qualified

Run with .venv/bin/python exam/build.py. Rebuilding produces new bytes (Chrome output and
render times differ); exam/manifest.json pins the committed files.
"""
import hashlib
import io
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine.sources import Store  # noqa: E402

EXAM = ROOT / "exam"
PKI = EXAM / "pki"
DOSSIERS = EXAM / "dossiers"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
ICC = Path("/System/Library/ColorSync/Profiles/sRGB Profile.icc")
FIXED = "2026-10-14T12:00:00Z"
PDF_DATE = "D:20261014120000Z"
LAW = "dr:portaria:320/2026/1"
BANNER = "DOCUMENTO SIMULADO — EXAME RJUE-ENGINE — SEM VALOR LEGAL"

# -- fictional parties ---------------------------------------------------------------------
NIF = "999999990"
SITE = {"address": "Rua Fictícia do Exame, n.º 1, 4890-000 Celorico de Basto",
        "point": {"lat": 41.387, "lon": -8.002}}
PEOPLE = {
    "requerente": {"name": "Maria Simulada Exame", "cn": "Maria Simulada Exame (TESTE)", "role": "requerente",
                   "address": "Rua Fictícia do Exame, n.º 1, 4890-000 Celorico de Basto"},
    "arquiteto": {"name": "Tiago Simulado", "cn": "Tiago Simulado (TESTE)", "role": "arquiteto",
                  "title": "arquiteto", "body": "Ordem dos Arquitectos", "number": "00000-SIM",
                  "address": "Rua do Atelier Fictício, n.º 2, 4000-000 Porto", "policy": "SIM-RC-0001"},
    "engenheiro": {"name": "Sofia Simulada", "cn": "Sofia Simulada (TESTE)", "role": "engenheira",
                   "title": "engenheira civil", "body": "Ordem dos Engenheiros", "number": "00000-SIM",
                   "address": "Avenida Fictícia, n.º 3, 4700-000 Braga", "policy": "SIM-RC-0002"},
    "diretor": {"name": "Rui Simulado", "cn": "Rui Simulado (TESTE)", "role": "diretor de obra",
                "title": "engenheiro civil", "body": "Ordem dos Engenheiros", "number": "00001-SIM",
                "address": "Travessa Fictícia, n.º 4, 4890-000 Celorico de Basto", "policy": "SIM-RC-0003"},
    "seguradora": {"name": "Seguradora Exemplo, S.A. (fictícia)", "cn": "Seguradora Exemplo (TESTE)", "role": "seguradora"},
}
WORK = "construção de moradia unifamiliar"
COST = "320 000,00 €"

# -- the planning summary (Annex I-C). Labels transcribed by hand from the official image
#    files.diariodarepublica.pt/images/1153698591/1153716690.png: a reading, not verified text.
SUMMARY_A = [
    ("superficie_total_terreno", "SUPERFÍCIE TOTAL DO TERRENO OBJETO DA OPERAÇÃO URBANÍSTICA", "1200", "m2"),
    ("area_parcela", "ÁREA DA PARCELA OU LOTE", "1200", "m2"),
    ("area_implantacao", "ÁREA TOTAL DE IMPLANTAÇÃO", "277", "m2"),
    ("area_impermeabilizacao", "ÁREA TOTAL DE IMPERMEABILIZAÇÃO", "350", "m2"),
    ("area_permeavel", "ÁREA TOTAL PERMEÁVEL", "850", "m2"),
    ("area_total_construcao", "ÁREA TOTAL DE CONSTRUÇÃO", "554", "m2"),
    ("volume_total", "VOLUME TOTAL", "1700", "m3"),
    ("altura_edificacao", "ALTURA DA EDIFICAÇÃO", "7,2", "m"),
    ("altura_fachada", "ALTURA DA FACHADA", "6,5", "m"),
    ("pisos_acima_soleira", "N.º DE PISOS ACIMA DA COTA DE SOLEIRA", "2", ""),
    ("pisos_abaixo_soleira", "N.º DE PISOS ABAIXO DA COTA DE SOLEIRA", "0", ""),
    ("uso", "USO A QUE SE DESTINA A EDIFICAÇÃO / USO DA EDIFICAÇÃO", "Habitação unifamiliar", ""),
    ("fogos", "N.º TOTAL DE FOGOS", "1", ""),
    ("area_habitacao", "ÁREA DE CONSTRUÇÃO PARA HABITAÇÃO", "554", "m2"),
    ("lugares_estacionamento", "N.º TOTAL DE LUGARES DE ESTACIONAMENTO", "2", ""),
]


# -- test PKI ---------------------------------------------------------------------------------
def ensure_pki():
    PKI.mkdir(parents=True, exist_ok=True)
    cnf = PKI / "openssl.cnf"
    cnf.write_text("[req]\ndistinguished_name=dn\n[dn]\n[ca]\nbasicConstraints=critical,CA:TRUE\n"
                   "keyUsage=critical,keyCertSign,cRLSign\n[signer]\nbasicConstraints=CA:FALSE\n"
                   "keyUsage=critical,digitalSignature,nonRepudiation\n")
    if not (PKI / "ca.pem").exists():
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-sha256", "-days", "3650",
                        "-config", str(cnf), "-extensions", "ca", "-keyout", str(PKI / "ca.key"), "-out", str(PKI / "ca.pem"),
                        "-subj", "/C=PT/O=RJUE-ENGINE EXAME/CN=CA DE TESTE - NAO QUALIFICADA"], check=True, capture_output=True)
    for serial, (key, person) in enumerate(PEOPLE.items(), start=2):
        if (PKI / f"{key}.pem").exists():
            continue
        csr = PKI / f"{key}.csr"
        subprocess.run(["openssl", "req", "-newkey", "rsa:2048", "-nodes", "-config", str(cnf),
                        "-keyout", str(PKI / f"{key}.key"), "-out", str(csr),
                        "-subj", f"/C=PT/O=RJUE-ENGINE EXAME/CN={person['cn']}"], check=True, capture_output=True)
        subprocess.run(["openssl", "x509", "-req", "-in", str(csr), "-CA", str(PKI / "ca.pem"), "-CAkey", str(PKI / "ca.key"),
                        "-set_serial", str(serial), "-days", "3650", "-sha256", "-extfile", str(cnf), "-extensions", "signer",
                        "-out", str(PKI / f"{key}.pem")], check=True, capture_output=True)
        csr.unlink()


# -- small synthetic photograph (PNG written with zlib, no external tools) --------------------
def png(width, height, tint):
    rows = []
    for y in range(height):
        row = bytearray(b"\x00")
        for x in range(width):
            row += bytes(((60 + x * 150 // width) % 256, (90 + y * 120 // height) % 256, tint))
        rows.append(bytes(row))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + chunk(b"IEND", b""))


# -- HTML documents -------------------------------------------------------------------------------
STYLE = """@page { size: A4; margin: 16mm; }
body { font-family: Arial, Helvetica, sans-serif; font-size: 10pt; color: #111; }
.sim { border: 1.5pt solid #b00; color: #b00; font-weight: bold; padding: 2mm; text-align: center; margin-bottom: 5mm; }
h1 { font-size: 13pt; margin: 0 0 4mm 0; } h2 { font-size: 11pt; margin: 4mm 0 2mm 0; }
table { border-collapse: collapse; width: 100%; } td, th { border: 0.6pt solid #444; padding: 1.2mm 2mm; font-size: 9pt; }
.legend td { font-size: 8.5pt; } p { margin: 0 0 2.5mm 0; line-height: 1.35; } .muted { color: #444; }"""


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def page(title, body):
    return (f"<!doctype html><html lang='pt'><head><meta charset='utf-8'><title>{esc(title)}</title>"
            f"<style>{STYLE}</style></head><body><div class='sim'>{BANNER}</div><h1>{esc(title)}</h1>{body}</body></html>")


def paras(*texts):
    return "".join(f"<p>{esc(t)}</p>" for t in texts)


def signature_line(person):
    return f"<p class='muted'>Celorico de Basto, 14 de outubro de 2026. Assinado digitalmente por {esc(person['name'])} (certificado de teste).</p>"


def term_author(person, project, kind="I"):
    """Annex VII template I (project authors) or II (specialty projects), filled in."""
    head = (f"{person['name']}, {person['title']}, com domicílio em {person['address']}, contribuinte n.º {NIF}, "
            f"inscrito na {person['body']} sob o n.º {person['number']}, declara, para efeitos do disposto no n.º 1 do "
            f"artigo 10.º do Decreto-Lei n.º 555/99, de 16 de dezembro, na sua redação atual, que o projeto de {project}, "
            f"de que é autor, relativo à obra de {WORK}, localizada em {SITE['address']}, cuja comunicação prévia foi "
            f"apresentada por {PEOPLE['requerente']['name']}")
    if kind == "I":
        body = [head + ", observa as normas legais e regulamentares aplicáveis à pretensão."]
    else:
        body = [head + ":", "Observa as normas legais e regulamentares aplicáveis, com exceção de nenhuma;",
                "Está conforme com os planos municipais ou intermunicipais de ordenamento do território aplicáveis à "
                "pretensão, nos termos do disposto no n.º 2 do artigo 10.º do RJUE, bem como com o Regulamento do PDM de "
                "Celorico de Basto."]
    body.append("Declara ainda, para efeitos do n.º 1 do artigo 24.º da Lei n.º 31/2009, de 3 de julho, na sua redação "
                f"atual, que o seguro de responsabilidade civil extracontratual com a Apólice n.º {person['policy']} cujo "
                f"tomador é {person['name']} abrange a elaboração e subscrição do presente projeto, de acordo com a "
                f"estimativa de custo total da obra, cujo valor é de {COST}.")
    return paras(*body) + signature_line(person)


def term_coordinator(person):
    return paras(
        f"{person['name']}, com domicílio em {person['address']}, contribuinte n.º {NIF}, inscrito na {person['body']} sob "
        f"o n.º {person['number']}, na qualidade de coordenador, relativo à obra de {WORK}, localizada em {SITE['address']}, "
        f"cuja comunicação prévia foi apresentada por {PEOPLE['requerente']['name']} declara, para efeitos do disposto no "
        "n.º 1 do artigo 10.º do Decreto-Lei n.º 555/99, de 16 de dezembro, na sua redação atual, a compatibilidade entre "
        "os diversos projetos e as condições necessárias para o cumprimento das disposições legais e regulamentares "
        "aplicáveis a cada especialidade e a respeitar por cada autor de projeto.",
        "Declara ainda, para efeitos do n.º 1 do artigo 24.º da Lei n.º 31/2009, de 3 de julho, na sua redação atual, que o "
        f"seguro de responsabilidade civil extracontratual com a Apólice n.º {person['policy']} cujo tomador é "
        f"{person['name']} abrange a coordenação dos presentes projetos, de acordo com a estimativa de custo total da obra, "
        f"cujo valor é de {COST}.") + signature_line(person)


def term_director(person):
    return paras(
        f"{person['name']}, com domicílio em {person['address']}, contribuinte n.º {NIF}, inscrito na {person['body']} sob "
        f"o n.º {person['number']}, declara, para efeitos do disposto no artigo 21.º, n.º 4 da Lei n.º 31/2009, de 3 de "
        f"julho, relativamente à obra de {WORK}, localizada em {SITE['address']}, cujo titular é "
        f"{PEOPLE['requerente']['name']}, que se responsabiliza pelo exercício da função de diretor de obra.",
        "Declara ainda, para efeitos do n.º 1 do artigo 24.º da Lei n.º 31/2009, de 3 de julho, na sua redação atual, que o "
        f"seguro de responsabilidade civil extracontratual com a Apólice n.º {person['policy']} cujo tomador é "
        f"{person['name']} abrange a direção/fiscalização da obra, de acordo com a estimativa de custo total da obra, cujo "
        f"valor é de {COST}.") + signature_line(person)


def insurance(person, scope):
    return paras(f"Certifica-se que {person['name']} é tomador da apólice n.º {person['policy']}, de seguro de "
                 f"responsabilidade civil profissional, que abrange {scope} relativos à obra de {WORK}, localizada em "
                 f"{SITE['address']}, com período de validade de 1 de janeiro de 2026 a 31 de dezembro de 2026.",
                 "Emitido por Seguradora Exemplo, S.A. (entidade fictícia).") + signature_line(PEOPLE["seguradora"])


def summary_table(rows):
    cells = "".join(f"<tr><td>{esc(label)}</td><td style='text-align:right'>{esc(value)}</td><td>{esc(unit)}</td></tr>"
                    for _, label, value, unit in rows)
    return f"<table><tr><th>Síntese urbanística (Anexo I-C)</th><th>Obra de edificação</th><th>Unid.</th></tr>{cells}</table>"


def request_doc(rows):
    req = PEOPLE["requerente"]
    return paras(
        "Exmo. Senhor Presidente da Câmara Municipal de Celorico de Basto",
        f"{req['name']}, contribuinte n.º {NIF}, com morada em {req['address']}, vem apresentar comunicação prévia de "
        f"obras de edificação ({WORK}) no prédio sito em {SITE['address']} (coordenadas {SITE['point']['lat']}, "
        f"{SITE['point']['lon']}), nos termos do Regime Jurídico da Urbanização e da Edificação.") + \
        "<h2>Síntese urbanística</h2>" + summary_table(rows) + signature_line(req)


def memory(built_area, plot_area):
    a = PEOPLE["arquiteto"]
    return paras(
        f"A presente memória descritiva e justificativa respeita à {WORK}, localizada em {SITE['address']}, "
        f"freguesia e concelho de Celorico de Basto, em prédio com a área de {plot_area} m2.",
        "A pretensão insere-se em Solo Urbano — Espaços centrais, conforme a Planta de Ordenamento do Plano Diretor "
        "Municipal de Celorico de Basto (2.ª revisão, Aviso n.º 14352/2025/2).",
        f"A edificação desenvolve-se em dois pisos acima da cota de soleira, com área de implantação de 277 m2 e área "
        f"total de construção de {built_area} m2, destinada a habitação unifamiliar (um fogo, tipologia T3), com dois "
        "lugares de estacionamento no interior do lote.",
        "Quadro sinóptico: superfície do terreno 1200 m2; área da parcela 1200 m2; área de implantação 277 m2; "
        f"área total de construção {built_area} m2; área permeável 850 m2; área impermeabilizada 350 m2; volume 1700 m3; "
        "altura da edificação 7,2 m; altura da fachada 6,5 m.") + signature_line(a)


def drawing(title, number, scale, author, shapes):
    legend = (f"<table class='legend'><tr><td>Requerente</td><td>{esc(PEOPLE['requerente']['name'])}</td>"
              f"<td>Desenho n.º</td><td>{number}</td></tr><tr><td>Localização</td><td>{esc(SITE['address'])}</td>"
              f"<td>Escala</td><td>{scale}</td></tr><tr><td>Especificação</td><td>{esc(title)}</td><td>Data</td>"
              f"<td>2026-10-14</td></tr><tr><td>Autor</td><td colspan='3'>{esc(author['name'])}</td></tr></table>")
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 600 420' width='100%' height='118mm' "
           f"style='border:0.6pt solid #444;margin-bottom:4mm'>{shapes}</svg>")
    return svg + legend + signature_line(author)


PLAN = ("<rect x='150' y='90' width='300' height='220' fill='none' stroke='#111' stroke-width='3'/>"
        "<line x1='300' y1='90' x2='300' y2='310' stroke='#111' stroke-width='2'/>"
        "<line x1='150' y1='200' x2='300' y2='200' stroke='#111' stroke-width='2'/>"
        "<text x='190' y='150' font-size='14'>Sala</text><text x='340' y='150' font-size='14'>Cozinha</text>"
        "<text x='190' y='260' font-size='14'>Quarto</text><text x='340' y='260' font-size='14'>Quarto</text>")
SECTION = ("<polygon points='150,300 450,300 450,140 300,80 150,140' fill='none' stroke='#111' stroke-width='3'/>"
           "<line x1='150' y1='220' x2='450' y2='220' stroke='#111' stroke-width='2'/>"
           "<text x='460' y='305' font-size='12'>cota de soleira 0,00</text><text x='460' y='145' font-size='12'>+6,50</text>")
SITEPLAN = ("<rect x='60' y='40' width='480' height='340' fill='none' stroke='#555' stroke-dasharray='8 5' stroke-width='2'/>"
            "<rect x='210' y='140' width='180' height='130' fill='#ddd' stroke='#111' stroke-width='3'/>"
            "<text x='70' y='60' font-size='12'>limite da parcela (1200 m2)</text><text x='230' y='210' font-size='13'>implantação 277 m2</text>")


def photo_doc(author):
    imgs = "".join(f"<img src='data:image/png;base64,{__import__('base64').b64encode(png(320, 200, t)).decode()}' "
                   f"style='width:82mm;margin:0 3mm 3mm 0'/>" for t in (40, 160))
    return paras("Registo fotográfico da situação existente, abrangendo o imóvel e as edificações adjacentes "
                 "(imagens sintéticas).") + imgs + signature_line(author)


def plain(author, *texts):
    return paras(*texts) + signature_line(author)


# -- the documents of dossier A, slot by slot (codes from Celorico de Basto's NoPaper form) ---
SPECIALTIES = [  # (term, insurance, memory, drawings, project name)
    ("TREECP", "SRCEST", "MDEECP", "PDEECP", "estabilidade, de escavação e contenção periférica"),
    ("TRPIE", "SRCIE", "MDPIE", "PDPIE", "instalações elétricas"),
    ("TRRPAE", "SRCPAE", "MDRPAE", "PDRPAE", "redes prediais de água e esgotos"),
    ("TRPAP", "SRCAP", "MDPAP", "PDPAP", "águas pluviais"),
    ("TRITED", "SRITED", "MDITED", "PDITED", "infraestruturas de telecomunicações (ITED)"),
    ("TRPCT", "SRCCT", "MDPCT", "PDPCT", "comportamento térmico"),
    ("TRPCA", "SRCCA", "MDPCA", "PDPCA", "condicionamento acústico"),
]


def documents_a():
    arq, eng, dire, req = PEOPLE["arquiteto"], PEOPLE["engenheiro"], PEOPLE["diretor"], PEOPLE["requerente"]
    d = [
        ("REQ", "requerimento", "Requerimento de comunicação prévia (modelo do Anexo I)", "written", "requerente", request_doc(SUMMARY_A)),
        ("CRP", "certidao-permanente", "Código de acesso à certidão permanente do registo predial", "written", "requerente",
         plain(req, "Código de acesso à certidão permanente do registo predial: 0000-0000-0000 (fictício).")),
        ("TRPARQ", "termo-arquitetura", "Termo de responsabilidade do autor do projeto de arquitetura", "written", "arquiteto", term_author(arq, "arquitetura")),
        ("SRCARQ", "seguro-arquiteto", "Comprovativo de seguro de responsabilidade civil do autor do projeto de arquitetura", "written", "seguradora", insurance(arq, "a elaboração e subscrição do projeto de arquitetura")),
        ("TRCP", "termo-coordenador", "Termo de responsabilidade do coordenador de projeto", "written", "arquiteto", term_coordinator(arq)),
        ("SRCCP", "seguro-coordenador", "Comprovativo de seguro de responsabilidade civil do coordenador de projeto", "written", "seguradora", insurance(arq, "a coordenação dos projetos")),
        ("TRPLAC", "termo-acessibilidades", "Termo de responsabilidade do autor do plano de acessibilidades", "written", "arquiteto", term_author(arq, "plano de acessibilidades")),
        ("TRDO", "termo-diretor-obra", "Termo de responsabilidade pela assunção da função de diretor de obra", "written", "diretor", term_director(dire)),
        ("SRCDO", "seguro-diretor-obra", "Comprovativo de seguro de responsabilidade civil do diretor de obra", "written", "seguradora", insurance(dire, "a direção da obra")),
        ("CCDO", "contrato-diretor-obra", "Comprovativo de contratação do diretor de obra", "written", "requerente",
         plain(req, f"Declara-se que {dire['name']} foi contratado para exercer a função de diretor de obra da {WORK}, por contrato de 1 de outubro de 2026 (fictício).")),
        ("FOTO", "registo-fotografico", "Registo fotográfico da situação existente", "written", "arquiteto", photo_doc(arq)),
        ("MDARQ", "memoria-descritiva", "Memória descritiva e justificativa", "written", "arquiteto", memory("554", "1200")),
        ("CEO", "calendarizacao", "Calendarização da execução da obra", "written", "arquiteto",
         plain(arq, "Início previsto dos trabalhos: janeiro de 2027. Conclusão prevista: dezembro de 2027 (12 meses).")),
        ("EOCT", "estimativa-custo", "Estimativa do custo total da obra", "written", "arquiteto",
         plain(arq, f"Estimativa do custo total da obra, baseada em quantidades e tipologias de trabalhos: {COST} (valor fictício).")),
        ("OUTDOC", "estimativa-encargos", "Estimativa dos encargos urbanísticos", "written", "requerente",
         plain(req, "Estimativa dos encargos urbanísticos, incluindo a taxa pela realização, manutenção e reforço de infraestruturas urbanísticas: 4 210,00 € (simulação, valor fictício).")),
        ("MDPLAC", "memoria-acessibilidades", "Memória descritiva do plano de acessibilidades", "written", "arquiteto",
         plain(arq, "O plano de acessibilidades demonstra a conformidade da operação com o regime jurídico da acessibilidade: percurso acessível desde a via pública até à entrada principal.")),
        ("PDPLAC", "pecas-acessibilidades", "Peças desenhadas do plano de acessibilidades", "drawn", "arquiteto", drawing("Plano de acessibilidades", "ACS-01", "1:100", arq, PLAN)),
        ("P10000", "planta-localizacao", "Planta de localização", "drawn", "arquiteto", drawing("Planta de localização", "LOC-01", "1:1000", arq, SITEPLAN)),
        ("LEVT", "levantamento-topografico", "Levantamento topográfico georreferenciado", "drawn", "engenheiro", drawing("Levantamento topográfico georreferenciado", "TOP-01", "1:200", eng, SITEPLAN)),
        ("LEVT", "termo-levantamento", "Termo de responsabilidade do autor do levantamento topográfico", "written", "engenheiro",
         plain(eng, f"{eng['name']}, {eng['title']}, declara ser autora do levantamento topográfico georreferenciado do prédio sito em {SITE['address']}, que identifica o prédio, a respetiva área e o espaço público envolvente.")),
        ("PI", "planta-implantacao", "Planta de implantação", "drawn", "arquiteto", drawing("Planta de implantação", "IMP-01", "1:200", arq, SITEPLAN)),
        ("PLANT", "plantas", "Plantas", "drawn", "arquiteto", drawing("Planta do piso 0", "ARQ-01", "1:100", arq, PLAN)),
        ("ALC", "alcados", "Alçados", "drawn", "arquiteto", drawing("Alçado principal", "ARQ-02", "1:100", arq, SECTION)),
        ("CORTES", "cortes", "Cortes", "drawn", "arquiteto", drawing("Corte longitudinal", "ARQ-03", "1:100", arq, SECTION)),
        ("PC", "pormenores", "Pormenores de construção", "drawn", "arquiteto", drawing("Pormenor de fachada e cobertura", "ARQ-04", "1:20", arq, SECTION)),
    ]
    for term, ins, mem, drw, name in SPECIALTIES:
        d += [
            (term, f"termo-{drw.lower()}", f"Termo de responsabilidade do autor do projeto de {name}", "written", "engenheiro", term_author(eng, name, "II")),
            (ins, f"seguro-{drw.lower()}", f"Comprovativo de seguro do autor do projeto de {name}", "written", "seguradora", insurance(eng, f"a elaboração do projeto de {name}")),
            (mem, f"memoria-{drw.lower()}", f"Memória descritiva do projeto de {name}", "written", "engenheiro",
             plain(eng, f"Memória descritiva e justificativa do projeto de {name}, relativo à {WORK} (conteúdo sintético).")),
            (drw, f"pecas-{drw.lower()}", f"Peças desenhadas do projeto de {name}", "drawn", "engenheiro", drawing(f"Projeto de {name}", f"{drw}-01", "1:100", eng, PLAN)),
        ]
    d += [
        ("TRFSCI", "termo-sci", "Termo de responsabilidade do autor da ficha de segurança contra incêndios", "written", "engenheiro", term_author(eng, "segurança contra incêndios em edifícios (ficha de segurança)", "II")),
        ("SRCSCI", "seguro-sci", "Comprovativo de seguro do autor da ficha de segurança contra incêndios", "written", "seguradora", insurance(eng, "a elaboração da ficha de segurança contra incêndios")),
        ("FSCI", "ficha-sci", "Ficha de segurança contra incêndios", "written", "engenheiro",
         plain(eng, "Ficha de segurança contra incêndios: utilização-tipo I (habitacional), 1.ª categoria de risco (conteúdo sintético).")),
        ("FEE", "ficha-estatistica", "Ficha de elementos estatísticos", "written", "requerente",
         plain(req, "Ficha de elementos estatísticos (Portaria n.º 235/2013): construção nova, habitação, 1 fogo, 554 m2 (sintético).")),
        ("ASAT", "apolice-acidentes", "Apólice de seguro de acidentes de trabalho", "written", "seguradora",
         plain(PEOPLE["seguradora"], "Apólice de seguro de acidentes de trabalho n.º SIM-AT-0001, Empresa de Construção Exemplo, Lda. (fictícia), válida em 2026-2027.")),
        ("IMPIC", "alvara-impic", "Número do alvará emitido pelo IMPIC, I. P.", "written", "diretor",
         plain(dire, "Empresa de Construção Exemplo, Lda. (fictícia): alvará de empreiteiro de obras públicas n.º 00000-PUB-SIM (fictício).")),
    ]
    return d


# -- rendering and post-processing ---------------------------------------------------------------
def render(html):
    with tempfile.TemporaryDirectory() as tmp:
        src, out = Path(tmp) / "doc.html", Path(tmp) / "doc.pdf"
        src.write_text(html, encoding="utf-8")
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", f"--user-data-dir={tmp}/profile",
                        "--no-pdf-header-footer", f"--print-to-pdf={out}", src.as_uri()],
                       check=True, capture_output=True, timeout=120)
        return out.read_bytes()


XMP = """<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
<rdf:Description rdf:about="" xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/" xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:xmp="http://ns.adobe.com/xap/1.0/" xmlns:pdf="http://ns.adobe.com/pdf/1.3/">
<pdfaid:part>2</pdfaid:part><pdfaid:conformance>B</pdfaid:conformance>
<dc:title><rdf:Alt><rdf:li xml:lang="x-default">{title}</rdf:li></rdf:Alt></dc:title>
<xmp:CreatorTool>rjue-engine exam builder</xmp:CreatorTool><xmp:CreateDate>{date}</xmp:CreateDate>
<xmp:ModifyDate>{date}</xmp:ModifyDate><pdf:Producer>rjue-engine exam builder</pdf:Producer>
</rdf:Description></rdf:RDF></x:xmpmeta>
<?xpacket end="w"?>"""


def finish(pdf, title, pdfa=True, fields=None):
    """Normalise with pypdf; optionally add PDF/A identification and hidden form fields."""
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import (ArrayObject, DecodedStreamObject, DictionaryObject, NameObject, NumberObject,
                               TextStringObject, FloatObject)
    w = PdfWriter(clone_from=PdfReader(io.BytesIO(pdf)))
    w.add_metadata({"/Title": title, "/Producer": "rjue-engine exam builder", "/Creator": "rjue-engine exam builder",
                    "/CreationDate": PDF_DATE, "/ModDate": PDF_DATE})
    if pdfa:
        meta = DecodedStreamObject()
        meta.set_data(XMP.format(title=esc(title), date=FIXED).encode("utf-8"))
        meta.update({NameObject("/Type"): NameObject("/Metadata"), NameObject("/Subtype"): NameObject("/XML")})
        w._root_object[NameObject("/Metadata")] = w._add_object(meta)
        icc = DecodedStreamObject()
        icc.set_data(ICC.read_bytes())
        icc.update({NameObject("/N"): NumberObject(3)})
        intent = DictionaryObject({NameObject("/Type"): NameObject("/OutputIntent"), NameObject("/S"): NameObject("/GTS_PDFA1"),
                                   NameObject("/OutputConditionIdentifier"): TextStringObject("sRGB IEC61966-2.1"),
                                   NameObject("/DestOutputProfile"): w._add_object(icc)})
        w._root_object[NameObject("/OutputIntents")] = ArrayObject([w._add_object(intent)])
    if fields:
        page = w.pages[0]
        refs = ArrayObject()
        for name, value in fields:
            field = DictionaryObject({
                NameObject("/FT"): NameObject("/Tx"), NameObject("/T"): TextStringObject(name),
                NameObject("/V"): TextStringObject(value), NameObject("/Type"): NameObject("/Annot"),
                NameObject("/Subtype"): NameObject("/Widget"), NameObject("/F"): NumberObject(4),
                NameObject("/Rect"): ArrayObject([FloatObject(0), FloatObject(0), FloatObject(0), FloatObject(0)]),
                NameObject("/P"): page.indirect_reference})
            refs.append(w._add_object(field))
        annots = page.get("/Annots")
        page[NameObject("/Annots")] = ArrayObject((list(annots.get_object()) if annots else []) + list(refs))
        w._root_object[NameObject("/AcroForm")] = DictionaryObject({NameObject("/Fields"): refs})
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()


def sign(pdf, signer_key, field_name="Assinatura1"):
    """Append a detached CMS signature (adbe.pkcs7.detached) as an incremental update."""
    import re
    from pypdf import PdfReader
    from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject, NameObject, NumberObject
    reader = PdfReader(io.BytesIO(pdf))
    size = int(reader.trailer["/Size"])
    root_ref = reader.trailer.raw_get("/Root")
    page_ref = reader.pages[0].indirect_reference
    prev = int(re.findall(rb"startxref\s+(\d+)", pdf)[-1])
    n_sig, n_field, n_acro = size, size + 1, size + 2

    def ser(obj):
        s = io.BytesIO()
        obj.write_to_stream(s)
        return s.getvalue()

    root = DictionaryObject(reader.trailer["/Root"])
    acro_old = root.get("/AcroForm")
    acro = DictionaryObject(acro_old.get_object()) if acro_old is not None else DictionaryObject()
    fields = list(acro.get("/Fields", ArrayObject()).get_object()) if "/Fields" in acro else []
    acro[NameObject("/Fields")] = ArrayObject(fields + [IndirectObject(n_field, 0, reader)])
    acro[NameObject("/SigFlags")] = NumberObject(3)
    root[NameObject("/AcroForm")] = IndirectObject(n_acro, 0, reader)
    page = DictionaryObject(reader.pages[0])
    annots = page.get("/Annots")
    page[NameObject("/Annots")] = ArrayObject((list(annots.get_object()) if annots is not None else [])
                                              + [IndirectObject(n_field, 0, reader)])
    hexlen = 16384
    sig_body = (b"<< /Type /Sig /Filter /Adobe.PPKLite /SubFilter /adbe.pkcs7.detached "
                b"/M (" + PDF_DATE.encode() + b") /ByteRange [0 0000000000 0000000000 0000000000] /Contents <"
                + b"0" * hexlen + b"> >>")
    field_body = (f"<< /FT /Sig /T ({field_name}) /V {n_sig} 0 R /Type /Annot /Subtype /Widget "
                  f"/Rect [0 0 0 0] /F 132 /P {page_ref.idnum} 0 R >>").encode()
    out = bytearray(pdf if pdf.endswith(b"\n") else pdf + b"\n")
    offsets = {}
    for num, body in ((root_ref.idnum, ser(root)), (page_ref.idnum, ser(page)), (n_sig, sig_body),
                      (n_field, field_body), (n_acro, ser(acro))):
        offsets[num] = len(out)
        out += f"{num} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += b"xref\n"
    for num in sorted(offsets):
        out += f"{num} 1\n{offsets[num]:010d} 00000 n \n".encode()
    trailer = DictionaryObject({NameObject("/Size"): NumberObject(n_acro + 1),
                                NameObject("/Root"): root_ref, NameObject("/Prev"): NumberObject(prev)})
    if "/ID" in reader.trailer:
        trailer[NameObject("/ID")] = reader.trailer["/ID"]
    out += b"trailer\n" + ser(trailer) + f"\nstartxref\n{xref_at}\n%%EOF\n".encode()
    start = out.index(b"/Contents <", offsets[n_sig]) + len(b"/Contents ")
    end = start + hexlen + 2
    byte_range = f"[0 {start:010d} {end:010d} {len(out) - end:010d}]".encode()
    br_at = out.index(b"/ByteRange [", offsets[n_sig]) + len(b"/ByteRange ")
    out[br_at:br_at + len(byte_range)] = byte_range
    signed = bytes(out[:start]) + bytes(out[end:])
    with tempfile.TemporaryDirectory() as tmp:
        data, der = Path(tmp) / "data", Path(tmp) / "sig.der"
        data.write_bytes(signed)
        subprocess.run(["openssl", "cms", "-sign", "-binary", "-noattr", "-md", "sha256", "-in", str(data),
                        "-signer", str(PKI / f"{signer_key}.pem"), "-inkey", str(PKI / f"{signer_key}.key"),
                        "-certfile", str(PKI / "ca.pem"), "-outform", "DER", "-out", str(der)], check=True, capture_output=True)
        sig_hex = der.read_bytes().hex().encode()
        assert len(sig_hex) <= hexlen, "signature larger than the reserved space"
        out[start + 1:start + 1 + len(sig_hex)] = sig_hex
        check = subprocess.run(["openssl", "cms", "-verify", "-binary", "-inform", "DER", "-in", str(der),
                                "-content", str(data), "-CAfile", str(PKI / "ca.pem"), "-out", "/dev/null"],
                               capture_output=True, text=True)
        if "Verification successful" not in check.stderr:
            raise RuntimeError(f"signature self-check failed: {check.stderr.strip()}")
    return bytes(out)


# -- dossiers -------------------------------------------------------------------------------------
def build():
    ensure_pki()
    if DOSSIERS.exists():
        shutil.rmtree(DOSSIERS)
    docs = documents_a()
    rendered = {}
    print(f"rendering {len(docs)} documents of dossier A ...")
    for code, stem, title, kind, signer, html in docs:
        rendered[stem] = render(page(title, html))

    variants = {
        "C:TRPARQ": render(page("Termo de responsabilidade do autor do projeto de arquitetura", paras(
            f"Eu, {PEOPLE['arquiteto']['name']}, declaro que sou o autor do projeto de arquitetura da {WORK} em "
            f"{SITE['address']} e que o mesmo foi elaborado com todo o cuidado.") + signature_line(PEOPLE["arquiteto"]))),
        "C:MDARQ": render(page("Memória descritiva e justificativa", memory("610", "1200"))),
    }
    summary_c = [(k, label, ("120" if k == "area_parcela" else v), u) for k, label, v, u in SUMMARY_A]
    variants["C:REQ"] = render(page("Requerimento de comunicação prévia (modelo do Anexo I)", request_doc(summary_c)))

    plan = {
        "A": {"omit": set(), "replace": {}, "unsigned": set(), "no_pdfa": set(), "not_pdf": set()},
        "B": {"omit": {"estimativa-encargos", "registo-fotografico"}, "replace": {}, "unsigned": set(), "no_pdfa": set(), "not_pdf": set()},
        "C": {"omit": set(), "replace": {"termo-arquitetura": "C:TRPARQ", "memoria-descritiva": "C:MDARQ", "requerimento": "C:REQ"},
              "unsigned": {"termo-diretor-obra"}, "no_pdfa": {"memoria-pdpap"}, "not_pdf": {"cortes"}},
    }
    stems = {d[1] for d in docs}
    for name, p in plan.items():
        named = p["omit"] | set(p["replace"]) | p["unsigned"] | p["no_pdfa"] | p["not_pdf"]
        assert named <= stems, f"dossier {name} names unknown documents: {sorted(named - stems)}"
    for name, p in plan.items():
        folder = DOSSIERS / name
        folder.mkdir(parents=True)
        files = []
        for code, stem, title, kind, signer, _ in docs:
            if stem in p["omit"]:
                continue
            fname = f"{code}-{stem}.pdf"
            if stem in p["not_pdf"]:
                data = png(640, 400, 90)  # an image saved with a .pdf name
            else:
                summary = (summary_c if name == "C" else SUMMARY_A) if stem == "requerimento" else None
                fields = [(f"sintese.{k}", v) for k, _, v, _ in summary] if summary else None
                pdf = finish(variants[p["replace"][stem]] if stem in p["replace"] else rendered[stem], title,
                             pdfa=stem not in p["no_pdfa"], fields=fields)
                data = pdf if stem in p["unsigned"] else sign(pdf, signer)
            (folder / fname).write_bytes(data)
            files.append({"slot": code, "file": fname, "title": title, "kind": kind,
                          "signed_by": None if stem in p["unsigned"] or stem in p["not_pdf"] else signer})
        submission = {"dossier": name, "simulated": True, "procedure": "cp-edificacao",
                      "municipality": "Celorico de Basto", "form_subject": "form:nopaper:celorico-de-basto:CP:CPEDI",
                      "applicant": {"name": PEOPLE["requerente"]["name"], "nif": NIF}, "site": SITE,
                      "operation": WORK, "submitted_at": "2026-10-14", "files": files}
        (folder / "submission.json").write_text(json.dumps(submission, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"dossier {name}: {len(files)} files")
    write_answers()
    write_manifest()


# -- answer key --------------------------------------------------------------------------------------
def law_quote(ref):
    pack = json.loads((ROOT / "rules" / "cp-edificacao.json").read_text(encoding="utf-8"))
    for r in pack["rules"]:
        if r["passage"] == ref:
            return r["quote"]
    if ref in pack["general_provisions"]:
        return pack["general_provisions"][ref]["quote"]
    raise KeyError(ref)


def write_answers():
    text = Store().text_for(LAW).text
    wording = "observa as normas legais e regulamentares aplicáveis à pretensão"
    assert wording in text
    common = [
        {"id": "dwg-site-plan", "status": "finding", "certain": True, "artifact": True, "type": "missing_complement",
         "target": {"slot": "PI"}, "law": {"ref": "VI.1.b", "quote": law_quote("VI.1.b")},
         "note": "The site plan is delivered as PDF/A only; the generator cannot produce the DWG the law adds."},
        {"id": "qualified-signatures", "status": "not_assessed", "certain": True, "type": "signature_qualification",
         "target": {"all_signed_files": True}, "law": {"ref": "VI.1", "quote": law_quote("VI.1")},
         "note": "Signatures use test certificates: valid, but whether they are qualified cannot be assessed (they are not)."},
        {"id": "external-opinions", "status": "not_assessed", "certain": True, "type": "conditional_requirement",
         "target": {"slot": "PAAEE"}, "law": {"ref": "V.27.h", "quote": law_quote("V.27.h")},
         "note": "Whether consulting an external entity is mandatory depends on facts (servidões, restrictions) the case does not hold."},
        {"id": "gas-project", "status": "not_assessed", "certain": True, "type": "conditional_requirement",
         "target": {"slot": "TRPIG"}, "law": {"ref": "V.27.i.iv", "quote": law_quote("V.27.i.iv")},
         "note": "'quando exigível, nos termos da lei': whether the house needs a gas project is not stated."},
        {"id": "pdfa-conformance", "status": "provisional", "certain": False, "type": "pdfa_conformance",
         "target": {"files_claiming_pdfa": True}, "law": {"ref": "VI.1.a", "quote": law_quote("VI.1.a")},
         "note": "Files carry PDF/A-2b identification and an sRGB output intent; conformance is unconfirmed until a reference validator runs."},
    ]
    dossiers = {
        "A": common,
        "B": common + [
            {"id": "missing-charges-estimate", "status": "finding", "certain": True, "type": "missing_required",
             "target": {"rule": "V.27.g"}, "law": {"ref": "V.27.g", "quote": law_quote("V.27.g")}},
            {"id": "missing-photographs", "status": "finding", "certain": True, "type": "missing_required",
             "target": {"rule": "V.15", "slot": "FOTO"}, "law": {"ref": "V.15", "quote": law_quote("V.15")}},
        ],
        "C": common + [
            {"id": "not-a-pdf", "status": "finding", "certain": True, "type": "not_pdf",
             "target": {"slot": "CORTES", "file": "CORTES-cortes.pdf"}, "law": {"ref": "VI.1.a", "quote": law_quote("VI.1.a")}},
            {"id": "no-pdfa-identification", "status": "finding", "certain": True, "type": "not_pdfa",
             "target": {"slot": "MDPAP", "file": "MDPAP-memoria-pdpap.pdf"}, "law": {"ref": "VI.1.a", "quote": law_quote("VI.1.a")}},
            {"id": "unsigned-declaration", "status": "finding", "certain": True, "type": "unsigned",
             "target": {"slot": "TRDO", "file": "TRDO-termo-diretor-obra.pdf"}, "law": {"ref": "VI.1", "quote": law_quote("VI.1")}},
            {"id": "declaration-wording", "status": "finding", "certain": True, "type": "template_wording_missing",
             "target": {"slot": "TRPARQ", "file": "TRPARQ-termo-arquitetura.pdf"},
             "law": {"ref": "VII.I", "quote": wording}},
            {"id": "built-area-mismatch", "status": "finding", "certain": True, "type": "value_mismatch",
             "target": {"field": "area_total_construcao", "files": ["REQ-requerimento.pdf", "MDARQ-memoria-descritiva.pdf"]},
             "basis": "documents", "values": {"REQ-requerimento.pdf": "554 m2", "MDARQ-memoria-descritiva.pdf": "610 m2"}},
            {"id": "plot-area-typo", "status": "finding", "certain": True, "type": "impossible_value",
             "target": {"field": "area_parcela", "file": "REQ-requerimento.pdf"}, "basis": "documents",
             "values": {"area_parcela": "120 m2", "area_implantacao": "277 m2", "area_permeavel": "850 m2",
                        "area_impermeabilizacao": "350 m2", "MDARQ-memoria-descritiva.pdf": "1200 m2"},
             "also_accept": [{"type": "impossible_value", "field": f} for f in ("area_implantacao", "area_permeavel", "area_impermeabilizacao")]
                            + [{"type": "value_mismatch", "field": "area_parcela"}],
             "note": "One typo (1200 typed as 120) with several symptoms; any of them counts, none is a false alarm."},
        ],
    }
    body = {"version": "rjue-exam-0.1", "procedure": "cp-edificacao", "law": LAW,
            "review": "proposed from the reviewed rule pack; not human-approved",
            "statuses": {"finding": "the engine must report it", "not_assessed": "the engine must say it cannot decide, naming the missing fact",
                         "provisional": "not scored until a reference check exists"},
            "dossiers": dossiers}
    for name, expected in dossiers.items():
        present = {f["file"] for f in json.loads((DOSSIERS / name / "submission.json").read_text(encoding="utf-8"))["files"]}
        for e in expected:
            named = [e["target"]["file"]] if "file" in e["target"] else e["target"].get("files", [])
            assert set(named) <= present, f"answer {e['id']} names files not in dossier {name}: {set(named) - present}"
    (EXAM / "answers.json").write_text(json.dumps(body, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def write_manifest():
    files = {}
    for path in sorted(p for p in EXAM.rglob("*") if p.is_file() and p.name not in {"manifest.json", "scores.jsonl"} and "__pycache__" not in p.parts
                       and p.suffix not in {".py", ".md"} and p.parent != PKI):
        files[str(path.relative_to(EXAM))] = hashlib.sha256(path.read_bytes()).hexdigest()
    (EXAM / "manifest.json").write_text(json.dumps({"version": "rjue-exam-0.1", "files": files}, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()
