"""D1 and D2 rows from generated expedientes: the reader sees the extracted text of a file (what any PDF reader gives a
técnico) through window() (D14: first pages, signal pages, the rest, 9 000 characters) and answers with the element it is (D1) or the facts it states, with the page (D2). Keys come from labels.jsonl,
written by the generator at the same time as the file, never from a model.

    .venv-of-rjue/bin/python -I generator/d1d2.py --src training/expedientes --out training/data           # train rows
    .venv-of-rjue/bin/python -I generator/d1d2.py --src sealed/expedientes --out sealed --prefix sealed    # sealed rows
"""
import argparse
import hashlib
import io
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pypdf import PdfReader  # noqa: E402

PORT = {p["id"]: p for p in json.loads((ROOT / "structure" / "portaria-320-2026-1.json").read_text(encoding="utf-8"))["passages"]}
sys.path.insert(0, str(ROOT / "generator"))
import guard  # noqa: E402  (D13: every row's key must be inside the language the reader is held to)

MAXCH = 3500  # the r1–r8 window (first 3,500 characters); kept only as a record, window() below is what rows use since r9 (D14)
WINDOW_CH, PAGE_CH, HEAD_PAGES = 65000, 65000, 0   # D16 (round 10): the whole document; D14's 11 000 / 2 500 / 2 and the signal-page order are retired
SIGNAL = re.compile(r"€|\btotal\b|\bm2\b|m²|\bpiso|\bfogo|\bprazo|\bmeses\b|\bdias\b|ap[oó]lice|validade|altura|assin|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}", re.I)


def cut(text, limit=PAGE_CH):
    """text up to limit characters, ending on a whitespace boundary (so every token shown is whole)."""
    if len(text) <= limit:
        return text
    k = text.rfind(" ", 0, limit); k2 = text.rfind("\n", 0, limit)
    return text[:max(k, k2)] if max(k, k2) > 0 else text[:limit]


def window(pages):
    """What the reader sees of a document (D16, round 10): the WHOLE document — every page, uncut, in order — up to WINDOW_CH
    characters (≈ the base model's 32k-token context minus the prompt and the answer). Only a document longer than that loses
    its last pages, and then the header lists the pages shown, so the grammar admits only those. Returns (text with
    «[página n]» blocks, header note or "")."""
    shown, budget = [], WINDOW_CH
    for i, t in enumerate(pages):
        if len(t) + 1 > budget:
            break
        shown.append(i); budget -= len(t) + 1
    if not shown:                                   # a single page longer than the whole budget: show its head
        pages = [cut(pages[0], WINDOW_CH)] + list(pages[1:]); shown = [0]
    text = "\n".join(f"[página {i + 1}]\n{pages[i]}" for i in shown)
    note = "" if len(shown) == len(pages) else " — páginas mostradas: " + ", ".join(str(i + 1) for i in shown)
    return text, note


KEYWORD = {"pisos_acima_soleira": "piso", "fogos": "fogo", "prazo_meses": "mes", "area_total_construcao": "constru", "area_parcela": "parcela|terreno|lote",
           "area_implantacao": "implanta", "altura_edificacao": "altura", "custo_total": "custo|valor|total", "validade_seguro_fim": "validade|até|ate",
           "apolice": "apólice|apolice", "uso": "destina|uso|habita", "wording_annex_vii": "observa"}


def quote_for(page_text, value, field, line=None):
    """The quote the key gives for a fact (D13): a token-aligned piece of the collapsed page that holds the value as a whole
    token — the labelled line when it is on the page, else the sentence holding the value (preferring one with the field's
    keyword), narrowed to ±120 characters on token boundaries when long. None when the value is not a whole token of the page."""
    t = guard.collapse(page_text); v = guard.collapse(value)
    if line:
        ln = guard.collapse(line)
        if guard.aligned(t, ln) and guard.aligned(ln, v):
            return ln
    if not guard.aligned(t, v):
        return None
    sents = [x.strip() for x in re.split(r"(?<=[.;])\s+", t)]
    cands = [x for x in sents if guard.aligned(t, x) and guard.aligned(x, v)]
    kw = re.compile(KEYWORD.get(field, "(?!x)x"), re.I)
    best = next((x for x in cands if kw.search(x)), cands[0] if cands else t)
    if len(best) > 300:
        best = narrow(best, v)
    return best if guard.aligned(t, best) and guard.aligned(best, v) else None


