"""D0 v3 — finding in the law, not reciting it: every question comes with candidate passages (id + text) in the prompt and the
reader selects one and copies its text verbatim, or abstains when the right one is not offered.

    python3 -I generator/d0.py            # -> training/data/d0/train.jsonl, sealed/d0-test.jsonl, generator/D0-REPORT.md

Tasks (field `task`):
  transcreve      "what does Annex V n.º 27 b) ii) say?"           candidates: the passage + its siblings
  localiza        "where does the law say «excerpt»?"               candidates: the passage + near passages
  alinea_de       "in n.º 27, which alínea asks for X?"             candidates: every alínea of that number
  elemento_doc    a Celorico CPEDI document -> its passage + how the law marks it
  exigencia       "does CP de obras de edificação require X, when?" (Annex V n.º 27 + common 5-17; negatives from other lists)
  proibido        "may the municipality demand X?"                  (RJUE art. 9.º n.º 12 vs Annex V elements)
Split by phrasing (the last phrasing of each task is sealed) + nao_sei probes (the right passage withheld) in both splits.
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
PORTARIA = "Portaria n.º 320/2026/1"
RJUE = "RJUE (DL n.º 555/99, republicado pelo DL n.º 108/2026)"
SYSTEM = ("És o leitor de saneamento de expedientes urbanísticos de um município português. Respondes só com o objeto JSON pedido, "
          "sem texto antes nem depois. Toda a citação é copiada letra a letra da lei; se não sabes, respondes {\"resposta\": \"nao_sei\"}.")
HEAD = ("Passagens da lei disponíveis (id — texto). Responde escolhendo uma delas: copia o id em «passagem» e o texto inteiro, letra a letra, em «citacao». "
        "Se nenhuma das passagens responde, responde {\"resposta\": \"nao_sei\"}.\n\n")


def load_passages(act):
    body = json.loads((ROOT / "structure" / f"{act}.json").read_text(encoding="utf-8"))
    return {p["id"]: p for p in body["passages"]}


def label_of(path):
    parts = path.split(".")
    if parts[0].startswith("anexo-"):
        out, rest = [f"Anexo {parts[0].split('-', 1)[1]}"], parts[1:]
    elif parts[0] == "anexo" and len(parts) > 1 and parts[1].startswith("art"):
        out, rest = [f"artigo {parts[1][3:]}.º"], parts[2:]
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
    return re.sub(r"^\s*(\d+\s*-\s*|[a-z]{1,4}\)\s*|[ivx]+\)\s*)", "", text).strip()


def excerpt(text, rng, words=7):
    toks = strip_label(text).split()
    if len(toks) <= words:
        return " ".join(toks)
    i = rng.randrange(0, len(toks) - words + 1)
    return " ".join(toks[i:i + words])


def block(cands):
    return HEAD + "\n".join(f"{p['id']} — {p['text']}" for p in cands) + "\n\n"


def row(task, prompt, answer, key, split):
    rid = hashlib.sha256(f"{task}|{key}|{prompt}".encode("utf-8")).hexdigest()[:16]
    return {"id": f"{task}:{rid}", "task": task, "prompt": prompt, "answer": json.dumps(answer, ensure_ascii=False), "passage": key, "split": split}


def main():
    rng = random.Random(SEED)
    port = load_passages("portaria-320-2026-1")
    rjue = load_passages("decreto-lei-108-2026")
    docs = json.loads((ROOT / "celorico" / "mapping" / "documents.json").read_text(encoding="utf-8"))["documents"]
    ajudas = [x for x in csv.DictReader(open(ROOT / "celorico" / "amostra" / "ajudas.csv", encoding="utf-8-sig")) if x["pedido"] == "CPEDI"]

    def leaf(p):
        return p["kind"] != "heading" and len(strip_label(p["text"])) >= 25
    pv = {k: v for k, v in port.items() if v["path"].startswith(("anexo-V.", "anexo-VI.", "anexo-VII.")) and leaf(v)}
    pr = {k: v for k, v in rjue.items() if re.match(r"anexo\.art(9|11|23)(\.|$)", v["path"]) and leaf(v)}
    allp = {**pv, **pr}
    order = list(allp)  # document order
    pos = {pid: i for i, pid in enumerate(order)}
    kids = defaultdict(list)
    for pid, p in allp.items():
        kids[p["parent"]].append(pid)

    def candidates(pid, k, withhold=False):
        """k candidate passages around pid (siblings first, then neighbours), shuffled; pid itself included unless withheld."""
        p = allp[pid]
        pool = [s for s in kids.get(p["parent"], []) if s != pid]
        i = pos[pid]
        near = [order[j] for j in range(max(0, i - 6), min(len(order), i + 7)) if order[j] != pid and order[j] not in pool]
        pool = pool + near
        rng.shuffle(pool)
        chosen = pool[:k - 1] if not withhold else pool[:k]
        if not withhold:
            chosen.append(pid)
        rng.shuffle(chosen)
        return [allp[c] for c in chosen]

    rows = []
    NS = {"resposta": "nao_sei"}
    # 1. transcreve
    T1 = ["Transcreve o texto de {act}, {label}.", "Qual é o texto exato de {act}, {label}?", "Cita, letra a letra, {act}, {label}.", "Que diz {act}, {label}? Dá o id da passagem e o seu texto."]
    for n, (pid, p) in enumerate(allp.items()):
        for i, tpl in enumerate(T1):
            split = "sealed" if i == len(T1) - 1 else "train"
            withhold = (n + i) % 9 == 0
            q = tpl.format(act=act_name(pid), label=label_of(p["path"]))
            rows.append(row("transcreve", block(candidates(pid, rng.randrange(5, 11), withhold)) + q, NS if withhold else {"passagem": pid, "citacao": p["text"]}, pid, split))
    # 2. localiza
    T2 = ["Onde diz a lei «{ex}»? Indica a passagem e transcreve-a por inteiro.", "Em que passagem de {act} aparece «{ex}»? Dá o id e o texto completo.",
          "A frase «{ex}» pertence a que passagem de {act}? Id e texto inteiro."]
    for n, (pid, p) in enumerate(allp.items()):
        for i, tpl in enumerate(T2):
            ex = excerpt(p["text"], rng)
            if len(ex.split()) < 4:
                continue
            split = "sealed" if i == len(T2) - 1 else "train"
            withhold = (n + i) % 11 == 0
            rows.append(row("localiza", block(candidates(pid, rng.randrange(5, 11), withhold)) + tpl.format(ex=ex, act=act_name(pid)), NS if withhold else {"passagem": pid, "citacao": p["text"]}, pid, split))
    # 3. elemento_doc
    ajuda_by_doc = {x["documento"]: x for x in ajudas if x["documento"]}
    T3 = ["No pedido CPEDI (comunicação prévia de obras de edificação) da instalação NoPaper de Celorico de Basto, o documento «{code} — {label}» assenta em que passagem da lei? Como a marca a lei?",
          "Celorico de Basto, pedido CPEDI: a que elemento de {act} corresponde o documento «{label}» ({code}), e é obrigatório, condicional ou facultativo?",
          "O formulário CPEDI de Celorico de Basto tem o campo «{label}» (código {code}). Qual é a passagem de {act} que o sustenta, com o texto, e qual o seu tipo?"]
    for d in docs:
        if "CP/CPEDI" not in d["requests"] or not d["passages"]:
            continue
        pid = f"portaria-320-2026-1:{d['passages'][0]}"
        if pid not in allp:
            continue
        a = ajuda_by_doc.get(d["code"])
        ans = {"passagem": pid, "citacao": allp[pid]["text"], "tipo": a["tipo"] if a else "previsto", "base_legal": a["base_legal"] if a else f"{PORTARIA}, {label_of(d['passages'][0])}"}
        for i, tpl in enumerate(T3):
            rows.append(row("elemento_doc", block(candidates(pid, rng.randrange(6, 12))) + tpl.format(code=d["code"], label=d["label"], act=PORTARIA), ans, pid, "sealed" if i == 2 else "train"))
    # 4. exigencia (CPEDI lists; negatives from other lists)
    cpedi_lists = ["anexo-V.27"] + [f"anexo-V.{n}" for n in range(5, 18)]
    cond_words = re.compile(r"\b(quando|caso|se |sempre que|nos casos|desde que|salvo|exceto|aplicando-se)\b", re.I)
    T4 = ["A comunicação prévia de obras de edificação exige «{ex}»? Responde se é exigido sempre, só em certa condição, ou não, e cita a passagem.",
          "Num pedido CPEDI em Celorico de Basto, é obrigatório entregar «{ex}»? Em que condição?",
          "Para uma comunicação prévia de obras de edificação, «{ex}» entra sempre, só às vezes, ou nunca? Diz a condição e a passagem."]
    in_cpedi = lambda p: any(p["path"] == l or p["path"].startswith(l + ".") for l in cpedi_lists)  # noqa: E731
    for pid, p in pv.items():
        if not in_cpedi(p):
            continue
        txt = strip_label(p["text"]); m = cond_words.search(txt)
        exig, cond = ("condicional", txt[m.start():].rstrip(";:.")) if m else ("sempre", "")
        for i, tpl in enumerate(T4):
            rows.append(row("exigencia", block(candidates(pid, rng.randrange(5, 10))) + tpl.format(ex=excerpt(p["text"], rng, 9)), {"exigido": exig, "condicao": cond, "passagem": pid, "citacao": p["text"]}, pid, "sealed" if i == 2 else "train"))
    others = [p for p in pv.values() if p["path"].startswith("anexo-V.") and not in_cpedi(p) and re.match(r"anexo-V\.(1|2|3|4|18|19|2\d|3[0-4])(\.|$)", p["path"])]
    for j, p in enumerate(rng.sample(others, min(90, len(others)))):
        rows.append(row("exigencia", block(candidates(p["id"], rng.randrange(5, 10))) + T4[j % 3].format(ex=excerpt(p["text"], rng, 9)),
                        {"exigido": "nao", "condicao": "", "passagem": p["id"], "citacao": p["text"], "nota": "elemento de outra lista do Anexo V, não da comunicação prévia de obras de edificação"}, p["id"], "sealed" if j % 3 == 2 else "train"))
    # 5. proibido
    T5 = ["Pode um município exigir, como elemento instrutório, «{ex}»? Cita a passagem que decide.", "É lícito pedir ao requerente «{ex}»? Responde sim ou não com a passagem.",
          "Um município pode pedir «{ex}» num procedimento urbanístico? Sim ou não, e a passagem."]
    proib = [p for p in pr.values() if re.match(r"anexo\.art9\.12\.[a-z]", p["path"])]
    for p in proib:
        for i, tpl in enumerate(T5):
            rows.append(row("proibido", block(candidates(p["id"], rng.randrange(5, 10))) + tpl.format(ex=excerpt(p["text"], rng, 8)), {"resposta": "nao", "passagem": p["id"], "citacao": p["text"]}, p["id"], "sealed" if i == 2 else "train"))
    for j, p in enumerate(rng.sample([p for p in pv.values() if p["path"].startswith("anexo-V.27.")], 24)):
        rows.append(row("proibido", block(candidates(p["id"], rng.randrange(5, 10))) + T5[j % 3].format(ex=excerpt(p["text"], rng, 8)), {"resposta": "sim", "passagem": p["id"], "citacao": p["text"]}, p["id"], "sealed" if j % 3 == 2 else "train"))
    # 6. alinea_de (all alíneas of the number as candidates)
    for parent, ps in kids.items():
        sibs = [allp[s] for s in ps if re.match(r"anexo-V\.\d+\.[a-z]+$", allp[s]["path"])]
        if len(sibs) < 3:
            continue
        for p in sibs:
            cands = list(sibs); rng.shuffle(cands)
            rows.append(row("alinea_de", block(cands) + f"No {label_of(port[parent]['path'])} de {PORTARIA}, que alínea pede «{excerpt(p['text'], rng, 7)}»? Dá o id e o texto.", {"passagem": p["id"], "citacao": p["text"]}, p["id"], "train"))
            rows.append(row("alinea_de", block(cands) + f"Dentro do {label_of(port[parent]['path'])} ({PORTARIA}), a alínea que trata de «{excerpt(p['text'], rng, 7)}» é qual? Id e texto.", {"passagem": p["id"], "citacao": p["text"]}, p["id"], "sealed"))

    train = [r for r in rows if r["split"] == "train"]; test = [r for r in rows if r["split"] == "sealed"]
    seen = set(); train = [r for r in train if not (r["id"] in seen or seen.add(r["id"]))]
    OUT.mkdir(parents=True, exist_ok=True); SEALED.mkdir(exist_ok=True)
    for path, rs in ((OUT / "train.jsonl", train), (SEALED / "d0-test.jsonl", test)):
        with open(path, "w", encoding="utf-8") as f:
            for r in rs:
                f.write(json.dumps({k: r[k] for k in ("id", "task", "prompt", "answer")}, ensure_ascii=False) + "\n")
    (OUT / "SYSTEM.txt").write_text(SYSTEM + "\n", encoding="utf-8")
    ct, cs = Counter(r["task"] for r in train), Counter(r["task"] for r in test)
    rep = ["# D0 report (v3: candidates in the prompt)", "", f"seed {SEED}; passages {len(allp)}; prompt chars p95 {sorted(len(r['prompt']) for r in train)[int(len(train) * 0.95)]}", "",
           "| task | train | sealed |", "|---|---|---|"] + [f"| {t} | {ct[t]} | {cs[t]} |" for t in sorted(set(ct) | set(cs))] + \
          ["", f"total train {len(train)}, sealed {len(test)}; nao_sei (passage withheld): train {sum('nao_sei' in r['answer'] for r in train)}, sealed {sum('nao_sei' in r['answer'] for r in test)}."]
    (ROOT / "generator" / "D0-REPORT.md").write_text("\n".join(rep) + "\n", encoding="utf-8")
    print("\n".join(rep))


if __name__ == "__main__":
    main()
