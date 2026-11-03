"""The scaffold's own tests (stdlib, no model):   python3 -I generator/test_guard.py

1. every key of the sealed D1/D2 sets and of the stranger test is inside the language (check() is None) — a key the
   scaffold refuses would be a key the reader can never give, i.e. a window or extraction defect, so it is listed;
2. every grammar is well-formed (each rule used is defined, root present) and the key is one of root's sentences in the
   simple cases the test can enumerate (D1 null branch; D2 null branch);
3. the known bad answers are refused: a fabricated quote with a real-looking number, a value on another page, an element id
   outside the shortlist, a citation that is not the law's text, a value outside the quote.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "generator"))
import guard  # noqa: E402

SETS = ["sealed/d1-test.jsonl", "sealed/d2-test.jsonl", "sealed/stranger-test.jsonl"]


def rows(path):
    return [json.loads(l) for l in open(ROOT / path, encoding="utf-8") if l.strip()]


def main():
    bad, n, sizes = [], 0, []
    for path in SETS:
        for r in rows(path):
            if r["task"] not in guard.TASKS:
                continue
            n += 1
            k = json.loads(r["answer"])
            if r["task"] == "d2_facto" and k["valor"]:
                k["citacao"] = k["valor"]  # a key's quote is a loose window (never scored); what the key fixes is the value on its page
            key = json.dumps(k, ensure_ascii=False)
            why = guard.check(r["task"], r["prompt"], key)
            if why:
                bad.append((path, r["id"], why, key[:120]))
            g = guard.grammar_for(r["task"], r["prompt"])
            assert guard.defined(g), (path, r["id"])
            sizes.append(len(g))
    print(f"keys checked {n}; outside the language {len(bad)}; grammar size min/median/max {min(sizes)}/{sorted(sizes)[len(sizes) // 2]}/{max(sizes)} chars")
    for b in bad:
        print("  REFUSED KEY", *b)

    # 3. known bad answers
    d1 = next(r for r in rows("sealed/stranger-test.jsonl") if r["task"] == "d1_elemento" and json.loads(r["answer"])["elemento"])
    d2 = next(r for r in rows("sealed/stranger-test.jsonl") if r["task"] == "d2_facto" and json.loads(r["answer"])["valor"])
    k1, k2 = json.loads(d1["answer"]), json.loads(d2["answer"])
    pages = guard.pages_of(d2["prompt"])
    cases = [
        ("d1 id outside the shortlist", "d1_elemento", d1["prompt"], json.dumps({"elemento": "portaria-320-2026-1:anexo-i-99", "citacao": "x", "tipo": "escrito"}, ensure_ascii=False)),
        ("d1 citation not the law text", "d1_elemento", d1["prompt"], json.dumps({"elemento": k1["elemento"], "citacao": k1["citacao"][:-1], "tipo": "escrito"}, ensure_ascii=False)),
        ("d1 keys out of order", "d1_elemento", d1["prompt"], json.dumps({"tipo": "escrito", "elemento": k1["elemento"], "citacao": k1["citacao"]}, ensure_ascii=False)),
        ("d1 element with tipo nao_e_elemento", "d1_elemento", d1["prompt"], json.dumps({"elemento": k1["elemento"], "citacao": k1["citacao"], "tipo": "nao_e_elemento"}, ensure_ascii=False)),
        ("d2 fabricated quote", "d2_facto", d2["prompt"], json.dumps({"valor": "1 888 000,00 €", "pagina": k2["pagina"], "citacao": "O valor total da obra é de 1 888 000,00 €."}, ensure_ascii=False)),
        ("d2 page not shown", "d2_facto", d2["prompt"], json.dumps({"valor": k2["valor"], "pagina": max(pages) + 1, "citacao": k2["valor"]}, ensure_ascii=False)),
        ("d2 value outside the quote", "d2_facto", d2["prompt"], json.dumps({"valor": k2["valor"], "pagina": k2["pagina"], "citacao": guard.pages_of(d2["prompt"])[k2["pagina"]].split(k2["valor"])[0].strip()}, ensure_ascii=False)),
        ("d2 null with a page", "d2_facto", d2["prompt"], json.dumps({"valor": None, "pagina": 1, "citacao": ""})),
        ("d2 value cut inside a token", "d2_facto", d2["prompt"], json.dumps({"valor": k2["valor"][1:], "pagina": k2["pagina"], "citacao": k2["valor"]}, ensure_ascii=False)),
    ]
    for name, task, prompt, text in cases:
        why = guard.check(task, prompt, text)
        assert why, f"accepted: {name}"
        print(f"  refused  {name}: {why}")
    for name, task, prompt, text in (("d1 key", "d1_elemento", d1["prompt"], json.dumps(k1, ensure_ascii=False)),
                                     ("d2 key", "d2_facto", d2["prompt"], json.dumps({**k2, "citacao": k2["valor"]}, ensure_ascii=False)),
                                     ("d1 null", "d1_elemento", d1["prompt"], guard.NONE_D1["nao_e_elemento"]), ("d2 null", "d2_facto", d2["prompt"], guard.NONE_D2)):
        assert guard.check(task, prompt, text) is None, name
    # the null sentences are literally in root
    assert guard._lit(guard.NONE_D2) in guard.grammar_d2(d2["prompt"]).splitlines()[0]
    # an illegible file admits one sentence
    ill = next(r for r in rows("sealed/d1-test.jsonl") if json.loads(r["answer"])["tipo"] == "ilegivel")
    assert guard.grammar_d1(ill["prompt"]) == f"root ::= {guard._lit(guard.NONE_D1['ilegivel'])}\n"
    assert guard.check("d1_elemento", ill["prompt"], guard.NONE_D1["nao_e_elemento"])
    print("ok" if not bad else f"{len(bad)} keys outside the language (see above)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