def narrow(text, value, radius=120):
    sp = guard.tokens(text)
    k = text.find(value)
    while k >= 0 and not any(a == k for a, _ in sp):
        k = text.find(value, k + 1)
    if k < 0:
        return text
    a = min((x for x, _ in sp if x >= k - radius), default=k)
    b = max((y for _, y in sp if y <= k + len(value) + radius), default=k + len(value))
    return text[a:b]
D1_PROMPT = ("Um expediente de comunicação prévia de obras de edificação (CPEDI, Celorico de Basto) traz o ficheiro abaixo. Os elementos instrutórios que este "
             "pedido pode levar são estes (id — texto da Portaria n.º 320/2026/1):\n{shortlist}\n\nLê o texto do ficheiro e diz qual destes elementos ele é: "
             "copia o id em «elemento» e o texto da passagem, letra a letra, em «citacao». Se o ficheiro não é nenhum deles, elemento null e tipo nao_e_elemento; "
             "se não se lê, tipo ilegivel.\nRegras: (1) o ficheiro é o elemento só quando é a própria peça instrutória (a memória, o termo, a planta, a estimativa, "
             "a certidão, o comprovativo), preenchida ou em minuta por preencher; a memória descritiva e justificativa de uma operação urbanística (obras de "
             "edificação, loteamento, alteração de alvará, obras de urbanização) é o elemento 9, mesmo quando o cabeçalho fala de outra operação ou de outro "
             "requerente — se descreve outra obra, isso vê-se depois nos factos; uma memória de apresentação de empresa, de candidatura ou de negócio não é "
             "elemento. (2) Um documento que fala sobre elementos — norma de instrução, regulamento ou anexo, capítulo "
             "ou artigos de regulamento, postura, guia técnico, nota técnica, nota explicativa, esclarecimento, análise, parecer, apresentação, critérios, lista de "
             "elementos, ficha de verificação, deliberação, ata, informação interna, instruções de preenchimento, manual, caderno de encargos, ficha de projeto, "
             "diagnóstico — não é elemento: elemento null, tipo nao_e_elemento. (3) Só os termos de responsabilidade são próprios de cada procedimento: um termo "
             "de outro procedimento (utilização do edifício, conclusão da obra, receção de obras de urbanização, loteamento) não é elemento deste pedido. (4) tipo escrito = peça "
             "de texto (memória, termo, estimativa, calendarização, certidão, comprovativo, registo fotográfico), mesmo com tabelas, quadros ou figuras; tipo desenhado = "
             "peça desenhada (planta, alçado, corte, pormenor, levantamento topográfico, peças desenhadas).\nResponde {{\"elemento\": <id ou null>, "
             "\"citacao\": <texto ou \"\">, \"tipo\": \"escrito\"|\"desenhado\"|\"nao_e_elemento\"|\"ilegivel\"}}."
             "\n\nFicheiro: {name} ({pages} página(s)){shown}\n---\n{text}\n---")
DOCS = json.loads((ROOT / "celorico" / "mapping" / "documents.json").read_text(encoding="utf-8"))["documents"]
SHORTLIST_IDS = sorted({f"portaria-320-2026-1:{d['passages'][0]}" for d in DOCS if "CP/CPEDI" in d["requests"] and d["passages"]},
                       key=lambda i: [int(x) if x.isdigit() else x for x in re.split(r"[.-]", i.split(":anexo-")[1])])
SHORTLIST = "\n".join(f"{i} — {PORT[i]['text']}" for i in SHORTLIST_IDS if i in PORT)
D2_FACT = ("Lê o documento abaixo de um expediente CPEDI (Celorico de Basto) e responde à pergunta com {{\"valor\": <texto exato como aparece ou null>, "
           "\"pagina\": <número ou null>, \"citacao\": <a linha onde aparece ou \"\">}}. Se o documento não o diz, valor null.\n\n"
           "Pergunta: {question}\n\nFicheiro: {name} ({pages} página(s)){shown}\n---\n{text}\n---")
