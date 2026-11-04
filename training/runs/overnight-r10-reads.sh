#!/bin/zsh
# Reads for round 10: the training function hit Modal's 6 h timeout at step ~1035/~1050; the step-1000 checkpoint on the volume is the r10 adapter.
cd ~/Downloads/saneamento-engine
MODAL=~/Downloads/foaap-core/.venv-modal/bin/modal
echo "== evaluate r10 (step-1000 checkpoint) under the scaffold $(date -u +%FT%TZ)"
($MODAL run modal/reader.py --jsonl sealed/d0-test.jsonl --out training/runs/r10/d0.json --lora r10 > training/runs/r10/d0.log 2>&1 &)
$MODAL run modal/reader.py --jsonl sealed/d1-test.jsonl --out training/runs/r10/d1.json --lora r10 --guard > training/runs/r10/d1.log 2>&1
sleep 30
($MODAL run modal/reader.py --jsonl sealed/d2-test.jsonl --out training/runs/r10/d2.json --lora r10 --guard > training/runs/r10/d2.log 2>&1 &)
$MODAL run modal/reader.py --jsonl sealed/stranger-test.jsonl --out training/runs/r10/stranger.json --lora r10 --guard > training/runs/r10/stranger.log 2>&1
while pgrep -f "reader.py --jsonl sealed/d" >/dev/null; do sleep 20; done
echo "== r9 under the scaffold on the whole-document stranger rows (baseline: the view alone) $(date -u +%FT%TZ)"
mkdir -p training/runs/r9-whole
$MODAL run modal/reader.py --jsonl sealed/stranger-test.jsonl --out training/runs/r9-whole/stranger.json --lora r9 --guard > training/runs/r9-whole/stranger.log 2>&1
for s in d0 d1 d2 stranger; do f=$([ $s = stranger ] && echo sealed/stranger-test.jsonl || echo sealed/$s-test.jsonl); [ -f training/runs/r10/$s.json ] && python3 -I generator/score.py --rows $f --answers training/runs/r10/$s.json --record training/runs/r10/SCORES.md | grep "^- " || echo "$s: no answers"; done
[ -f training/runs/r9-whole/stranger.json ] && python3 -I generator/score.py --rows sealed/stranger-test.jsonl --answers training/runs/r9-whole/stranger.json --record training/runs/r9-whole/SCORES.md | grep "^- " || echo "r9-whole: no answers"
echo "== done $(date -u +%FT%TZ)"
