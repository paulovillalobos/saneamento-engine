"""The verdict layer (DECISIONS D18): an expediente folder in, the técnico's verdict out.

    check(folder) -> list of items                       the contract exam/score.py expects
    python3 -I engine/application.py exam/dossiers/B     writes verdict.json, convite.md, verdict.html under engine/verdicts/<key>/

Five steps, in order. (1) Inventory: every file, its NoPaper slot (the file-name prefix), is it a PDF, PDF/A mark, digital
signature, pages of text. Code. (2) Required list: every Annex V element the Portaria asks of a CPEDI, the Celorico slots that
carry it (celorico/mapping/documents.json), mandatory or optional in the municipal catalogue; a mandatory element with no file is
a finding «missing_required» with the law's own quote; a conditional element with no file is «not_assessed», naming the condition,
unless engine/cpedi.json decides it (each entry says why). Code. (3) Element check: the reader's answer to «which element is this
file» (D1, guarded) against the slot; a file whose answer the checker refused is «not_read»; a file the reader places in another
family goes to the técnico for «review», never as a finding (the reader is right 74 of 77 times, a wrong guess must not become
a convite). Model + guard. (4) Facts: the reader's D2 answers on the requerimento, the memória, the estimate and the calendar;
code compares across files («value_mismatch», both quotes) and within a file («impossible_value»); a null or refused answer is
«not_read». Model reads, code decides. (5) Format: not a PDF, no PDF/A identification, unsigned where the slot demands a
signature, a termo without the Annex VII wording, the DWG the law adds to the planta de implantação. Code.

Statuses: finding (goes into the convite), not_assessed (the engine cannot decide and says which fact is missing), provisional
(PDF/A conformance: claimed, not validated), review (reader and slot disagree), not_read (the reader gave no checked answer).
The reader's answers come from engine/read.py (Modal, guarded), stored under engine/reads/<key>/answers-checked.json; without
them steps 3 and 4 report every file and fact as not_read, and the code-only findings still stand.
"""
import argparse
import hashlib
import html
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "generator"))
import guard  # noqa: E402
from generator import d1d2  # noqa: E402  (prompts, questions, window, extract: the reader's own language)

LAW = json.loads((ROOT / "law" / "cp-edificacao.json").read_text(encoding="utf-8"))
RULES = {r["passage"]: r for r in LAW["rules"]}
GP = LAW["general_provisions"]
TABLE = json.loads((ROOT / "engine" / "cpedi.json").read_text(encoding="utf-8"))
DOCS = {d["code"]: d for d in json.loads((ROOT / "celorico" / "mapping" / "documents.json").read_text(encoding="utf-8"))["documents"]
        if TABLE["request"] in d["requests"]}
PREFIX = "portaria-320-2026-1:anexo-"
LAW_ID = "dr:portaria:320/2026/1"


def _catalogue():
    cat = json.loads((ROOT / "celorico" / "catalogue" / "catalogue.json").read_text(encoding="utf-8"))
    code = TABLE["request"].split("/")[1]
    for proc in cat["procedures"]:
        for g in proc["groups"]:
            for r in g["requests"]:
                if r["code"] == code:
                    return {s["code"]: s for s in r["slots"]}
    raise KeyError(TABLE["request"])


CAT = _catalogue()
SLOTS_OF = {}  # passage -> [slot codes carrying it]
for _code, _d in DOCS.items():
    for _p in _d["passages"]:
        SLOTS_OF.setdefault(_p.replace("anexo-", ""), []).append(_code)


def law(ref):
    """(ref, quote) for an Annex V passage or a general provision, from the rule pack (every quote hash-checked there)."""
    if ref in RULES:
        return {"ref": ref, "quote": RULES[ref]["quote"]}
    if ref in GP:
        return {"ref": ref, "quote": GP[ref]["quote"]}
    raise KeyError(ref)


