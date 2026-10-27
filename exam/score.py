"""Score the engine on the exam (exam/answers.json).

The engine is expected to expose engine/application.py with
    check(dossier_dir) -> list of {"status": "finding" | "not_assessed", "type": ...,
                                   "slot"?, "file"?, "field"?, "rule"?, "law_ref"?, "quote"?}

Counted per dossier:
    found        expected findings the engine reported (same type and target, or an accepted symptom)
    missed       expected findings it did not report
    false alarms findings it reported that the answer key does not expect
    honest       expected "not_assessed" items it reported as not_assessed (it must not guess)
Provisional items are reported but never scored.

usage: python3 exam/score.py [--record]   (--record appends the result to exam/scores.jsonl)
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAM = ROOT / "exam"
sys.path.insert(0, str(ROOT))
TARGET_KEYS = ("slot", "file", "field", "rule")


def engine():
    try:
        from engine import application
        return application
    except ImportError:
        return None


def target_match(expected_target, found):
    keys = [k for k in TARGET_KEYS if k in expected_target]
    if not keys:
        return True  # targets like "all signed files" are matched by type alone
    return any(found.get(k) == expected_target[k] for k in keys)


def matches(e, f):
    if f.get("status") != e["status"]:
        return False
    if f.get("type") == e["type"] and target_match(e["target"], f):
        return True
    return any(f.get("type") == alt["type"] and f.get("field") == alt.get("field") for alt in e.get("also_accept", []))


def score_dossier(expected, found):
    findings = [e for e in expected if e["status"] == "finding"]
    honesty = [e for e in expected if e["status"] == "not_assessed"]
    provisional = [e for e in expected if e["status"] == "provisional"]
    if found is None:
        return {"found": 0, "expected": len(findings), "false_alarms": 0, "honest": 0, "honesty_items": len(honesty),
                "provisional": len(provisional), "missed": [e["id"] for e in findings], "ran": False}
    hit = [e for e in findings if any(matches(e, f) for f in found)]
    honest = [e for e in honesty if any(matches(e, f) for f in found)]
    provisional_types = {e["type"] for e in provisional}
    alarms = [f for f in found if f.get("status") == "finding" and f.get("type") not in provisional_types
              and not any(matches(e, f) for e in findings)]
    return {"found": len(hit), "expected": len(findings), "false_alarms": len(alarms), "honest": len(honest),
            "honesty_items": len(honesty), "provisional": len(provisional),
            "missed": [e["id"] for e in findings if e not in hit], "alarms": alarms, "ran": True}


def main():
    answers = json.loads((EXAM / "answers.json").read_text(encoding="utf-8"))
    app = engine()
    results = {}
    for name, expected in answers["dossiers"].items():
        found = app.check(EXAM / "dossiers" / name) if app else None
        results[name] = score_dossier(expected, found)
    total_found = sum(r["found"] for r in results.values())
    total_expected = sum(r["expected"] for r in results.values())
    total_alarms = sum(r["false_alarms"] for r in results.values())
    total_honest = sum(r["honest"] for r in results.values())
    total_honesty = sum(r["honesty_items"] for r in results.values())
    print("dossier  found/expected  false alarms  honest (not_assessed)  provisional (not scored)")
    for name, r in results.items():
        print(f"   {name}        {r['found']}/{r['expected']}            {r['false_alarms']}              "
              f"{r['honest']}/{r['honesty_items']}                    {r['provisional']}")
        if r["missed"]:
            print(f"            missed: {', '.join(r['missed'])}")
    print(f"TOTAL: {total_found}/{total_expected} findings, {total_alarms} false alarms, "
          f"{total_honest}/{total_honesty} honest not-assessed")
    if app is None:
        print("The engine cannot read applications yet (no engine/application.py), so every item counts as missed.")
    if "--record" in sys.argv:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        line = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "commit": commit, "exam": answers["version"],
                "engine_ran": app is not None, "found": total_found, "expected": total_expected,
                "false_alarms": total_alarms, "honest": total_honest, "honesty_items": total_honesty}
        with (EXAM / "scores.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(line, sort_keys=True) + "\n")
        print("recorded in exam/scores.jsonl")


if __name__ == "__main__":
    main()
