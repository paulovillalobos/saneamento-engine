#!/bin/zsh
set -e
cd ~/Downloads/saneamento-engine
PY=/Users/baphomet/Downloads/rjue-engine/.venv/bin/python
MODAL=~/Downloads/foaap-core/.venv-modal/bin/modal
echo "== regenerate training expedientes (80) $(date -u +%FT%TZ)"
rm -rf training/expedientes
$PY -I generator/expedientes.py --n 80 --seed 1 2>&1 | tail -1
echo "== D1/D2 rows with augmentation"
$PY -I generator/d1d2.py --src training/expedientes --out training/data --augment 2>&1 | tail -3
git add training/expedientes training/data/d1 training/data/d2 && git commit -q -m "Training set for round 4: 80 expedientes (long memórias, new noise), D1/D2 rows with augmentation" || true
echo "== train r4 $(date -u +%FT%TZ)"
mkdir -p training/runs/r4
$MODAL run modal/train_lora.py --run r4 > training/runs/r4/train.log 2>&1
grep -o "'examples': [0-9]*\|'steps': [0-9]*, 'seconds': [0-9.]*" training/runs/r4/train.log | tail -2
echo "== evaluate r4 $(date -u +%FT%TZ)"
($MODAL run modal/reader.py --jsonl sealed/d0-test.jsonl --out training/runs/r4/d0.json --lora r4 > training/runs/r4/d0.log 2>&1 &)
$MODAL run modal/reader.py --jsonl sealed/d1-test.jsonl --out training/runs/r4/d1.json --lora r4 > training/runs/r4/d1.log 2>&1
sleep 30
($MODAL run modal/reader.py --jsonl sealed/d2-test.jsonl --out training/runs/r4/d2.json --lora r4 > training/runs/r4/d2.log 2>&1 &)
$MODAL run modal/reader.py --jsonl sealed/stranger-test.jsonl --out training/runs/r4/stranger.json --lora r4 > training/runs/r4/stranger.log 2>&1
while pgrep -f "reader.py --jsonl sealed/d" >/dev/null; do sleep 20; done
for s in d0 d1 d2 stranger; do f=$([ $s = stranger ] && echo sealed/stranger-test.jsonl || echo sealed/$s-test.jsonl); [ -f training/runs/r4/$s.json ] && python3 -I generator/score.py --rows $f --answers training/runs/r4/$s.json --record training/runs/r4/SCORES.md | grep "^- " || echo "$s: no answers"; done
git add training/runs/r4 training/runs/r3 && git commit -q -m "Round 4 trained and scored on the sealed sets and the stranger test" || true
echo "== done $(date -u +%FT%TZ)"