# ---- step 1: inventory ----------------------------------------------------------------------------------------------------
def inventory(folder):
    files = []
    for path in sorted(p for p in Path(folder).iterdir() if p.is_file() and not p.name.startswith(".") and p.suffix.lower() != ".json" and p.suffix.lower() != ".jsonl"):
        data = path.read_bytes()
        is_pdf = data.startswith(b"%PDF")
        slot = path.name.split("-")[0] if "-" in path.name else None
        pages, n = d1d2.extract(path, is_pdf)
        signed = is_pdf and (b"/Type /Sig" in data or b"/Type/Sig" in data or b"/ByteRange" in data)
        files.append({"file": path.name, "slot": slot if slot in CAT else None, "slot_raw": slot, "is_pdf": is_pdf, "ext": path.suffix.lower(),
                      "pdfa": is_pdf and b"pdfaid:part" in data, "signed": signed, "signer": signer_of(data) if signed else None,
                      "declarant": declarant_of(pages) if pages else None, "pages": pages, "n": n})
    return files


SIG_CONTENTS = re.compile(rb"/Type\s*/Sig.*?/Contents\s*<([0-9A-Fa-f]+)>", re.S)
SUBJECT_CN = re.compile(r"CN\s*=\s*([^,/\n]+)")


def signer_of(data):
    """{"cn", "sha256"} of the signing certificate inside the first CMS signature of a PDF (openssl pkcs7 -print_certs), or None."""
    m = SIG_CONTENTS.search(data)
    if not m:
        return None
    try:
        der = bytes.fromhex(m.group(1).decode("ascii"))  # zero padding after the CMS is fine for openssl; stripping it can cut a real trailing 00
        out = subprocess.run(["openssl", "pkcs7", "-inform", "DER", "-print_certs"], input=der, capture_output=True, check=True).stdout.decode("utf-8", "replace")
    except (ValueError, subprocess.CalledProcessError, FileNotFoundError):
        return None
    certs = [c for c in out.split("-----END CERTIFICATE-----") if "-----BEGIN CERTIFICATE-----" in c]
    if not certs:
        return None
    # the signer is the certificate whose subject is not a CA (openssl prints subject= before each certificate)
    for c in certs:
        subj = next((l for l in c.splitlines() if l.startswith("subject=")), "")
        if "CA " not in subj and "/CN=CA" not in subj and " CA" not in subj.split("CN=")[-1][:3]:
            pem = c[c.index("-----BEGIN"):] + "-----END CERTIFICATE-----"
            return {"cn": (SUBJECT_CN.search(subj) or [None, None])[1].strip() if SUBJECT_CN.search(subj) else subj, "sha256": hashlib.sha256(pem.encode()).hexdigest()[:16]}
    return None


DECLARANT = re.compile(r"(?:^|\n)\s*(?:Eu,\s*)?([A-ZÁÉÍÓÚÂÊÔÃÕÇ][^,\n]{2,80}?),\s*(?:[a-zç ]+,\s*)?com domicílio em", re.M)


def declarant_of(pages):
    """The person who declares in a termo de responsabilidade: the name before «, com domicílio em» (Annex VII models), else None."""
    text = "\n".join(pages[:1])
    m = DECLARANT.search(text)
    return " ".join(m.group(1).split()) if m else None


