"""«Pergunte à lei» (D22): a técnico's question in their own words → the passages of the decomposed law that answer it, quoted letter
by letter, with «sempre / condicional / não» decided by code from the rule pack. AMALIA, when asked, picks the passage among the
candidates the code found (the D0 «exigencia» task it was trained on: passage 94 %, citação 93 % in round 11) — its «exigido»
label (53 %) is not used; the code's reading of the condition is. Nothing it says is shown unless the passage id is one of the
candidates and the citation equals that passage's text.

    python3 -I engine/law_search.py "preciso de projeto de gás numa moradia?"
"""
import json
import math
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORTARIA = "Portaria n.º 320/2026/1"
RJUE = "RJUE (Decreto-Lei n.º 555/99, redação do Decreto-Lei n.º 108/2026)"
HEAD = ("Passagens da lei disponíveis (id — texto). Responde escolhendo uma delas: copia o id em «passagem» e o texto inteiro, letra a letra, em «citacao». "
        "Se nenhuma das passagens responde, responde {\"resposta\": \"nao_sei\"}.\n\n")
SCOPE = ("Nota: para a comunicação prévia de obras de edificação contam o Anexo V n.º 27 e os elementos comuns n.os 5 a 17; um elemento de outra lista "
         "(loteamento, PIP, licença, utilização) não é exigido neste pedido. «Condicional» quando a própria passagem põe uma condição (quando, caso, sempre que, nos casos). ")
COND = re.compile(r"\b(quando|caso|se |sempre que|nos casos|desde que|salvo|exceto|aplicando-se)\b", re.I)
STOP = set("a o os as um uma uns umas de do da dos das em no na nos nas por para com sem sobre entre e ou que qual quais se não nao é e são sao ser ter há ha ao à aos às este esta estes estas esse essa isso isto aquele aquela seu sua seus suas meu minha num numa num pelo pela pelos pelas mais menos muito pouco como onde quando preciso precisa tenho tem posso pode deve devo obrigatório obrigatorio obrigatoria necessário necessario exigido exige entregar apresentar pedido".split())
LISTS = {"CP/CPEDI": ["anexo-V.27"] + [f"anexo-V.{n}" for n in range(5, 18)]}


