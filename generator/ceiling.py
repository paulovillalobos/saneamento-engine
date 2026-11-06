"""The ceiling: a large general model reads the SAME stranger rows with the WHOLE document (every page, uncut, in order), no
training, no window. Its score is what these 106 real rows allow; the gap between it and AMALIA is ours to close, the rest is
the documents.

    python -I generator/ceiling.py build --tag whole      # -> training/runs/ceiling-whole/prompts/<id>.txt + index.json
    (the readers write training/runs/ceiling-whole/raw/<id>.json = {"text": "<the JSON answer>"} ; they see prompts/ only)
    python -I generator/ceiling.py collect --tag whole    # -> stranger.json (reader format), stranger-checked.json (scaffold checker), SCORES

The prompts are the generator's own D1/D2 templates (generator/d1d2.py), so the ceiling answers the same question in the same
shape as the adapters; only the text differs: all pages. The keys stay where they are (sealed/stranger-test.jsonl); the
readers never see them.
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "generator" / f"{name}.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def whole(pages):
    """Every page, uncut, in order, in the same «[página n]» blocks the window uses; no header note (all pages are shown)."""
    return "\n".join(f"[página {i + 1}]\n{t}" for i, t in enumerate(pages)), ""


def build(tag):
    S = load("stranger"); M = S.M
    from pypdf import PdfReader
    out = ROOT / "training" / "runs" / f"ceiling-{tag}"; (out / "prompts").mkdir(parents=True, exist_ok=True); (out / "raw").mkdir(exist_ok=True)
    index, chars = [], 0
    for path, elem, tipo, facts, note in S.KEYS:
        pages = [(p.extract_text() or "").strip() for p in PdfReader(str(ROOT / path)).pages]
        text, shown = whole(pages); name = Path(path).name
        rows = [(f"d1:{S.rid('stranger', name)}", "d1_elemento", M.D1_PROMPT.format(shortlist=M.SHORTLIST, name=name, pages=len(pages), shown=shown, text=text))]
        for field, value in facts:
            rows.append((f"d2:{S.rid('stranger', name, field)}", "d2_facto", M.D2_FACT.format(question=M.QUESTIONS[field], name=name, pages=len(pages), shown=shown, text=text)))
        for rid, task, prompt in rows:
            (out / "prompts" / f"{rid.replace(':', '-')}.txt").write_text(prompt, encoding="utf-8")
            index.append({"id": rid, "task": task, "file": name, "pages": len(pages), "chars": len(prompt)}); chars += len(prompt)
    (out / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{out.relative_to(ROOT)}: {len(index)} prompts, {chars:,} chars (≈ {chars // 3:,} tokens), max {max(i['chars'] for i in index):,} chars")


def normalise(task, obj):
    if task == "d1_elemento":
        o = {"elemento": obj.get("elemento"), "citacao": obj.get("citacao", "") or "", "tipo": obj.get("tipo")}
        if o["elemento"] is None and o["tipo"] not in ("nao_e_elemento", "ilegivel"):
            o["tipo"] = "nao_e_elemento"
        if o["elemento"] is None:
            o["citacao"] = ""
    else:
        o = {"valor": obj.get("valor"), "pagina": obj.get("pagina"), "citacao": obj.get("citacao", "") or ""}
        if o["valor"] is None:
            o = {"valor": None, "pagina": None, "citacao": ""}
    return json.dumps(o, ensure_ascii=False)


def collect(tag, model):
    guard = load("guard")
    out = ROOT / "training" / "runs" / f"ceiling-{tag}"
    index = json.loads((out / "index.json").read_text(encoding="utf-8"))
    rows, missing, bad = [{"meta": {"model": model, "adapter": None, "whole_document": True, "answered": 0, "skipped": 0, "load_s": 0, "gen_s": 0}}], [], []
    for it in index:
        f = out / "raw" / f"{it['id'].replace(':', '-')}.json"
        if not f.exists():
            missing.append(it["id"]); continue
        raw = json.loads(f.read_text(encoding="utf-8"))
        text = raw["text"] if isinstance(raw, dict) and "text" in raw and isinstance(raw["text"], str) else json.dumps(raw, ensure_ascii=False)
        try:
            obj = json.loads(text)
            text = normalise(it["task"], obj)
        except Exception:
            bad.append(it["id"])
        rows.append({"key": it["id"], "task": it["task"], "prompt_tokens": it["chars"] // 3, "completion_tokens": 0, "finish_reason": "stop", "text": text})
    rows[0]["meta"]["answered"] = len(rows) - 1
    (out / "stranger.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    checked = [rows[0]]
    for r in rows[1:]:
        prompt = (out / "prompts" / f"{r['key'].replace(':', '-')}.txt").read_text(encoding="utf-8")
        why = guard.check(r["task"], prompt, r["text"])
        checked.append({**r, **({"guard": why} if why else {})})
    (out / "stranger-checked.json").write_text(json.dumps(checked, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"answers {len(rows) - 1}/{len(index)}; missing {len(missing)}; not JSON {len(bad)} {bad[:5]}; refused by the checker {sum('guard' in c for c in checked[1:])}")
    for c in checked[1:]:
        if "guard" in c:
            print("  refused", c["key"], c["guard"], c["text"][:140])
    if missing:
        print("  missing:", *missing[:10])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "collect"]); ap.add_argument("--tag", default="whole"); ap.add_argument("--model", default="general-purpose-model")
    a = ap.parse_args()
    build(a.tag) if a.cmd == "build" else collect(a.tag, a.model)