# ---- step 2: the required list --------------------------------------------------------------------------------------------
def required(files):
    out, elements = [], []
    by_slot = {}
    for f in files:
        if f["slot"]:
            by_slot.setdefault(f["slot"], []).append(f)
    for passage, rule in RULES.items():
        if rule["role"] != "document":
            continue
        entry = TABLE["elements"].get(passage, {})
        slots = entry.get("slots", []) + [s for s in SLOTS_OF.get(passage, []) if s not in entry.get("slots", [])]  # the table's order first: the slot a técnico opens
        present = [f["file"] for s in slots for f in by_slot.get(s, [])]
        marker = entry.get("text_marker")
        if marker and not present:
            present = [f["file"] for s in entry.get("slots", []) for f in by_slot.get(s, [])
                       if f["pages"] and marker in " ".join(f["pages"][0].split()).lower()]
        mandatory = [s for s in slots if CAT.get(s, {}).get("kind") == "O"]
        status = {"element": passage, "slots": slots, "files": present, "mandatory_slots": mandatory}
        if present:
            status["state"] = "present"
        else:
            decision = entry.get("decision") or ("mandatory" if mandatory else ("conditional" if rule["conditions"] else "unmapped"))
            if decision in ("required", "mandatory"):
                status["state"] = "missing"
                item = {"status": "finding", "type": "missing_required", "rule": passage, "law": law(passage)}
                if mandatory or slots:
                    item["slot"] = (mandatory or slots)[0]
                if entry.get("why"):
                    item["why"] = entry["why"]
                out.append(item)
            elif decision == "satisfied_by":
                have = [f["file"] for s in entry["by"] for f in by_slot.get(s, [])]
                status["state"] = "satisfied_by" if have else "not_required_here"
                status["by"] = have
            elif decision == "optional":
                status["state"] = "optional"
            else:  # not_assessed | conditional | unmapped
                status["state"] = "not_assessed"
                cond = entry.get("condition") or (rule["conditions"][0]["phrase"] if rule["conditions"] else "no municipal slot marks it mandatory and the law states no condition the expediente can answer")
                item = {"status": "not_assessed", "type": "conditional_requirement", "rule": passage, "law": law(passage), "condition": cond}
                if slots:
                    item["slot"] = slots[0]
                out.append(item)
        elements.append(status)
    # every mandatory municipal slot that carries an Annex V element (relation same / part_of) and has no file: the element may be
    # present through a sibling slot (V.14 has one insurance slot per author), the slot is still empty. Conditional law → not_assessed.
    for code, d in DOCS.items():
        if CAT.get(code, {}).get("kind") != "O" or d["relation"] not in ("same", "part_of") or by_slot.get(code) or not d["passages"]:
            continue
        passage = d["passages"][0].replace("anexo-", "")
        rule = RULES.get(passage)
        entry = TABLE["elements"].get(passage, {})
        if entry.get("decision") in ("not_assessed", "optional", "satisfied_by"):
            continue
        if rule and rule["conditions"] and entry.get("decision") != "required":
            out.append({"status": "not_assessed", "type": "conditional_requirement", "rule": passage, "slot": code, "law": law(passage),
                        "condition": rule["conditions"][0]["phrase"] + f" — the municipal slot {code} is marked mandatory, the law conditions it"})
        elif not any(i.get("slot") == code and i["type"] == "missing_required" for i in out):
            out.append({"status": "finding", "type": "missing_required", "rule": passage, "slot": code, "law": law(passage),
                        "detail": f"campo obrigatório {code} («{CAT[code]['label']}») sem ficheiro"})
    return out, elements


# ---- step 5: format -------------------------------------------------------------------------------------------------------
def formats(files, folder):
    out = []
    core = TABLE["wording_core"].lower()
    wording_slots = set(SLOTS_OF.get(TABLE["wording_slots_passage"], []))
    exts = {f["ext"] for f in files}
    for f in files:
        base = {"slot": f["slot"], "file": f["file"]}
        if f["ext"] == ".pdf" and not f["is_pdf"]:
            out.append({"status": "finding", "type": "not_pdf", **base, "law": law("VI.1.a"), "detail": "o ficheiro tem o nome .pdf mas o conteúdo não é um PDF"})
            continue
        if not f["is_pdf"]:
            continue
        if not f["pdfa"]:
            out.append({"status": "finding", "type": "not_pdfa", **base, "law": law("VI.1.a"), "detail": "sem identificação PDF/A (pdfaid) no ficheiro"})
        if f["slot"] and CAT[f["slot"]]["signature"] == "S" and not f["signed"]:
            out.append({"status": "finding", "type": "unsigned", **base, "law": law("VI.1"), "detail": "o campo exige assinatura e o ficheiro não traz assinatura digital"})
        if f["slot"] in wording_slots and f["pages"] and core not in " ".join(" ".join(f["pages"]).split()).lower():
            out.append({"status": "finding", "type": "template_wording_missing", **base, "law": {"ref": "VII.I", "quote": TABLE["wording_quote"]},
                        "detail": "o termo não declara que o projeto observa as normas legais e regulamentares aplicáveis (redação do Anexo VII)"})
    for slot, c in TABLE["complements"].items():
        if any(f["slot"] == slot for f in files) and not any(e in exts for e in c["extensions"]):
            out.append({"status": "finding", "type": "missing_complement", "slot": slot, "law": law(c["law"]),
                        "detail": f"a peça do campo {slot} vem só em PDF; a lei acrescenta o ficheiro {'/'.join(c['extensions'])}"})
    signed = [f["file"] for f in files if f["signed"]]
    out.append({"status": "not_assessed", "type": "signature_qualification", "all_signed_files": True, "files": signed, "law": law("VI.1"),
                "condition": "whether the signatures are qualified (certificate chain to a qualified trust service) is not checked here"})
    claiming = [f["file"] for f in files if f["pdfa"]]
    out.append({"status": "provisional", "type": "pdfa_conformance", "files_claiming_pdfa": True, "files": claiming, "law": law("VI.1.a"),
                "condition": "PDF/A identification is present; conformance is not validated (no reference validator)"})
    return out


