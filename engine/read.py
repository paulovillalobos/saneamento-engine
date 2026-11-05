"""The reader's part of the verdict layer (D18): the D1 and D2 prompts of one or more expediente folders, read on Modal under the
guard, checked, and stored where engine/application.py finds them.

    python3 -I engine/read.py exam/dossiers/A exam/dossiers/B exam/dossiers/C --lora r11
    python3 -I engine/read.py <folders> --prompts-only          # write the prompts, read nothing (no GPU)

Per folder key (<parent>-<name>): engine/reads/<key>/prompts.jsonl (one row per D1 question = one per PDF with a slot, one per D2
question = the fields engine/cpedi.json lists for the slot) and answers-checked.json (reader.py output through guard.apply, so a
refused answer carries "guard": why). One Modal call for all folders (the model loads once, ≈ 2.5 min); L40S at ≈ USD 1.9/h.
The prompts are the generator's own (generator/d1d2.py): same shortlist, same window, same wording the adapter was trained on.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "generator"))
import guard  # noqa: E402
from generator import d1d2  # noqa: E402
from engine import application as A  # noqa: E402

MODAL = os.environ.get("MODAL", str(Path.home() / "Downloads" / "foaap-core" / ".venv-modal" / "bin" / "modal"))


def prompts(folder):
    key = A.key_of(folder)
    rows = []
    for f in A.inventory(folder):
        if not f["is_pdf"] or not f["slot"] or not f["pages"]:
            continue
        text, shown = d1d2.window(f["pages"])
        rows.append({"id": d1d2.rid("d1", key, f["file"]), "task": "d1_elemento", "expediente": key, "file": f["file"], "slot": f["slot"],
                     "prompt": d1d2.D1_PROMPT.format(shortlist=d1d2.SHORTLIST, name=f["file"], pages=f["n"], shown=shown, text=text)})
        for field in A.fields_of(f["slot"]):
            rows.append({"id": d1d2.rid("d2", key, f["file"], field), "task": "d2_facto", "expediente": key, "file": f["file"], "slot": f["slot"], "field": field,
                         "prompt": d1d2.D2_FACT.format(question=d1d2.QUESTIONS[field], name=f["file"], pages=f["n"], shown=shown, text=text)})
    return key, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", nargs="+")
    ap.add_argument("--lora", default="r11")
    ap.add_argument("--prompts-only", action="store_true")
    a = ap.parse_args()
    out = ROOT / "engine" / "reads"
    out.mkdir(exist_ok=True)
    batch, per = [], {}
    for folder in a.folder:
        key, rows = prompts(folder)
        d = out / key
        d.mkdir(exist_ok=True)
        (d / "prompts.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        per[key] = rows
        batch += rows
        print(f"{key}: {sum(r['task'] == 'd1_elemento' for r in rows)} element questions, {sum(r['task'] == 'd2_facto' for r in rows)} fact questions")
    if a.prompts_only:
        return
    bj, bo = out / "_batch.jsonl", out / "_batch.json"
    bj.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in batch), encoding="utf-8")
    cmd = [MODAL, "run", "modal/reader.py", "--jsonl", str(bj.relative_to(ROOT)), "--out", str(bo.relative_to(ROOT)), "--lora", a.lora, "--guard"]
    print(" ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)
    answers = json.load(open(bo, encoding="utf-8"))
    meta, by_key = answers[0], {o["key"]: o for o in answers[1:]}
    for key, rows in per.items():
        mine = [meta] + [by_key[r["id"]] for r in rows if r["id"] in by_key]
        checked, stats = guard.apply(rows, mine)
        json.dump(checked, open(out / key / "answers-checked.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(key, json.dumps(stats, ensure_ascii=False))
    bj.unlink(); bo.unlink()


if __name__ == "__main__":
    main()
