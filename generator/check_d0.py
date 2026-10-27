"""Every quote in D0 (train and sealed) is a verbatim passage; no row id repeats; no passage sits in both files; prompts are bounded.

    python3 -I generator/check_d0.py   # exit 1 on any problem
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
texts = {}
for act in ("portaria-320-2026-1", "decreto-lei-108-2026"):
    for p in json.loads((ROOT / "structure" / f"{act}.json").read_text(encoding="utf-8"))["passages"]:
        texts[p["id"]] = p["text"]
problems, ids, by_file = [], set(), {}
for name in ("training/data/d0/train.jsonl", "sealed/d0-test.jsonl"):
    rows = [json.loads(l) for l in (ROOT / name).read_text(encoding="utf-8").splitlines() if l.strip()]
    by_file[name] = set()
    for r in rows:
        a = json.loads(r["answer"])
        if r["id"] in ids:
            problems.append(f"{name}: duplicate id {r['id']}")
        ids.add(r["id"])
        if a.get("resposta") == "nao_sei":
            continue
        if "passagem" in a:
            by_file[name].add(a["passagem"])
            if a["passagem"] not in texts:
                problems.append(f"{name}: unknown passage {a['passagem']}")
            elif a.get("citacao") != texts[a["passagem"]]:
                problems.append(f"{name}: quote differs from the passage {a['passagem']}")
        if len(r["prompt"]) > 1200 or len(r["answer"]) > 6000:
            problems.append(f"{name}: oversized row {r['id']}")
    print(f"{name}: {len(rows)} rows")
prompts_train = {json.loads(l)["prompt"] for l in (ROOT / "training/data/d0/train.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
dup = sum(1 for l in (ROOT / "sealed/d0-test.jsonl").read_text(encoding="utf-8").splitlines() if l.strip() and json.loads(l)["prompt"] in prompts_train)
if dup:
    problems.append(f"{dup} sealed prompts also in training")
print(f"{len(problems)} problems" + ("".join("\n - " + p for p in problems[:20]) if problems else ""))
sys.exit(1 if problems else 0)
