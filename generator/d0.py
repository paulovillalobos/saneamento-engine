"""D0 — the vocabulary of the law, as question/answer rows for the reader, written by code from the law files and nothing else.

    python3 -I generator/d0.py            # -> training/data/d0/train.jsonl, sealed/d0-test.jsonl, generator/D0-REPORT.md

Every answer is a JSON object whose quotes are passages of the structured acts (structure/*.json), copied verbatim; nothing is
paraphrased, nothing comes from a model. Tasks (field `task`):
  transcreve      the id of a passage -> its text                          (Annex V, VI, VII; RJUE arts 9, 11, 23)
  localiza        an excerpt of a passage -> its id and full text           (reverse lookup)
  elemento_doc    a Celorico CPEDI document (code + label) -> the passage it rests on, its text, and how the law marks it
  exigencia       "does CP de obras de edificação require X, and when?"    (from Annex V n.º 27 + common elements 5-17)
  proibido        "may the municipality demand X?"                         (RJUE art. 9.º n.º 12 list vs. Annex V elements)
  alinea_de       "in Annex V n.º N, which alínea asks for X?"             (sibling disambiguation)
The sealed test takes whole passages out of training (never the same passage in both), by seed.
"""
import csv
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "training" / "data" / "d0"
SEALED = ROOT / "sealed"
SEED = 20261027
HOLD_FRACTION = 0.10
PORTARIA = "Portaria n.º 320/2026/1"
RJUE = "RJUE (DL n.º 555/99, republicado pelo DL n.º 108/2026)"

SYSTEM = ("És o leitor de saneamento de expedientes urbanísticos de um município português. Respondes só com o objeto JSON pedido, "
          "sem texto antes nem depois. Toda a citação é copiada letra a letra da lei; se não sabes, respondes {\"resposta\": \"nao_sei\"}.")


def load_passages(act):
    body = json.loads((ROOT / "structure" / f"{act}.json").read_text(encoding="utf-8"))
    return {p["id"]: p for p in body["passages"]}


def label_of(path):
    """anexo-V.27.b.ii -> 'Anexo V, n.º 27, alínea b), subalínea ii)'; anexo.art9.12.a -> 'artigo 9.º, n.º 12, alínea a)'."""
    parts = path.split(".")
    if parts[0].startswith("anexo-"):
        out = [f"Anexo {parts[0].split('-', 1)[1]}"]
        rest = parts[1:]
    elif parts[0] == "anexo" and len(parts) > 1 and parts[1].startswith("art"):
        out = [f"artigo {parts[1][3:]}.º"]
        rest = parts[2:]
    else:
        return path
    names = ["n.º {}", "alínea {})", "subalínea {})", "ponto {}"]
    for i, r in enumerate(rest):
        if r.startswith("sec-"):
            out.append(f"secção {r[4:]}")
        elif r.startswith("p") and r[1:].isdigit():
            out.append(f"parágrafo {r[1:]}")
        elif r == "heading":
            out.append("epígrafe")
        else:
            out.append(names[min(i, 3)].format(r))
    return ", ".join(out)


def act_name(pid):
    return PORTARIA if pid.startswith("portaria-320") else RJUE


def strip_label(text):
    """'b) Projeto de arquitetura, incluindo:' -> 'Projeto de arquitetura, incluindo:' (the label is in the id already)."""
    return re.sub(r"^\s*(\d+\s*-\s*|[a-z]{1,4}\)\s*|[ivx]+\)\s*)", "", text).strip()


def excerpt(text, rng, words=7):
    toks = strip_label(text).split()
    if len(toks) <= words:
        return " ".join(toks)
    i = rng.randrange(0, len(toks) - words + 1)
    return " ".join(toks[i:i + words])


def row(task, prompt, answer, key):
    rid = hashlib.sha256(f"{task}|{key}|{prompt}".encode("utf-8")).hexdigest()[:16]
    return {"id": f"{task}:{rid}", "task": task, "prompt": prompt, "answer": json.dumps(answer, ensure_ascii=False), "passage": key}