# ---- steps 3 and 4: the reader's answers -----------------------------------------------------------------------------------
def key_of(folder):
    folder = Path(folder).resolve()
    return f"{folder.parent.name}-{folder.name}"


def load_reads(folder):
    d = ROOT / "engine" / "reads" / key_of(folder)
    f = d / "answers-checked.json"
    if not f.exists():
        return None
    rows = {r["id"]: r for r in (json.loads(l) for l in (d / "prompts.jsonl").read_text(encoding="utf-8").splitlines() if l.strip())}
    answers = json.load(open(f, encoding="utf-8"))
    return {"meta": answers[0]["meta"], "rows": rows, "answers": {a["key"]: a for a in answers[1:]}}


def family(passage):
    """The parent group a passage belongs to, for the review rule: V.27.i.* (specialty projects), V.27.b.* (drawn pieces), V.11, V.14…"""
    parts = passage.split(".")
    return ".".join(parts[:3]) if passage.startswith("V.27.") and len(parts) > 3 else ".".join(parts[:2])


def elements_read(files, reads, key):
    out = []
    for f in files:
        if not f["is_pdf"] or not f["slot"]:
            continue
        rid = d1d2.rid("d1", key, f["file"])
        a = reads["answers"].get(rid) if reads else None
        base = {"slot": f["slot"], "file": f["file"]}
        if a is None or a.get("guard") or not a.get("text"):
            out.append({"status": "not_read", "type": "element", **base, "detail": (a or {}).get("guard") or "no checked answer from the reader"})
            continue
        ans = json.loads(a["text"])
        want = [p.replace("anexo-", "") for p in DOCS[f["slot"]]["passages"]]
        got = ans["elemento"].replace(PREFIX, "") if ans["elemento"] else None
        if got and (got in want or any(family(got) == family(w) for w in want)):
            out.append({"status": "ok", "type": "element", **base, "element": got, "quote": ans["citacao"], "kind": ans["tipo"]})
        elif not want:
            out.append({"status": "ok", "type": "element", **base, "element": got, "quote": ans["citacao"], "kind": ans["tipo"], "detail": "slot has no Annex V element"})
        else:
            out.append({"status": "review", "type": "slot_content", **base, "expected": want, "element": got, "quote": ans["citacao"], "kind": ans["tipo"],
                        "detail": "the reader places this file under another element than its slot" if got else "the reader says this file is not an Annex V element"})
    return out


def names_fact(field, value, quote):
    """True when the piece of the quote that holds the value also names the fact asked. A quote is cut at ; , . and «e»/«com»
    boundaries; the segment with the value must match the field's keyword. «superfície do terreno 1200 m2; área da parcela 1200 m2;
    área de implantação de 277 m2» names the implantação, but 1200 sits in the other segments: not an implantação reading."""
    kw = re.compile(KEYWORD.get(field, "."), re.I)
    segs = [x for x in re.split(r"[;,.]|\s+e\s+|\s+com\s+", quote or "") if x.strip()]
    hits = [x for x in segs if value in x]
    return any(kw.search(x) for x in hits) if hits else bool(kw.search(quote or ""))


KEYWORD = {**d1d2.KEYWORD, "area_parcela": "parcela|lote|terreno", "area_total_construcao": "constru", "area_implantacao": "implanta", "altura_edificacao": "altura",
           "pisos_acima_soleira": "piso", "fogos": "fogo|habita|tipologia|T\\d", "uso": "destin|uso|habita|com[eé]rcio|armaz|servi", "custo_total": "custo|valor|total|€",
           "prazo_meses": "mes|prazo|dura|conclus", "validade_seguro_fim": "valid|até|ate|vigor|\\d{4}"}

NUM = re.compile(r"\d{1,3}(?:[ .]\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?")


WORDS = {"zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "três": 3, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10,
         "onze": 11, "doze": 12, "treze": 13, "catorze": 14, "quatorze": 14, "quinze": 15, "dezasseis": 16, "dezassete": 17, "dezoito": 18, "dezanove": 19, "vinte": 20}