def fold(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def toks(s):
    return [t[:6] for t in re.findall(r"[a-z0-9]+", fold(s)) if t not in STOP and len(t) > 2]


def label_of(path):
    parts = path.split(".")
    if parts[0].startswith("anexo-"):
        out, rest = [f"Anexo {parts[0].split('-', 1)[1]}"], parts[1:]
    elif parts[0] == "anexo" and len(parts) > 1 and parts[1].startswith("art"):
        out, rest = [f"artigo {parts[1][3:]}.º"], parts[2:]
    elif parts[0].startswith("art"):
        out, rest = [f"artigo {parts[0][3:]}.º"], parts[1:]
    else:
        return path
    names = ["n.º {}", "alínea {})", "subalínea {})", "ponto {}"]
    for i, r in enumerate(rest):
        out.append(names[min(i, 3)].format(r))
    return ", ".join(out)


def strip_label(text):
    return re.sub(r"^\s*(\d+\s*-\s*|[a-z]{1,4}\)\s*|[ivx]+\)\s*)", "", text).strip()


class Law:
    def __init__(self):
        self.p = {}
        port = json.loads((ROOT / "structure" / "portaria-320-2026-1.json").read_text(encoding="utf-8"))["passages"]
        for x in port:
            if x["path"].startswith(("anexo-V.", "anexo-VI.", "anexo-VII.")) and x["kind"] != "heading" and len(strip_label(x["text"])) >= 25:
                self.p[x["id"]] = {**x, "act": PORTARIA, "label": label_of(x["path"])}
        f = ROOT / "structure" / "decreto-lei-108-2026.json"
        if f.exists():
            for x in json.loads(f.read_text(encoding="utf-8"))["passages"]:
                if re.match(r"anexo\.art(\d+[A-Z-]*)(\.|$)", x["path"]) and x["kind"] != "heading" and len(strip_label(x["text"])) >= 25:
                    self.p[x["id"]] = {**x, "act": RJUE, "label": label_of(x["path"])}
        self.rules = {r["passage"]: r for r in json.loads((ROOT / "law" / "cp-edificacao.json").read_text(encoding="utf-8"))["rules"]}
        self.order = list(self.p)
        self.tf = {pid: {} for pid in self.p}
        df = {}
        for pid, x in self.p.items():
            ts = toks(x["text"]) + toks(x["label"]) * 2
            for t in ts:
                self.tf[pid][t] = self.tf[pid].get(t, 0) + 1
            for t in set(ts):
                df[t] = df.get(t, 0) + 1
        n = len(self.p)
        self.idf = {t: math.log((n + 1) / (d + 0.5)) for t, d in df.items()}
        self.len = {pid: sum(v.values()) for pid, v in self.tf.items()}
        self.avg = sum(self.len.values()) / max(n, 1)

    def search(self, q, k=8, scope="CP/CPEDI"):
        qt = toks(q)
        scored = []
        for pid in self.p:
            s = 0.0
            for t in qt:
                f = self.tf[pid].get(t, 0)
                if f:
                    s += self.idf.get(t, 0) * f * 2.2 / (f + 1.2 * (0.25 + 0.75 * self.len[pid] / self.avg))
            if s > 0:
                if scope and self.in_scope(pid, scope):
                    s *= 1.3
                scored.append((s, pid))
        scored.sort(reverse=True)
        return [self.card(pid, scope, s) for s, pid in scored[:k]]

    def in_scope(self, pid, scope):
        path = self.p[pid]["path"]
        return any(path == l or path.startswith(l + ".") for l in LISTS.get(scope, []))

    def card(self, pid, scope="CP/CPEDI", score=None):
        x = self.p[pid]
        passage = x["path"].replace("anexo-", "") if x["act"] == PORTARIA else None
        rule = self.rules.get(passage) if passage else None
        txt = strip_label(x["text"])
        if x["act"] == PORTARIA and x["path"].startswith("anexo-V.") and not self.in_scope(pid, scope):
            exig, cond, why = "nao", "", "elemento de outra lista do Anexo V, não da comunicação prévia de obras de edificação"
        elif rule and rule["conditions"]:
            exig, cond, why = "condicional", rule["conditions"][0]["phrase"], "condição lida da própria passagem (regra do pacote cp-edificacao)"
        elif rule:
            exig, cond, why = "sempre", "", "elemento da lista do pedido, sem condição na passagem"
        else:
            m = COND.search(txt)
            exig, cond, why = ("condicional", txt[m.start():].rstrip(";:."), "condição detetada no texto") if m else ("—", "", "passagem fora da lista de elementos: lê-se, não se exige")
        return {"id": pid, "act": x["act"], "label": x["label"], "text": x["text"], "exigido": exig, "condicao": cond, "porque": why, "score": round(score or 0, 2),
                "role": rule["role"] if rule else None}

    def prompt(self, q, cands):
        block = HEAD + "\n".join(f"{c['id']} — {c['text']}" for c in cands) + "\n\n"
        return block + SCOPE + q.strip() + " Responde se é exigido sempre, só em certa condição, ou não, e cita a passagem."

    def check(self, text, cands):
        """The reader's answer as a verified pick: the passage must be a candidate and the citation its text; else None with why."""
        try:
            a = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return None, "não é JSON"
        if a.get("resposta") == "nao_sei":
            return None, "o leitor diz não saber"
        by = {c["id"]: c for c in cands}
        c = by.get(a.get("passagem"))
        if not c:
            return None, "a passagem não está entre as candidatas"
        if " ".join((a.get("citacao") or "").split()) != " ".join(c["text"].split()):
            return None, "a citação não é o texto da passagem"
        return c, None


LAW = None


def law():
    global LAW
    if LAW is None:
        LAW = Law()
    return LAW


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "preciso de projeto de gás numa moradia?"
    for c in law().search(q):
        print(f"{c['score']:5}  {c['exigido']:11} {c['label']}  — {c['text'][:110]}  [{c['condicao'][:60]}]")
