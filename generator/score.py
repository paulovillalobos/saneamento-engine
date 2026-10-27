"""Score a reader run against the keys: per task, exact fields, verbatim quotes, invented answers, abstentions.

    python3 -I generator/score.py --rows sealed/d0-test.jsonl --answers training/runs/base/d0.json [--record training/runs/base/SCORES.md]

Metrics (all as count/total):
  D0  passagem exact; citacao verbatim (== the passage text); both.
  D1  elemento exact (null == null); tipo exact; citacao verbatim when an element is named; invented = element named when key is null.
  D2  valor exact (string equality after whitespace collapse; null == null); pagina exact; citacao contains the value;
      invented = non-null valor when the key is null; missed = null valor when the key has one.
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def norm(s):
    return re.sub(r"\s+", " ", s or "").strip()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--rows", required=True); ap.add_argument("--answers", required=True); ap.add_argument("--record", default="")
    a = ap.parse_args()
    keys = {r["id"]: r for r in (json.loads(l) for l in open(ROOT / a.rows, encoding="utf-8") if l.strip())}
    res = json.load(open(ROOT / a.answers, encoding="utf-8"))
    meta, outs = res[0]["meta"], res[1:]
    m = defaultdict(lambda: defaultdict(int))
    for o in outs:
        r = keys.get(o["key"])
        if not r:
            continue
        t = r["task"]; k = json.loads(r["answer"]); c = m[t]; c["n"] += 1
        if o.get("skipped") or not o.get("text"):
            c["skipped"] += 1; continue
        try:
            p = json.loads(o["text"])
        except json.JSONDecodeError:
            c["malformed"] += 1; continue
        if k.get("resposta") == "nao_sei":
            c["probes"] += 1; c["absteve"] += p.get("resposta") == "nao_sei"; c["inventado"] += p.get("resposta") != "nao_sei"; c["n"] -= 1; continue
        if t in ("transcreve", "localiza", "alinea_de", "elemento_doc", "exigencia", "proibido"):
            c["passagem"] += p.get("passagem") == k.get("passagem")
            c["citacao"] += norm(p.get("citacao")) == norm(k.get("citacao"))
            c["ambos"] += (p.get("passagem") == k.get("passagem") and norm(p.get("citacao")) == norm(k.get("citacao")))
            for f in ("tipo", "exigido", "resposta"):
                if f in k:
                    c[f] += p.get(f) == k[f]; c[f + "_n"] += 1
            c["nao_sei"] += p.get("resposta") == "nao_sei"
        elif t == "d1_elemento":
            c["elemento"] += p.get("elemento") == k["elemento"]
            c["tipo"] += p.get("tipo") == k["tipo"]
            if k["elemento"]:
                c["com_elemento"] += 1; c["citacao"] += norm(p.get("citacao")) == norm(k["citacao"])
            else:
                c["sem_elemento"] += 1; c["inventado"] += bool(p.get("elemento"))
        elif t == "d2_facto":
            if k["valor"] is None:
                c["nulos"] += 1; c["inventado"] += p.get("valor") is not None; c["valor"] += p.get("valor") is None
            else:
                c["com_valor"] += 1; c["perdido"] += p.get("valor") is None
                c["valor"] += norm(p.get("valor")) == norm(k["valor"])
                c["pagina"] += p.get("pagina") == k["pagina"]
                c["valor_e_pagina"] += (norm(p.get("valor")) == norm(k["valor"]) and p.get("pagina") == k["pagina"])
                c["citacao_contem"] += bool(p.get("citacao")) and norm(k["valor"]) in norm(p.get("citacao"))
    lines = [f"# {a.answers}", "", f"model {meta.get('model')} adapter {meta.get('adapter')} answered {meta.get('answered')} skipped {meta.get('skipped')} "
             f"load {meta.get('load_seconds')}s gen {meta.get('generate_seconds')}s", ""]
    for t, c in sorted(m.items()):
        n = c["n"]
        parts = [f"**{t}** n={n}"]
        for f in ("passagem", "citacao", "ambos", "elemento", "tipo", "exigido", "resposta", "valor", "pagina", "valor_e_pagina", "citacao_contem"):
            if f in c:
                den = n if f not in ("citacao",) or t != "d1_elemento" else c["com_elemento"]
                if f in ("tipo", "exigido", "resposta") and c.get(f + "_n"):
                    den = c[f + "_n"]
                if f in ("pagina", "valor_e_pagina", "citacao_contem") and t == "d2_facto":
                    den = c["com_valor"]
                parts.append(f"{f} {c[f]}/{den} ({100 * c[f] / den:.0f}%)" if den else f"{f} -")
        for f in ("inventado", "perdido", "malformed", "skipped", "nao_sei"):
            if c.get(f):
                parts.append(f"{f} {c[f]}")
        if c.get("probes"):
            parts.append(f"probes nao_sei {c['absteve']}/{c['probes']}")
        lines.append("- " + "; ".join(parts))
    text = "\n".join(lines)
    print(text)
    if a.record:
        Path(ROOT / a.record).parent.mkdir(parents=True, exist_ok=True)
        with open(ROOT / a.record, "a", encoding="utf-8") as f:
            f.write(text + "\n\n")


if __name__ == "__main__":
    main()