def number(value):
    """The number a read value states: digits (Portuguese thousands and decimal marks) or a number word («dois pisos», «um fogo»)."""
    if value is None:
        return None
    w = value.strip().lower()
    if w in WORDS:
        return float(WORDS[w])
    m = NUM.search(value)
    if not m:
        return None
    s = m.group(0)
    if re.fullmatch(r"\d{1,3}(?:[ .]\d{3})+(?:,\d+)?", s):
        s = s.replace(" ", "").replace(".", "")
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def fields_of(slot):
    """The fact questions asked of a slot: the table's list for the slot, plus the list for the Annex V passage it carries."""
    out = list(TABLE["facts"].get(slot or "", []))
    for p in DOCS.get(slot, {}).get("passages", []):
        for field in TABLE.get("facts_by_passage", {}).get(p.replace("anexo-", ""), []):
            if field not in out:
                out.append(field)
    return out


MONTHS = {m: i + 1 for i, m in enumerate(["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"])}


def iso_date(value):
    """YYYY-MM-DD from an ISO date, a dd/mm/yyyy or dd-mm-yyyy date, or «31 de dezembro de 2026»."""
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", value or "")
    if m:
        return m.group(0)
    m = re.search(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})", value or "")
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    m = re.search(r"(\d{1,2}) de ([a-zç]+) de (\d{4})", (value or "").lower())
    return f"{m.group(3)}-{MONTHS[m.group(2)]:02d}-{int(m.group(1)):02d}" if m and m.group(2) in MONTHS else None


def facts_read(files, reads, key):
    items, values = [], {}
    for f in files:
        fields = fields_of(f["slot"])
        if not fields or not f["is_pdf"]:
            continue
        for field in fields:
            rid = d1d2.rid("d2", key, f["file"], field)
            a = reads["answers"].get(rid) if reads else None
            if a is None or a.get("guard") or not a.get("text"):
                items.append({"status": "not_read", "type": "fact", "field": field, "slot": f["slot"], "file": f["file"], "detail": (a or {}).get("guard") or "no checked answer from the reader"})
                continue
            ans = json.loads(a["text"])
            if ans["valor"] is None:
                items.append({"status": "absent", "type": "fact", "field": field, "slot": f["slot"], "file": f["file"], "detail": "o documento não declara este facto (resposta do leitor)"})
                continue
            if not names_fact(field, ans["valor"], ans["citacao"]):
                # the value is on the page and inside the quote (the grammar saw to that), but the quote does not name the fact asked:
                # the reader took a neighbour (round 11 reads «superfície do terreno 1200» for the implantação). Code does not decide on it.
                items.append({"status": "not_read", "type": "fact", "field": field, "slot": f["slot"], "file": f["file"], "value": ans["valor"], "quote": ans["citacao"],
                              "detail": "a citação não nomeia o facto perguntado"})
                continue
            values.setdefault(field, []).append({"file": f["file"], "slot": f["slot"], "value": ans["valor"], "page": ans["pagina"], "quote": ans["citacao"], "number": number(ans["valor"])})
    # across files: the same fact with two different values
    for field, vs in values.items():
        for i in range(len(vs)):
            for j in range(i + 1, len(vs)):
                a, b = vs[i], vs[j]
                if a["number"] is not None and b["number"] is not None:
                    differ = abs(a["number"] - b["number"]) > 0.005 * max(abs(a["number"]), abs(b["number"]), 1)
                else:
                    differ = " ".join(a["value"].lower().split()) != " ".join(b["value"].lower().split())
                if differ:
                    items.append({"status": "finding", "type": "value_mismatch", "field": field, "files": [a["file"], b["file"]], "file": a["file"], "slots": [a["slot"], b["slot"]],
                                  "values": {a["file"]: a["value"], b["file"]: b["value"]},
                                  "evidence": [{"file": x["file"], "page": x["page"], "quote": x["quote"]} for x in (a, b)],
                                  "detail": f"{field}: {a['value']} em {a['file']} contra {b['value']} em {b['file']}"})
    # within a file: a plot smaller than the building standing on it
    by_file = {}
    for field, vs in values.items():
        for v in vs:
            by_file.setdefault(v["file"], {})[field] = v
    for file, fv in by_file.items():
        p, i = fv.get("area_parcela"), fv.get("area_implantacao")
        if p and i and p["number"] is not None and i["number"] is not None and p["number"] < i["number"]:
            items.append({"status": "finding", "type": "impossible_value", "field": "area_parcela", "file": file, "slot": p["slot"],
                          "values": {"area_parcela": p["value"], "area_implantacao": i["value"]},
                          "evidence": [{"file": file, "page": x["page"], "quote": x["quote"]} for x in (p, i)],
                          "detail": f"área da parcela {p['value']} inferior à área de implantação {i['value']} em {file}"})
    # an insurance that ends before the day the expediente came in
    submitted = SUBMITTED.get(key)
    if submitted:
        for v in values.get("validade_seguro_fim", []):
            end = iso_date(v["value"])
            if end and end < submitted:
                items.append({"status": "finding", "type": "expired_insurance", "slot": v["slot"], "file": v["file"], "field": "validade_seguro_fim", "law": law("V.14"),
                              "values": {"validade_fim": end, "submetido": submitted}, "evidence": [{"file": v["file"], "page": v["page"], "quote": v["quote"]}],
                              "detail": f"a apólice termina em {end}, antes da entrega do expediente em {submitted}"})
    return items, values