QUESTIONS = {"area_total_construcao": "Qual é a área total de construção declarada?", "area_parcela": "Qual é a área da parcela (ou do terreno) declarada?",
             "area_implantacao": "Qual é a área total de implantação declarada?", "pisos_acima_soleira": "Quantos pisos acima da cota de soleira declara?",
             "uso": "Qual é o uso a que se destina a edificação?", "fogos": "Quantos fogos declara?", "altura_edificacao": "Qual é a altura da edificação declarada?",
             "custo_total": "Qual é o valor da estimativa do custo total da obra?", "validade_seguro_fim": "Até que data é válida a apólice de seguro?",
             "apolice": "Qual é o número da apólice?", "prazo_meses": "Qual é a duração prevista da obra, em meses?",
             "wording_annex_vii": "O termo contém a declaração de conformidade exigida pelo Anexo VII (que o projeto observa as normas legais e regulamentares aplicáveis)? Se sim, valor = essa frase tal como aparece no termo; se não, null."}
ABSENT = {"area_total_construcao": ["CEO", "CRP", "ASAT", "IMPIC", "FSCI"], "custo_total": ["CRP", "FOTO", "FEE", "MDARQ", "MDARQ"], "validade_seguro_fim": ["TRDO", "CEO", "MDARQ"],
          "pisos_acima_soleira": ["EOCT", "CEO", "ASAT"], "apolice": ["REQ", "CEO", "FEE"], "prazo_meses": ["MDARQ", "MDARQ", "CEO", "TRDO"]}
# a question is asked as absent only of a file whose labels carry no such fact (a memória may now state its cost or prazo); MDARQ twice = asked more often:
# the memória that states a prazo in DAYS answers prazo_meses with null (the days-vs-months trap), the one with areas but no cost answers custo_total with null


def rid(task, *parts):
    return f"{task}:{hashlib.sha256('|'.join(parts).encode('utf-8')).hexdigest()[:16]}"


def extract(path, is_pdf):
    if not is_pdf:
        return None, 0
    try:
        r = PdfReader(str(path)); pages = [(pg.extract_text() or "").replace("DOCUMENTO SIMULADO - SANEAMENTO-ENGINE - SEM VALOR LEGAL", "").strip() for pg in r.pages]
        return pages, len(pages)
    except Exception:
        return None, 0


def noisy(text, rng):
    """OCR-like damage: dropped accents, broken words at line ends, a few swapped letters, double spaces."""
    out = []
    for ch in text:
        r = rng.random()
        if r < 0.004:
            continue
        if r < 0.012 and ch.isalpha():
            out.append(rng.choice("aeiouxlnrs"))
        elif r < 0.02 and ch == " ":
            out.append("-\n" if rng.random() < 0.5 else "  ")
        else:
            out.append(ch)
    t = "".join(out)
    for a_, b_ in (("ç", "c"), ("ã", "a"), ("é", "e"), ("ó", "o"), ("í", "i")):
        if rng.random() < 0.5:
            t = t.replace(a_, b_)
    return t


def perline(text):
    """Layout damage seen on real PDFs (the OA minutas): the extractor returns one word per line."""
    return "\n".join(text.split())


def damage(text, rng):
    r = rng.random()
    if r < 0.55:
        return noisy(text, rng)
    if r < 0.85:
        return perline(text)
    return perline(noisy(text, rng))


MUNIS = ["cascais", "valongo", "braga", "porto", "guimaraes", "fafe", "amarante", "cmcb", "celorico", "vnfamalicao", "lisboa"]