def main():
    rng = random.Random(SEED)
    port = load_passages("portaria-320-2026-1")
    rjue = load_passages("decreto-lei-108-2026")
    law = json.loads((ROOT / "law" / "portaria-320-2026-1.json").read_text(encoding="utf-8"))
    docs = json.loads((ROOT / "celorico" / "mapping" / "documents.json").read_text(encoding="utf-8"))["documents"]
    ajudas = [x for x in csv.DictReader(open(ROOT / "celorico" / "amostra" / "ajudas.csv", encoding="utf-8-sig")) if x["pedido"] == "CPEDI"]

    # ---- the passages D0 covers: Annex V (all), VI, VII of the Portaria; RJUE arts 9 (n.º 12), 11, 23 ----
    def leaf(p):  # a passage with its own normative text (not a bare heading)
        return p["kind"] not in ("heading",) and len(strip_label(p["text"])) >= 25
    pv = {k: v for k, v in port.items() if v["path"].startswith(("anexo-V.", "anexo-VI.", "anexo-VII.")) and leaf(v)}
    pr = {k: v for k, v in rjue.items() if re.match(r"anexo\.art(9|11|23)(\.|$)", v["path"]) and leaf(v)}
    allp = {**pv, **pr}
    print(f"passages: Portaria V/VI/VII {len(pv)}, RJUE 9/11/23 {len(pr)}")

    rows = []
    # 1. transcreve (3 phrasings)
    T1 = ["Transcreve o texto de {act}, {label}.", "Qual é o texto exato de {act}, {label}?", "Cita, letra a letra, {act}, {label}."]
    for pid, p in allp.items():
        for tpl in T1:
            rows.append(row("transcreve", tpl.format(act=act_name(pid), label=label_of(p["path"])),
                            {"passagem": pid, "citacao": p["text"]}, pid))
    # 2. localiza (2 excerpts per passage)
    T2 = ["Onde diz a lei «{ex}»? Indica a passagem e transcreve-a por inteiro.", "Em que passagem de {act} aparece «{ex}»? Dá o id e o texto completo."]
    for pid, p in allp.items():
        for tpl in T2:
            ex = excerpt(p["text"], rng)
            if len(ex.split()) < 4:
                continue
            rows.append(row("localiza", tpl.format(ex=ex, act=act_name(pid)), {"passagem": pid, "citacao": p["text"]}, pid))
    # 3. elemento_doc — Celorico CPEDI documents -> passage + how the law marks them
    ajuda_by_doc = {x["documento"]: x for x in ajudas if x["documento"]}
    T3 = ["No pedido CPEDI (comunicação prévia de obras de edificação) da instalação NoPaper de Celorico de Basto, o documento «{code} — {label}» assenta em que passagem da lei? Como a marca a lei?",
          "Celorico de Basto, pedido CPEDI: a que elemento de {act} corresponde o documento «{label}» ({code}), e é obrigatório, condicional ou facultativo?"]
    n3 = 0
    for d in docs:
        if "CP/CPEDI" not in d["requests"] or not d["passages"]:
            continue
        pid = f"portaria-320-2026-1:{d['passages'][0]}"
        if pid not in port:
            continue
        a = ajuda_by_doc.get(d["code"])
        tipo = a["tipo"] if a else "previsto"
        ans = {"passagem": pid, "citacao": port[pid]["text"], "tipo": tipo, "base_legal": a["base_legal"] if a else f"{PORTARIA}, {label_of(d['passages'][0])}"}
        for tpl in T3:
            rows.append(row("elemento_doc", tpl.format(code=d["code"], label=d["label"], act=PORTARIA), ans, pid)); n3 += 1
    # 4. exigencia — Annex V n.º 27 alíneas + common elements 5-17 for CPEDI
    cpedi_lists = ["anexo-V.27"] + [f"anexo-V.{n}" for n in range(5, 18)]
    cond_words = re.compile(r"\b(quando|caso|se |sempre que|nos casos|desde que|salvo|exceto|aplicando-se)\b", re.I)
    T4 = ["A comunicação prévia de obras de edificação exige «{ex}»? Responde se é exigido sempre, só em certa condição, ou não, e cita a passagem.",
          "Num pedido CPEDI em Celorico de Basto, é obrigatório entregar «{ex}»? Em que condição?"]
    n4 = 0
    for pid, p in pv.items():
        if not any(p["path"] == l or p["path"].startswith(l + ".") for l in cpedi_lists):
            continue
        txt = strip_label(p["text"])
        m = cond_words.search(txt)
        if m:
            exig, cond = "condicional", txt[m.start():].rstrip(";:.")
        else:
            exig, cond = "sempre", ""
        for tpl in T4:
            rows.append(row("exigencia", tpl.format(ex=excerpt(p["text"], rng, 9)), {"exigido": exig, "condicao": cond, "passagem": pid, "citacao": p["text"]}, pid)); n4 += 1
    # negatives for exigencia: elements of other lists (loteamento, PIP, utilização) that CPEDI does not require
    others = [p for k, p in pv.items() if p["path"].startswith("anexo-V.") and not any(p["path"] == l or p["path"].startswith(l + ".") for l in cpedi_lists)
              and re.match(r"anexo-V\.(1|2|3|4|18|19|20|21|22|23|24|25|26|28|29|30|31|32|33|34)(\.|$)", p["path"])]
    for p in rng.sample(others, min(60, len(others))):
        pid = p["id"]
        rows.append(row("exigencia", T4[0].format(ex=excerpt(p["text"], rng, 9)), {"exigido": "nao", "condicao": "", "passagem": pid, "citacao": p["text"], "nota": "elemento de outra lista do Anexo V, não da comunicação prévia de obras de edificação"}, pid)); n4 += 1
    # 5. proibido — RJUE art. 9.º n.º 12
    T5 = ["Pode um município exigir, como elemento instrutório, «{ex}»? Cita a passagem que decide.", "É lícito pedir ao requerente «{ex}»? Responde sim ou não com a passagem."]
    proib = [p for k, p in pr.items() if re.match(r"anexo\.art9\.12\.[a-z]", p["path"])]
    n5 = 0
    for p in proib:
        for tpl in T5:
            rows.append(row("proibido", tpl.format(ex=excerpt(p["text"], rng, 8)), {"resposta": "nao", "passagem": p["id"], "citacao": p["text"]}, p["id"])); n5 += 1
    for p in rng.sample([p for p in pv.values() if p["path"].startswith("anexo-V.27.")], 12):
        rows.append(row("proibido", T5[0].format(ex=excerpt(p["text"], rng, 8)), {"resposta": "sim", "passagem": p["id"], "citacao": p["text"]}, p["id"])); n5 += 1
    # 6. alinea_de — sibling disambiguation inside a number
    kids = defaultdict(list)
    for pid, p in pv.items():
        if p["path"].startswith("anexo-V.") and re.match(r"anexo-V\.\d+\.[a-z]+$", p["path"]):
            kids[p["parent"]].append(p)
    n6 = 0
    for parent, ps in kids.items():
        if len(ps) < 3:
            continue
        for p in ps:
            rows.append(row("alinea_de", f"No {label_of(port[parent]['path'])} de {PORTARIA}, que alínea pede «{excerpt(p['text'], rng, 7)}»? Dá o id e o texto.",
                            {"passagem": p["id"], "citacao": p["text"]}, p["id"])); n6 += 1

    # ---- sealed split by passage ----
    keys = sorted({r["passage"] for r in rows})
    held = set(rng.sample(keys, int(len(keys) * HOLD_FRACTION)))
    train = [r for r in rows if r["passage"] not in held]
    test = [r for r in rows if r["passage"] in held]
    seen = set(); train = [r for r in train if not (r["id"] in seen or seen.add(r["id"]))]
    OUT.mkdir(parents=True, exist_ok=True); SEALED.mkdir(exist_ok=True)
    with open(OUT / "train.jsonl", "w", encoding="utf-8") as f:
        for r in train:
            f.write(json.dumps({k: r[k] for k in ("id", "task", "prompt", "answer")}, ensure_ascii=False) + "\n")
    with open(SEALED / "d0-test.jsonl", "w", encoding="utf-8") as f:
        for r in test:
            f.write(json.dumps({k: r[k] for k in ("id", "task", "prompt", "answer")}, ensure_ascii=False) + "\n")
    (OUT / "SYSTEM.txt").write_text(SYSTEM + "\n", encoding="utf-8")
    ct, cs = Counter(r["task"] for r in train), Counter(r["task"] for r in test)
    rep = ["# D0 report", "", f"seed {SEED}; passages covered {len(keys)}; held-out passages {len(held)} ({HOLD_FRACTION:.0%})", "",
           "| task | train | sealed |", "|---|---|---|"] + [f"| {t} | {ct[t]} | {cs[t]} |" for t in sorted(set(ct) | set(cs))] + \
          ["", f"total train {len(train)}, sealed {len(test)}; every `citacao` is a verbatim passage of structure/*.json (checked by generator/check_d0.py)."]
    (ROOT / "generator" / "D0-REPORT.md").write_text("\n".join(rep) + "\n", encoding="utf-8")
    print("\n".join(rep))


if __name__ == "__main__":
    main()