SUBMITTED = {}  # key -> submitted_at, set by verdict() from submission.json


# ---- step 5b: the site and the signer, code over the text and the certificates ------------------------------------------------
SITE = re.compile(r"localizad[ao] em (.+?)(?=, cuj[ao]|, observa|, com período|, declara|, freguesia|\. [A-ZÀ-Ú]|;|$)", re.I)


def consistency(files, meta):
    out = []
    site = " ".join((meta.get("site") or "").split()) if isinstance(meta.get("site"), str) else ""
    site_slots = {s for p in TABLE.get("site_slots_passage", []) for s in SLOTS_OF.get(p, [])}
    if site:
        for f in files:
            if f["slot"] in site_slots and f["pages"]:
                m = SITE.search(" ".join(" ".join(f["pages"]).split()))
                if m and not " ".join(m.group(1).split()).lower().startswith(site.lower()):  # the text may go on («, concelho de…»); it must begin with the request's site
                    out.append({"status": "finding", "type": "wrong_site", "slot": f["slot"], "file": f["file"], "values": {"REQ": site, f["slot"]: m.group(1).strip()},
                                "evidence": [{"file": f["file"], "page": 1, "quote": m.group(0)}],
                                "detail": f"o documento situa a obra em «{m.group(1).strip()}», o requerimento em «{site}»"})
    # one certificate, one declarant (engine/cpedi.json signer_rule)
    authors = {s for s in SLOTS_OF.get("V.11", [])}
    others = {s for p in ("V.12", "V.27.k") for s in SLOTS_OF.get(p, [])}
    owner = {}
    for f in files:
        if f["slot"] in authors and f["signer"] and f["declarant"]:
            owner.setdefault(f["signer"]["sha256"], set()).add(f["declarant"])
    for f in files:
        if f["slot"] in others and f["signer"] and f["declarant"]:
            names = owner.get(f["signer"]["sha256"])
            if names and f["declarant"] not in names:
                out.append({"status": "finding", "type": "wrong_signer", "slot": f["slot"], "file": f["file"], "law": law("VI.1"),
                            "values": {"declarante": f["declarant"], "certificado": f["signer"]["cn"], "mesmo certificado em": sorted(names)},
                            "detail": f"o termo é declarado por {f['declarant']} mas assinado com o certificado «{f['signer']['cn']}» que assina os termos de {', '.join(sorted(names))}"})
    return out