def opaque_name(rng, stem=""):
    """A file name that says nothing (or lies) about the content: real submissions arrive like this, and the reader must read the text, not the name."""
    n = rng.randrange(1, 9999)
    styles = [lambda: f"doc_{n:04d}.pdf", lambda: f"scan{n}.pdf", lambda: f"IMG_{n}.pdf", lambda: f"{rng.choice(MUNIS)}_{n}.pdf",
              lambda: f"{rng.choice(MUNIS)}_{rng.choice(['md', 'tr', 'pl', 'proc', 'lot', 'cp'])}_{n}.pdf", lambda: f"2026-{rng.randrange(1, 12):02d}-{rng.randrange(1, 28):02d}_{n}.pdf",
              lambda: f"ficheiro ({rng.randrange(1, 9)}).pdf", lambda: f"anexo{rng.randrange(1, 30)}.pdf", lambda: f"{n}l2026_{rng.choice(['md', 'a', 'b', 'c'])}.pdf",
              lambda: f"Documento{rng.randrange(1, 40)}.pdf", lambda: f"{rng.choice(['PROJETO', 'processo', 'entrega', 'final', 'rev'])}_{n}.pdf",
              lambda: f"{rng.choice(['memoria', 'termo', 'planta', 'certidao', 'estimativa', 'calendarizacao', 'levantamento'])}.pdf"]   # the last one may lie
    return rng.choice(styles)()


def stranger_name(slot, stem, rng):
    if rng.random() < 0.5:
        return opaque_name(rng, stem)
    styles = [lambda: f"{slot}_{stem.replace('-', '_')}.pdf", lambda: f"{stem.replace('-', '')[:40]}.pdf", lambda: f"{rng.randrange(1, 60):02d}_{stem.replace('-', '_')[:30]}.pdf",
              lambda: f"{slot.lower()}-{rng.randrange(100, 999)}.pdf", lambda: f"{stem.split('-')[0].upper()}_{rng.choice(['v1', 'final', 'rev2', 'assinado'])}.pdf"]
    return rng.choice(styles)()


