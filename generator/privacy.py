"""Scan PDFs for a private person's identifiers before a real document enters the corpus (rule since wave 2: never).

    python -I generator/privacy.py sources/real/train            # every PDF under the folder
    python -I generator/privacy.py sources/real/train/x.pdf      # one file

Flags, with the surrounding text so a human decides: 9-digit numbers that look like a natural person's NIF (first digit 1, 2
or 3), phone numbers (9xx xxx xxx, 2xx xxx xxx), the words NIF / contribuinte / BI / cartão de cidadão / CC n.º / passaporte /
telemóvel / tlm / portador, professional membership numbers (membro n.º, inscrito ... n.º, cédula), personal e-mail addresses
(gmail, hotmail, sapo, live, outlook, yahoo) and "assinado por". A public body's NIF (5xx xxx xxx, 6xx xxx xxx), a company's
(5xx) and a municipality's phone lines are legitimate and still shown, marked as such, so the reader of the report sees why a
number was kept. Exit code 1 when any file has a hit that is not marked public, 0 otherwise. The decision is the human's.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ocr import pages_text  # noqa: E402

NUM = re.compile(r"(?<!\d)(\d{3})[ .]?(\d{3})[ .]?(\d{3})(?!\d)")
WORDS = re.compile(r"\b(NIF|NIPC|contribuinte|B\.?I\.?|bilhete de identidade|cart[aã]o de cidad[aã]o|CC n|passaporte|telem[oó]vel|tlm|tel\.?|telefone|portador|membro n|inscri[tç][oã]o? n|c[eé]dula|assinado por|assinatura digital)\b", re.I)
MAIL = re.compile(r"[\w.+-]+@(gmail|hotmail|sapo|live|outlook|yahoo|iol|netcabo|clix)\.\w+", re.I)
PRO = re.compile(r"\b(OA|OE|OET|ANET|Ordem dos (Arquitectos|Engenheiros|Engenheiros Técnicos))\b.{0,40}?n[.º°o]?\s*\d{3,6}", re.I | re.S)


PHONE_CTX = re.compile(r"(\+\s?351|tel|fax|t\.|telef|contacto)\W{0,6}$", re.I)


def classify(n, before=""):
    d = n[0]
    if PHONE_CTX.search(before) or before.rstrip().endswith("351"):
        return "telefone (contexto)"
    if d in "123":
        return "NIF pessoa singular?"
    if d == "9":
        return "telemóvel?"
    if d == "2":
        return "telefone fixo?"
    if d in "56":
        return "NIF entidade (público/empresa)"
    if d == "7":
        return "NIF heranças/outros"
    return "número"


def scan(path):
    hits = []
    for i, t in enumerate(pages_text(path)):
        flat = " ".join(t.split())
        for m in NUM.finditer(flat):
            n = "".join(m.groups())
            kind = classify(n, flat[max(0, m.start() - 12): m.start()])
            ctx = flat[max(0, m.start() - 50): m.end() + 30]
            hits.append((i + 1, kind, n, ctx, kind.startswith(("NIF entidade", "telefone (contexto)"))))
        for m in WORDS.finditer(flat):
            hits.append((i + 1, "palavra", m.group(0), flat[max(0, m.start() - 40): m.end() + 60], False))
        for m in MAIL.finditer(flat):
            hits.append((i + 1, "e-mail pessoal", m.group(0), flat[max(0, m.start() - 40): m.end() + 20], False))
        for m in PRO.finditer(flat):
            hits.append((i + 1, "n.º profissional", m.group(0)[:60], flat[max(0, m.start() - 40): m.end() + 20], False))
    return hits


def main(target):
    p = Path(target)
    files = sorted(p.rglob("*.pdf")) if p.is_dir() else [p]
    bad = 0
    for f in files:
        hits = scan(f)
        private = [h for h in hits if not h[4]]
        flag = "REVIEW" if private else "clean "
        bad += bool(private)
        print(f"{flag} {f.name}: {len(private)} to review, {len(hits) - len(private)} entity numbers")
        for page, kind, what, ctx, public in hits[:40]:
            print(f"    p{page} [{kind}] {what!r} … {ctx!r}")
        if len(hits) > 40:
            print(f"    … {len(hits) - 40} more")
    print(f"{len(files)} files, {bad} to review")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "sources/real/train"))
