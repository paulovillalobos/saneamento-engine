"""D1 and D2 rows from generated expedientes: the reader sees the extracted text of a file (what any PDF reader gives a
técnico) and answers with the element it is (D1) or the facts it states, with the page (D2). Keys come from labels.jsonl,
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
MAXCH = 3500  # characters of document text shown to the reader (the first pages; a termo or a memória fits whole)
D1_PROMPT = ("Um expediente de comunicação prévia de obras de edificação (CPEDI, Celorico de Basto) traz o ficheiro abaixo. Os elementos instrutórios que este "
             "pedido pode levar são estes (id — texto da Portaria n.º 320/2026/1):\n{shortlist}\n\nLê o texto do ficheiro e diz qual destes elementos ele é: "
             "copia o id em «elemento» e o texto da passagem, letra a letra, em «citacao». Se o ficheiro não é nenhum deles, elemento null e tipo nao_e_elemento; "
             "se não se lê, tipo ilegivel. Responde {{\"elemento\": <id ou null>, \"citacao\": <texto ou \"\">, \"tipo\": \"escrito\"|\"desenhado\"|\"nao_e_elemento\"|\"ilegivel\"}}."
             "\n\nFicheiro: {name} ({pages} página(s))\n---\n{text}\n---")
DOCS = json.loads((ROOT / "celorico" / "mapping" / "documents.json").read_text(encoding="utf-8"))["documents"]
SHORTLIST_IDS = sorted({f"portaria-320-2026-1:{d['passages'][0]}" for d in DOCS if "CP/CPEDI" in d["requests"] and d["passages"]},
                       key=lambda i: [int(x) if x.isdigit() else x for x in re.split(r"[.-]", i.split(":anexo-")[1])])
SHORTLIST = "\n".join(f"{i} — {PORT[i]['text']}" for i in SHORTLIST_IDS if i in PORT)
D2_FACT = ("Lê o documento abaixo de um expediente CPEDI (Celorico de Basto) e responde à pergunta com {{\"valor\": <texto exato como aparece ou null>, "
           "\"pagina\": <número ou null>, \"citacao\": <a linha onde aparece ou \"\">}}. Se o documento não o diz, valor null.\n\n"
           "Pergunta: {question}\n\nFicheiro: {name} ({pages} página(s))\n---\n{text}\n---")
QUESTIONS = {"area_total_construcao": "Qual é a área total de construção declarada?", "area_parcela": "Qual é a área da parcela (ou do terreno) declarada?",
             "area_implantacao": "Qual é a área total de implantação declarada?", "pisos_acima_soleira": "Quantos pisos acima da cota de soleira declara?",
             "uso": "Qual é o uso a que se destina a edificação?", "fogos": "Quantos fogos declara?", "altura_edificacao": "Qual é a altura da edificação declarada?",
             "custo_total": "Qual é o valor da estimativa do custo total da obra?", "validade_seguro_fim": "Até que data é válida a apólice de seguro?",
             "apolice": "Qual é o número da apólice?", "prazo_meses": "Qual é a duração prevista da obra, em meses?",
             "wording_annex_vii": "O termo contém a declaração de conformidade exigida pelo Anexo VII (que o projeto observa as normas legais e regulamentares aplicáveis)? Se sim, valor = essa frase tal como aparece no termo; se não, null."}
ABSENT = {"area_total_construcao": ["CEO", "CRP", "ASAT", "IMPIC", "FSCI"], "custo_total": ["CRP", "FOTO", "FEE"], "validade_seguro_fim": ["TRDO", "CEO", "MDARQ"],
          "pisos_acima_soleira": ["EOCT", "CEO", "ASAT"], "apolice": ["REQ", "CEO", "FEE"]}


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


def stranger_name(slot, stem, rng):
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
    d1, d2, stats = [], [], {"files": 0, "illegible": 0, "noise": 0, "facts": 0, "absent": 0}
    for folder in sorted(p for p in src.iterdir() if p.is_dir()):
        for lab in (json.loads(l) for l in (folder / "labels.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()):
            stats["files"] += 1
            pages, n = extract(folder / lab["file"], lab["is_pdf"])
            text = "\n".join(f"[página {i + 1}]\n{t}" for i, t in enumerate(pages))[:MAXCH] if pages else "(ficheiro ilegível: não é um PDF)"
            # D1
            if pages is None:
                ans = {"elemento": None, "citacao": "", "tipo": "ilegivel"}; stats["illegible"] += 1
            elif lab["noise"] or not lab["element"] or lab["element"] not in SHORTLIST_IDS:
                ans = {"elemento": None, "citacao": "", "tipo": "nao_e_elemento"}; stats["noise"] += lab["noise"]
            else:
                ans = {"elemento": lab["element"], "citacao": PORT[lab["element"]]["text"], "tipo": "desenhado" if lab["kind"] == "drawn" else "escrito"}
            d1.append({"id": rid("d1", lab["expediente"], lab["file"]), "task": "d1_elemento", "prompt": D1_PROMPT.format(shortlist=SHORTLIST, name=lab["file"], pages=n or 0, text=text),
                       "answer": json.dumps(ans, ensure_ascii=False), "expediente": lab["expediente"]})
            if a.augment and pages is not None and rng.random() < 0.35:
                stem = lab["file"][len(lab["slot"]) + 1:-4]
                sname = stranger_name(lab["slot"], stem, rng)
                ntext = "\n".join(f"[página {i + 1}]\n{noisy(t, rng)}" for i, t in enumerate(pages))[:MAXCH]
                d1.append({"id": rid("d1", lab["expediente"], lab["file"], "aug"), "task": "d1_elemento", "prompt": D1_PROMPT.format(shortlist=SHORTLIST, name=sname, pages=n, text=ntext),
                           "answer": json.dumps(ans, ensure_ascii=False), "expediente": lab["expediente"]})
                stats["augmented"] = stats.get("augmented", 0) + 1
            if pages is None:
                continue
            # D2: every labelled fact, plus questions the document does not answer
            for f in lab["facts"]:
                if f["field"] not in QUESTIONS:
                    continue
                if f["field"] == "wording_annex_vii":
                    present = bool(f["value"])
                    ans = {"valor": f["value"] if present else None, "pagina": f["page"] if present else None, "citacao": line_with(pages, f["page"], f["value"]) if present else ""}
                else:
                    ans = {"valor": f["value"], "pagina": f["page"], "citacao": line_with(pages, f["page"], f["value"])}
                    if not ans["citacao"]:
                        continue  # the value did not survive extraction (should not happen; counted below)
                stats["facts"] += 1
                d2.append({"id": rid("d2", lab["expediente"], lab["file"], f["field"]), "task": "d2_facto",
                           "prompt": D2_FACT.format(question=QUESTIONS[f["field"]], name=lab["file"], pages=n, text=text), "answer": json.dumps(ans, ensure_ascii=False), "expediente": lab["expediente"]})
            for field, slots in ABSENT.items():
                if lab["slot"] in slots and rng.random() < 0.35:
                    stats["absent"] += 1
                    d2.append({"id": rid("d2", lab["expediente"], lab["file"], field, "absent"), "task": "d2_facto",
                               "prompt": D2_FACT.format(question=QUESTIONS[field], name=lab["file"], pages=n, text=text),
                               "answer": json.dumps({"valor": None, "pagina": None, "citacao": ""}, ensure_ascii=False), "expediente": lab["expediente"]})
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
