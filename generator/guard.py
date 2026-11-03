"""The hard scaffold (DECISIONS D13): the reader can only answer with what the prompt itself holds.

    grammar_for(task, prompt) -> str               an xgrammar EBNF grammar for one D1 or D2 prompt (vLLM: StructuredOutputsParams(grammar=…))
    check(task, prompt, text) -> None | str        the same language plus the product rule, in plain Python: None = accepted, else why not
    python3 -I generator/guard.py --rows sealed/stranger-test.jsonl --answers training/runs/r8/stranger-v3.json --out …-guard.json
                                                   the checker over a finished run: every answer outside the language is marked
                                                   "guard": <why> and the scorer counts it as wrong (never as an abstention)

D1 (which element is this file): the answer is one of 1 + 2·|shortlist| sentences. Either {"elemento":null,"citacao":"","tipo":
"nao_e_elemento"|"ilegivel"}, or {"elemento":"<an id printed in the prompt's shortlist>","citacao":"<that line's law text, letter
by letter>","tipo":"escrito"|"desenhado"}. The element id cannot be outside the shortlist and the citation cannot be anything but
the law's own words for that id. A prompt without pages (the file is not a PDF) admits the one sentence {null,"","ilegivel"}.

D2 (a fact with its page): either {"valor":null,"pagina":null,"citacao":""}, or, for one page p shown in the prompt,
{"valor":"<a token-aligned piece of page p>","pagina":p,"citacao":"<a token-aligned piece of page p>"}. Tokens are maximal runs
of word characters and each other non-space character on its own; what lies between two tokens is the page's own text. So a value
or a quote that is not written on the page it names is not in the language. The product rule the grammar cannot say, check()
adds: the value must be inside the quote. An answer the checker refuses is not an abstention: the file goes to the técnico as
not read, and the scorer counts it as wrong.

What the scaffold does not do: it cannot stop a wrong choice among real options (a real number that answers another
question, a real element id for a file that is not that element). Those stay measured by the keys.

The sentences use the trained spacing (json.dumps default: «, » and «: »), as every training answer was written. Page text
and answer strings are compared after collapse() (whitespace runs as one space).

The grammar is built from the prompt alone (the shortlist lines and the «[página n]» blocks between the «---» fences), so what
the decoder may write is exactly what the model was shown; the generator's files are not read. Stdlib only.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKEN = re.compile(r"\d+|[^\W\d]+|[^\w\s]")  # digits, letters and each other mark apart: «1.900,00m2» holds the piece «1.900,00»
ILLEGIBLE = "(ficheiro ilegível: não é um PDF)"
NONE_D1 = {"nao_e_elemento": '{"elemento": null, "citacao": "", "tipo": "nao_e_elemento"}', "ilegivel": '{"elemento": null, "citacao": "", "tipo": "ilegivel"}'}
NONE_D2 = '{"valor": null, "pagina": null, "citacao": ""}'
WS = re.compile(r"\s+")
TASKS = ("d1_elemento", "d2_facto")


# ---- the prompt ---------------------------------------------------------------------------------------------------------
def body_of(prompt):
    """The file text between the fences: after «Ficheiro: … (n página(s))\\n---\\n», up to the final «\\n---»."""
    m = re.search(r"\nFicheiro: .*? \(\d+ página\(s\)\)\n---\n", prompt)
    if not m or not prompt.endswith("\n---"):
        raise ValueError("the prompt has no «Ficheiro: … ---» fences")
    return prompt[m.end():-4]


def collapse(s):
    """Runs of whitespace (line breaks, non-breaking spaces) as one space, ends trimmed: the reader's own quotes never carry a
    line break (round 8: 0 of 1 198), the keys are written the same way, so the language is defined on the collapsed page."""
    return WS.sub(" ", s or "").strip()


def pages_of(prompt):
    """{page number: collapsed text as shown}, in the prompt's order; {} when the file is not a PDF. A page cut by the window keeps what
    was shown (a partial marker stays as text of the page before it, which is what the model saw)."""
    body = body_of(prompt)
    if body == ILLEGIBLE:
        return {}
    parts = re.split(r"(?m)^\[página (\d+)\]\n?", body)
    if parts[0].strip():
        raise ValueError("file text before the first «[página n]» marker")
    pages = {}
    for num, text in zip(parts[1::2], parts[2::2]):
        if int(num) in pages:
            raise ValueError(f"page {num} twice")
        pages[int(num)] = collapse(text)
    return pages


def shortlist_of(prompt):
    """[(id, law text)] of the lines «<id> — <text>» printed in a D1 prompt, in order."""
    out = [(m.group(1), m.group(2)) for m in re.finditer(r"(?m)^(portaria-\S+) — (.+)$", prompt.split("\n\nLê o texto do ficheiro")[0])]
    if not out:
        raise ValueError("no shortlist lines in the prompt")
    return out


# ---- the text -----------------------------------------------------------------------------------------------------------
def tokens(text):
    return [m.span() for m in TOKEN.finditer(text or "")]


def aligned(text, piece):
    """True when piece is text[a:b] with a a token's start and b a token's end."""
    if not piece or not text:
        return False
    sp = tokens(text)
    starts, ends = {a for a, _ in sp}, {b for _, b in sp}
    k = text.find(piece)
    while k >= 0:
        if k in starts and k + len(piece) in ends:
            return True
        k = text.find(piece, k + 1)
    return False


# ---- the grammar --------------------------------------------------------------------------------------------------------
def _ebnf(raw):
    """An EBNF string literal matching raw: backslash and double quote escaped, control characters as \\u escapes."""
    out = []
    for c in raw:
        if c in '"\\':
            out.append("\\" + c)
        elif ord(c) < 0x20 or 0x7f <= ord(c) <= 0x9f:
            out.append(f"\\u{ord(c):04x}")
        else:
            out.append(c)
    return '"' + "".join(out) + '"'


def _escaped(text):
    """text as json.dumps(ensure_ascii=False) writes it inside the quotes."""
    return json.dumps(text, ensure_ascii=False)[1:-1]


def _lit(raw):
    return _ebnf(raw)


def _page_rules(k, text):
    """texto<k> ::= t<k>_0 | …; t<k>_i ::= tok_i (sep_i t<k>_i+1)?: the token-aligned pieces of text. [] when text has no token."""
    sp = tokens(text)
    if not sp:
        return []
    names = [f"t{k}_{i}" for i in range(len(sp))]
    rules = []
    for i, (a, b) in enumerate(sp):
        tok = _ebnf(_escaped(text[a:b]))
        if i + 1 == len(sp):
            body = tok
        else:
            sep = text[b:sp[i + 1][0]]
            body = f"{tok} ({_ebnf(_escaped(sep))} {names[i + 1]})?" if sep else f"{tok} {names[i + 1]}?"
        rules.append(f"{names[i]} ::= {body}")
    return [f"texto{k} ::= " + " | ".join(names)] + rules


def grammar_d1(prompt):
    if not pages_of(prompt):
        return f"root ::= {_lit(NONE_D1['ilegivel'])}\n"
    alts = [_lit('{"elemento": null, "citacao": "", "tipo": ') + ' tipo_none ' + _lit("}")]
    for eid, law in shortlist_of(prompt):
        head = '{"elemento": ' + json.dumps(eid, ensure_ascii=False) + ', "citacao": ' + json.dumps(law, ensure_ascii=False) + ', "tipo": '
        alts.append(_lit(head) + " tipo_peca " + _lit("}"))
    return ("root ::= " + " | ".join(alts) + "\n"
            "tipo_none ::= " + _lit('"nao_e_elemento"') + " | " + _lit('"ilegivel"') + "\n"
            "tipo_peca ::= " + _lit('"escrito"') + " | " + _lit('"desenhado"') + "\n")


def grammar_d2(prompt):
    pages = pages_of(prompt)
    alts, rules = [_lit(NONE_D2)], []
    for k, (p, text) in enumerate(sorted(pages.items())):
        pr = _page_rules(k, text)
        if not pr:
            continue
        rules += pr
        alts.append(_lit('{"valor": "') + f" texto{k} " + _lit(f'", "pagina": {p}, "citacao": "') + f" texto{k} " + _lit('"}'))
    return "root ::= " + " | ".join(alts) + "\n" + "".join(r + "\n" for r in rules)


def grammar_for(task, prompt):
    if task == "d1_elemento":
        return grammar_d1(prompt)
    if task == "d2_facto":
        return grammar_d2(prompt)
    raise ValueError(f"no grammar for task {task}")


def defined(grammar):
    """Every rule name used on a right-hand side is defined (a syntax check of what grammar_for writes)."""
    names, used = set(), set()
    for line in grammar.splitlines():
        name, body = line.split(" ::= ", 1)
        names.add(name)
        used |= set(re.findall(r'(?<!["\\])\b(t\d+_\d+|texto\d+|tipo_\w+)\b(?!")', re.sub(r'"(?:[^"\\]|\\.)*"', "", body)))
    return used <= names and "root" in names


# ---- the same language in Python, plus the product rule -------------------------------------------------------------------
def _parse(text, keys):
    try:
        pairs = json.loads(text, object_pairs_hook=lambda ps: ps)
    except (json.JSONDecodeError, TypeError):
        return None, "não é JSON"
    if not isinstance(pairs, list) or [k for k, _ in pairs] != keys:
        return None, f"as chaves não são {keys}"
    return dict(pairs), None


def check(task, prompt, text):
    """None when text is in the language of grammar_for(task, prompt) and keeps the product rule; else why not."""
    if task == "d1_elemento":
        a, why = _parse(text, ["elemento", "citacao", "tipo"])
        if why:
            return why
        pages = pages_of(prompt)
        if a["elemento"] is None:
            if a["citacao"] != "":
                return "citação sem elemento"
            if not pages:
                return "ficheiro ilegível: só «ilegivel»" if a["tipo"] != "ilegivel" else None
            return None if a["tipo"] in ("nao_e_elemento", "ilegivel") else f"tipo {a['tipo']!r} sem elemento"
        if not pages:
            return "ficheiro ilegível: elemento tem de ser null"
        law = dict(shortlist_of(prompt)).get(a["elemento"])
        if law is None:
            return f"elemento {a['elemento']!r} não está na lista"
        if a["citacao"] != law:
            return "citação não é o texto da lei para esse elemento"
        return None if a["tipo"] in ("escrito", "desenhado") else f"tipo {a['tipo']!r} com elemento"
    if task == "d2_facto":
        a, why = _parse(text, ["valor", "pagina", "citacao"])
        if why:
            return why
        if a["valor"] is None:
            return None if a["pagina"] is None and a["citacao"] == "" else "valor null com página ou citação"
        if not isinstance(a["valor"], str) or not isinstance(a["citacao"], str):
            return "valor e citação têm de ser texto"
        pages = pages_of(prompt)
        if not isinstance(a["pagina"], int) or isinstance(a["pagina"], bool) or a["pagina"] not in pages:
            return f"página {a['pagina']!r} não foi mostrada"
        page, cit, val = pages[a["pagina"]], collapse(a["citacao"]), collapse(a["valor"])
        if not aligned(page, cit):
            return f"citação não está na página {a['pagina']}"
        if not aligned(page, val):
            return f"valor não está na página {a['pagina']}"
        if val not in cit:
            return "valor fora da citação"
        return None
    raise ValueError(f"no check for task {task}")


def apply(rows, answers):
    """The checker over a run's answer list (reader.py output): a copy where each refused answer carries "guard": why.
    Returns (answers, {task: {"checked", "refused", "reasons"}})."""
    keys = {r["id"]: r for r in rows}
    out, stats = [answers[0]], {}
    for o in answers[1:]:
        o = dict(o)
        r = keys.get(o["key"])
        if r and r["task"] in TASKS and o.get("text"):
            s = stats.setdefault(r["task"], {"checked": 0, "refused": 0, "reasons": {}})
            s["checked"] += 1
            why = check(r["task"], r["prompt"], o["text"])
            if why:
                o["guard"] = why
                s["refused"] += 1
                s["reasons"][why] = s["reasons"].get(why, 0) + 1
        out.append(o)
    out[0] = {"meta": {**answers[0]["meta"], "guard": "checked"}}
    return out, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True); ap.add_argument("--answers", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(ROOT / a.rows, encoding="utf-8") if l.strip()]
    answers = json.load(open(ROOT / a.answers, encoding="utf-8"))
    out, stats = apply(rows, answers)
    Path(ROOT / a.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(ROOT / a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for t, s in sorted(stats.items()):
        print(f"{t}: checked {s['checked']} refused {s['refused']}")
        for why, n in sorted(s["reasons"].items(), key=lambda x: -x[1]):
            print(f"  {n}  {why}")
    for o in out[1:]:
        if o.get("guard"):
            print(f"- {o['key']}  {o['guard']}  {o['text'][:160]}")


if __name__ == "__main__":
    main()
