"""Score the verdict layer on the sealed expedientes (sealed/expedientes/*/key.json, frozen before any training).

Each key holds "planted" (the errors the generator put in, each with a type and a target: slot, slots, field) and "always" (the
findings every simulated expediente carries: the DWG that cannot be produced, the signature qualification that cannot be assessed).
Counted per expediente, the exam's way (exam/score.py): found, missed, false alarms (a finding the key does not expect; a
not_assessed, review or not_read item is never an alarm), honest (expected not_assessed items reported as such).

    python3 -I engine/score_sealed.py [--record]      (--record appends to engine/sealed-scores.jsonl and rewrites engine/SCORES-sealed.md)
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine import application as A  # noqa: E402

TARGET_KEYS = ("slot", "slots", "field", "file")


def target_match(target, found):
    keys = [k for k in TARGET_KEYS if k in target]
    if not keys:
        return True
    for k in keys:
        want, got = target[k], found.get(k)
        if k == "slots":
            if set(want) <= set(got or []):
                return True
        elif got == want:
            return True
    return False


def matches(e, f):
    if f.get("status") != e.get("status", "finding"):
        return False
    return f.get("type") == e["type"] and target_match(e.get("target", {}), f)


def score_one(folder):
    key = json.loads((folder / "key.json").read_text(encoding="utf-8"))
    expected = key["planted"] + key["always"]
    found = A.check(folder)
    findings = [e for e in expected if e.get("status", "finding") == "finding"]
    honesty = [e for e in expected if e.get("status") == "not_assessed"]
    hit = [e for e in findings if any(matches(e, f) for f in found)]
    honest = [e for e in honesty if any(matches(e, f) for f in found)]
    # one planted typo, several symptoms (the exam's also_accept): a value_mismatch on the field of a planted impossible_value is the same error seen twice
    typo_fields = {e["target"].get("field") for e in findings if e["type"] == "impossible_value"}
    alarms = [f for f in found if f["status"] == "finding" and not any(matches(e, f) for e in findings)
              and not (f["type"] == "value_mismatch" and f.get("field") in typo_fields)]
    return {"expediente": folder.name, "expected": len(findings), "found": len(hit), "missed": [e["type"] + ":" + json.dumps(e.get("target"), ensure_ascii=False) for e in findings if e not in hit],
            "false_alarms": [f["type"] + ":" + (f.get("file") or f.get("slot") or f.get("rule") or "") for f in alarms],
            "honest": len(honest), "honesty_items": len(honesty),
            "review": sum(1 for f in found if f["status"] == "review"), "not_read": sum(1 for f in found if f["status"] == "not_read"),
            "reader": bool(A.load_reads(folder))}


def main():
    folders = sorted(p for p in (ROOT / "sealed" / "expedientes").iterdir() if p.is_dir() and (p / "key.json").exists())
    rows = [score_one(f) for f in folders]
    tot = {k: sum(r[k] for r in rows) for k in ("expected", "found", "honest", "honesty_items", "review", "not_read")}
    tot["false_alarms"] = sum(len(r["false_alarms"]) for r in rows)
    print("expediente     found/expected  false alarms  honest  review  not read")
    for r in rows:
        print(f"{r['expediente']}   {r['found']}/{r['expected']}            {len(r['false_alarms'])}            {r['honest']}/{r['honesty_items']}     {r['review']}       {r['not_read']}")
        for m in r["missed"]:
            print(f"      missed: {m}")
        for a in r["false_alarms"]:
            print(f"      alarm:  {a}")
    print(f"TOTAL: {tot['found']}/{tot['expected']} findings, {tot['false_alarms']} false alarms, {tot['honest']}/{tot['honesty_items']} honest, "
          f"{tot['review']} review, {tot['not_read']} not read, reader answers on {sum(r['reader'] for r in rows)}/{len(rows)}")
    if "--record" in sys.argv:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        line = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "commit": commit, "expedientes": len(rows), **tot}
        with (ROOT / "engine" / "sealed-scores.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(line, sort_keys=True) + "\n")
        md = ["# Sealed expedientes through the verdict layer", "", f"Run {line['at']}, commit {commit}, reader answers on {sum(r['reader'] for r in rows)}/{len(rows)} folders.", "",
              "| expediente | found/expected | false alarms | honest | review | not read | missed | alarms |", "|---|---|---|---|---|---|---|---|"]
        for r in rows:
            md.append(f"| {r['expediente']} | {r['found']}/{r['expected']} | {len(r['false_alarms'])} | {r['honest']}/{r['honesty_items']} | {r['review']} | {r['not_read']} | "
                      f"{'; '.join(r['missed'])} | {'; '.join(r['false_alarms'])} |")
        md += ["", f"**TOTAL {tot['found']}/{tot['expected']} findings, {tot['false_alarms']} false alarms, {tot['honest']}/{tot['honesty_items']} honest.**", ""]
        (ROOT / "engine" / "SCORES-sealed.md").write_text("\n".join(md), encoding="utf-8")
        print("recorded")


if __name__ == "__main__":
    main()