# ---- the verdict ----------------------------------------------------------------------------------------------------------
def verdict(folder):
    folder = Path(folder)
    key = key_of(folder)
    sub = folder / "submission.json"
    meta = json.loads(sub.read_text(encoding="utf-8")) if sub.exists() else {}
    SUBMITTED[key] = meta.get("submitted_at")
    files = inventory(folder)
    reads = load_reads(folder)
    req, elements = required(files)
    fmt = formats(files, folder)
    cons = consistency(files, meta)
    el = elements_read(files, reads, key)
    fx, values = facts_read(files, reads, key)
    items = req + fmt + cons + el + fx
    return {"expediente": meta.get("expediente") or meta.get("dossier") or folder.name, "key": key, "folder": str(folder),
            "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "law": LAW_ID, "procedure": TABLE["procedure"], "request": TABLE["request"],
            "reader": (reads or {}).get("meta"), "operation": meta.get("operation"), "applicant": meta.get("applicant", {}).get("name"),
            "files": [{k: v for k, v in f.items() if k != "pages"} for f in files],
            "counts": {s: sum(1 for i in items if i["status"] == s) for s in ("finding", "not_assessed", "provisional", "review", "not_read", "absent", "ok")},
            "findings": [i for i in items if i["status"] == "finding"], "not_assessed": [i for i in items if i["status"] == "not_assessed"],
            "provisional": [i for i in items if i["status"] == "provisional"], "review": [i for i in items if i["status"] == "review"],
            "not_read": [i for i in items if i["status"] == "not_read"], "absent": [i for i in items if i["status"] == "absent"], "elements_ok": [i for i in el if i["status"] == "ok"],
            "elements": elements, "facts": values}


def check(folder):
    """The exam contract: every item with a status (finding | not_assessed | provisional | review | not_read | ok)."""
    v = verdict(folder)
    return v["findings"] + v["not_assessed"] + v["provisional"] + v["review"] + v["not_read"] + v["absent"] + v["elements_ok"]


def convite(v):
    """Draft of the convite ao aperfeiçoamento (RJUE art. 11.º n.º 3): one paragraph per finding, with the law's words; for the técnico to edit, sign or discard."""
    lines = [f"# Convite ao aperfeiçoamento — expediente {v['expediente']}", "",
             "Exmo.(a) Senhor(a) Requerente,", "",
             f"Analisada a comunicação prévia de obras de edificação ({v.get('operation') or 'operação urbanística'}), verifica-se que a instrução "
             "não satisfaz o disposto na Portaria n.º 320/2026/1, nos pontos seguintes, pelo que se convida V. Ex.ª a suprir as deficiências no prazo "
             "legal (artigo 11.º do RJUE):", ""]
    for n, f in enumerate(v["findings"], 1):
        label = CAT.get(f.get("slot") or "", {}).get("label")
        where = f" ({f['file']})" if f.get("file") else (f" «{label}» (campo {f['slot']})" if label else "")
        what = {"missing_required": "Falta o elemento", "missing_complement": "Falta o elemento complementar ao", "not_pdf": "O ficheiro não é um PDF:",
                "not_pdfa": "O ficheiro não tem identificação PDF/A:", "unsigned": "O ficheiro não está assinado digitalmente:",
                "template_wording_missing": "O termo de responsabilidade não contém a declaração do Anexo VII:",
                "value_mismatch": "Valores divergentes entre documentos:", "impossible_value": "Valor incompatível:", "wrong_site": "Local da obra divergente:",
                "expired_insurance": "Seguro caducado:", "wrong_signer": "Assinatura de outra pessoa:"}.get(f["type"], f["type"])
        detail = f.get("detail") or ""
        lawref = f"Portaria n.º 320/2026/1, Anexo {f['law']['ref']}: «{f['law']['quote']}»" if f.get("law") else ""
        lines.append(f"{n}. {what}{where}. {detail}".strip() + (f"\n   {lawref}" if lawref else ""))
        for e in f.get("evidence", []):
            lines.append(f"   — {e['file']}, página {e['page']}: «{e['quote']}»")
        lines.append("")
    if v["not_assessed"]:
        lines += ["Nota interna (não segue no convite): elementos cuja exigibilidade depende de factos não constantes do expediente —",
                  *[f"- {i['rule']}: {i['condition']}" for i in v["not_assessed"] if i.get("rule")], ""]
    if v["not_read"]:
        lines += [f"Nota interna: {len(v['not_read'])} leitura(s) sem resposta verificada — ver verdict.json (not_read).", ""]
    lines += ["Com os melhores cumprimentos,", "", "O/A Técnico(a)", f"(rascunho gerado {v['checked_at']}, a validar)"]
    return "\n".join(lines) + "\n"


