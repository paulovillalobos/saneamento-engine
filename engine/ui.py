"""The técnico's screens (D21, D22, D23): static pages under engine/static/, rendered by substitution. No framework, no build.

    lei(inline=None)                      «Pergunte à lei», the Palantir "Request" layout
    app(pdf_base, back, inline=None)      one expediente, the "full object view, high density" layout
    inbox(rows=None, municipality="")     the expedientes as an inbox (client-side from /v1/expedientes, or inline rows for a preview)

Placeholders in the pages: __CSS__ (engine/static/app.css, inlined so a page opened from a file still looks right), __HEAD__ (the
Blueprint and font links), __DATA__ (JSON or null), __PDF_BASE__, __BACK__, __STATES__. The states and finding labels come from
engine/cpedi.json (work_states, finding_labels): the product's vocabulary is data, not code.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "engine" / "static"
TABLE = json.loads((ROOT / "engine" / "cpedi.json").read_text(encoding="utf-8"))
STATES = [tuple(x) for x in TABLE["work_states"]]
BP = ('<link rel="stylesheet" href="https://unpkg.com/normalize.css@8.0.1/normalize.css">'
      '<link rel="stylesheet" href="https://unpkg.com/@blueprintjs/core@5.10.5/lib/css/blueprint.css">'
      '<link rel="stylesheet" href="https://unpkg.com/@blueprintjs/icons@5.9.0/lib/css/blueprint-icons.css">'
      '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@500;600;700&display=swap">')
EXAMPLES = ["Preciso de projeto de gás numa moradia unifamiliar?", "O levantamento topográfico é sempre obrigatório?", "A planta de implantação tem de ir em DWG?",
            "Quando é que preciso de pareceres de entidades externas?", "Qual é o prazo do convite ao aperfeiçoamento?", "Fotografias do terreno são obrigatórias?"]


def render(name, **subs):
    page = (STATIC / name).read_text(encoding="utf-8")
    subs = {"__CSS__": (STATIC / "app.css").read_text(encoding="utf-8"), "__HEAD__": BP, **subs}
    for k, v in subs.items():
        page = page.replace(k, v)
    left = [m for m in ("__CSS__", "__HEAD__", "__DATA__", "__PDF_BASE__", "__BACK__", "__STATES__") if m in page]
    if left:
        raise ValueError(f"{name}: placeholders not filled: {left}")
    return page


def lei(inline=None):
    return render("lei.html", __DATA__=json.dumps(inline, ensure_ascii=False) if inline else "null")


def app(pdf_base="ficheiros/", back="/expedientes", inline=None):
    return render("app.html", __PDF_BASE__=pdf_base, __BACK__=back, __DATA__=json.dumps(inline, ensure_ascii=False) if inline else "null")


def inbox(rows=None, municipality=""):
    data = json.dumps({"municipio": municipality, "expedientes": rows}, ensure_ascii=False) if rows is not None else "null"
    return render("inbox.html", __DATA__=data, __STATES__=json.dumps(STATES, ensure_ascii=False))