def line_with(pages, page, value):
    for ln in pages[page - 1].splitlines():
        if value and value in ln:
            return ln.strip()
    joined = " ".join(pages[page - 1].split())
    i = joined.find(value) if value else -1
    return joined[max(0, i - 60): i + len(value) + 60] if i >= 0 else ""


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--src", required=True); ap.add_argument("--out", required=True); ap.add_argument("--prefix", default="")
    ap.add_argument("--seed", type=int, default=5); ap.add_argument("--augment", action="store_true", help="training only: add noisy copies and stranger file names")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    src = ROOT / a.src
    d1, d2, stats, dropped = [], [], {"files": 0, "illegible": 0, "noise": 0, "facts": 0, "absent": 0, "dropped": 0}, []
    for folder in sorted(p for p in src.iterdir() if p.is_dir()):
        for lab in (json.loads(l) for l in (folder / "labels.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()):
            stats["files"] += 1
            pages, n = extract(folder / lab["file"], lab["is_pdf"])
            text, shown = window(pages) if pages else ("(ficheiro ilegível: não é um PDF)", "")
            cpages = [guard.collapse(t) for t in pages] if pages else []
            # D1
            if pages is None:
                ans = {"elemento": None, "citacao": "", "tipo": "ilegivel"}; stats["illegible"] += 1
            elif lab["noise"] or not lab["element"] or lab["element"] not in SHORTLIST_IDS:
                ans = {"elemento": None, "citacao": "", "tipo": "nao_e_elemento"}; stats["noise"] += lab["noise"]
            else:
                ans = {"elemento": lab["element"], "citacao": PORT[lab["element"]]["text"], "tipo": "desenhado" if lab["kind"] == "drawn" else "escrito"}
            shown_name = opaque_name(rng) if (a.augment and rng.random() < 0.5) else lab["file"]   # training: 40 % of base rows carry an uninformative name
            d1.append({"id": rid("d1", lab["expediente"], lab["file"]), "task": "d1_elemento", "prompt": D1_PROMPT.format(shortlist=SHORTLIST, name=shown_name, pages=n or 0, shown=shown, text=text),
                       "answer": json.dumps(ans, ensure_ascii=False), "expediente": lab["expediente"]})
            if a.augment and pages is not None and rng.random() < 0.45:
                stem = lab["file"][len(lab["slot"]) + 1:-4] if lab["file"].startswith(lab["slot"] + "-") else lab["file"][:-4]
                sname = stranger_name(lab["slot"], stem, rng)
                ntext, nshown = window([damage(t, rng) for t in pages])
                d1.append({"id": rid("d1", lab["expediente"], lab["file"], "aug"), "task": "d1_elemento", "prompt": D1_PROMPT.format(shortlist=SHORTLIST, name=sname, pages=n, shown=nshown, text=ntext),
                           "answer": json.dumps(ans, ensure_ascii=False), "expediente": lab["expediente"]})
                stats["augmented"] = stats.get("augmented", 0) + 1
            if pages is None:
                continue
            # D2: every labelled fact, plus questions the document does not answer
            for f in lab["facts"]:
                if f["field"] not in QUESTIONS:
                    continue
                present = bool(f["value"])
                if present:
                    q = quote_for(cpages[f["page"] - 1], f["value"], f["field"], f.get("line")) if f["page"] <= len(cpages) else None
                    ans = {"valor": f["value"], "pagina": f["page"], "citacao": q or ""}
                else:
                    ans = {"valor": None, "pagina": None, "citacao": ""}
                prompt = D2_FACT.format(question=QUESTIONS[f["field"]], name=lab["file"], pages=n, shown=shown, text=text)
                why = "valor não é um token inteiro da página" if (present and not q) else guard.check("d2_facto", prompt, json.dumps(ans, ensure_ascii=False))
                if why:
                    # D13/D14: a key the reader cannot give (page not shown, value cut by the window) is never a training row
                    stats["dropped"] += 1; dropped.append((lab["expediente"], lab["file"], f["field"], why)); continue
                stats["facts"] += 1
                d2.append({"id": rid("d2", lab["expediente"], lab["file"], f["field"]), "task": "d2_facto", "prompt": prompt, "answer": json.dumps(ans, ensure_ascii=False), "expediente": lab["expediente"]})
            have = {f["field"] for f in lab["facts"] if f["value"]}
            for field, slots in ABSENT.items():
                if field not in have and rng.random() < 0.35 * slots.count(lab["slot"]):
                    stats["absent"] += 1
                    d2.append({"id": rid("d2", lab["expediente"], lab["file"], field, "absent"), "task": "d2_facto",
                               "prompt": D2_FACT.format(question=QUESTIONS[field], name=lab["file"], pages=n, shown=shown, text=text),
                               "answer": json.dumps({"valor": None, "pagina": None, "citacao": ""}, ensure_ascii=False), "expediente": lab["expediente"]})
            if lab["noise"] and rng.random() < 0.5:
                # a question asked of a noise file (funding sheet, tender spec, norm): the answer is null even when a similar-looking number is on the page
                field = rng.choice(sorted(QUESTIONS))
                stats["absent"] += 1
                d2.append({"id": rid("d2", lab["expediente"], lab["file"], field, "noise"), "task": "d2_facto",
                           "prompt": D2_FACT.format(question=QUESTIONS[field], name=lab["file"], pages=n, shown=shown, text=text),
                           "answer": json.dumps({"valor": None, "pagina": None, "citacao": ""}, ensure_ascii=False), "expediente": lab["expediente"]})
    for r in d1:
        why = guard.check("d1_elemento", r["prompt"], r["answer"])
        assert not why, (r["id"], why)
    if dropped:
        import collections
        print("dropped (key outside the language):", dict(collections.Counter(w for *_, w in dropped)))
        for x in dropped[:8]:
            print("  ", x)
    out = ROOT / a.out
    for name, rows in (("d1", d1), ("d2", d2)):
        rng.shuffle(rows)
        if a.prefix:
            path = out / f"{name}-test.jsonl"
        else:
            (out / name).mkdir(parents=True, exist_ok=True); path = out / name / "train.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps({k: r[k] for k in ("id", "task", "prompt", "answer")}, ensure_ascii=False) + "\n")
        print(f"{path.relative_to(ROOT)}: {len(rows)} rows")
    print(stats)


if __name__ == "__main__":
    main()