def page(v):
    """One screen: yes/no per element, then the findings with their evidence."""
    def esc(s):
        return html.escape(str(s if s is not None else ""))
    state_label = {"present": "sim", "missing": "FALTA", "not_assessed": "não avaliado", "satisfied_by": "sim (via outro elemento)", "optional": "facultativo", "not_required_here": "n/a"}
    rows = "".join(f"<tr class='{esc(e['state'])}'><td>{esc(e['element'])}</td><td>{esc(', '.join(e['slots']))}</td><td>{esc(state_label.get(e['state'], e['state']))}</td>"
                   f"<td>{esc(', '.join(e['files']))}</td></tr>" for e in v["elements"])
    finds = "".join(f"<li><b>{esc(f['type'])}</b> {esc(f.get('slot') or '')} {esc(f.get('file') or '')} — {esc(f.get('detail') or '')}"
                    + (f"<br><small>Anexo {esc(f['law']['ref'])}: «{esc(f['law']['quote'])}»</small>" if f.get("law") else "")
                    + "".join(f"<br><small>{esc(e['file'])} p.{esc(e['page'])}: «{esc(e['quote'])}»</small>" for e in f.get("evidence", [])) + "</li>" for f in v["findings"])
    na = "".join(f"<li>{esc(i.get('rule') or i['type'])} — {esc(i.get('condition'))}</li>" for i in v["not_assessed"])
    rev = "".join(f"<li>{esc(i['file'])}: {esc(i['detail'])} ({esc(i.get('element'))})</li>" for i in v["review"])
    nr = "".join(f"<li>{esc(i['file'])} {esc(i.get('field') or '')}: {esc(i['detail'])}</li>" for i in v["not_read"])
    return f"""<!doctype html><html lang="pt"><head><meta charset="utf-8"><title>Veredicto {esc(v['expediente'])}</title>
<style>body{{font:500 15px/1.4 system-ui,sans-serif;margin:24px;max-width:1100px;color:#111}}table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #ddd;padding:4px 8px;text-align:left;vertical-align:top}}
tr.missing td{{background:#fde8e8;font-weight:700}}tr.not_assessed td{{background:#fff6d6}}tr.present td:nth-child(3){{color:#0a6b2d;font-weight:700}}h2{{margin-top:28px}}small{{color:#333}}</style></head><body>
<h1>Expediente {esc(v['expediente'])} — {esc(v.get('operation') or '')}</h1>
<p><b>{v['counts']['finding']}</b> deficiência(s) · {v['counts']['not_assessed']} não avaliado(s) · {v['counts']['review']} para revisão · {v['counts']['not_read']} não lido(s) · {len(v['files'])} ficheiros · lei {esc(v['law'])} · leitor {esc((v.get('reader') or {}).get('adapter') or 'sem leituras')}</p>
<h2>Deficiências (vão no convite)</h2><ol>{finds or '<li>nenhuma</li>'}</ol>
<h2>Elementos do Anexo V</h2><table><tr><th>Elemento</th><th>Campos NoPaper</th><th>Presente</th><th>Ficheiros</th></tr>{rows}</table>
<h2>Não avaliado (depende de factos fora do expediente)</h2><ul>{na or '<li>nenhum</li>'}</ul>
<h2>Para revisão do técnico</h2><ul>{rev or '<li>nenhum</li>'}</ul>
<h2>Não lido</h2><ul>{nr or '<li>nenhum</li>'}</ul>
<p><small>Gerado {esc(v['checked_at'])}. O leitor lê, o código decide, o técnico assina.</small></p></body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", nargs="+")
    ap.add_argument("--out", default=str(ROOT / "engine" / "verdicts"))
    a = ap.parse_args()
    for folder in a.folder:
        v = verdict(folder)
        out = Path(a.out) / v["key"]
        out.mkdir(parents=True, exist_ok=True)
        (out / "verdict.json").write_text(json.dumps(v, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        (out / "convite.md").write_text(convite(v), encoding="utf-8")
        (out / "verdict.html").write_text(page(v), encoding="utf-8")
        c = v["counts"]
        print(f"{v['key']}: {c['finding']} findings, {c['not_assessed']} not assessed, {c['review']} review, {c['not_read']} not read, {c['ok']} elements confirmed -> {out}")
        for f in v["findings"]:
            print(f"   {f['type']:26} {f.get('slot') or '':7} {f.get('file') or f.get('rule') or ''}")


if __name__ == "__main__":
    main()
