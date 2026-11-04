#!/bin/zsh
set -e
cd ~/Downloads/saneamento-engine
PY=/Users/baphomet/Downloads/rjue-engine/.venv/bin/python
MODAL=~/Downloads/foaap-core/.venv-modal/bin/modal
echo "== regenerate training expedientes (80, D16 whole documents + scaffold-clean keys) $(date -u +%FT%TZ)"
rm -rf training/expedientes
$PY -I generator/expedientes.py --n 80 --seed 1 2>&1 | tail -1
echo "== D1/D2 rows with augmentation"
$PY -I generator/d1d2.py --src training/expedientes --out training/data --augment 2>&1 | tail -3
git add training/expedientes training/data/d1 training/data/d2 && git commit -q -m "Training set for round 10: whole documents (D16), every key inside the scaffold language" || true
echo "== train r10 $(date -u +%FT%TZ)"
mkdir -p training/runs/r10
$MODAL run --detach modal/train_lora.py --run r10 > training/runs/r10/train.log 2>&1 &
TRAIN=$!
# watchdog: if the log stops growing for 25 minutes (32k rows: a step can take minutes) (the container died: "Runner terminated"), kill the hung client and go on with the last checkpoint
LAST=0; STALL=0
while kill -0 $TRAIN 2>/dev/null; do
  sleep 60; SZ=$(wc -c < training/runs/r10/train.log)
  if [ "$SZ" = "$LAST" ]; then STALL=$((STALL+1)); else STALL=0; LAST=$SZ; fi
  if [ $STALL -ge 25 ]; then echo "!! trainer log stalled 25 min, killing the client $(date -u +%FT%TZ)"; kill $TRAIN; break; fi
done
wait $TRAIN 2>/dev/null
grep -o "'examples': [0-9]*\|'steps': [0-9]*, 'seconds': [0-9.]*\|'checkpoint': [0-9]*" training/runs/r10/train.log | tail -3
$MODAL volume ls amalia-saneamento-lora 2>/dev/null | grep -q "amalia-saneamento-r10" || { echo "!! no r10 adapter on the volume, stopping $(date -u +%FT%TZ)"; exit 1; }
echo "== evaluate r10 under the scaffold $(date -u +%FT%TZ)"
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
git add training/runs/r10 && git commit -q -m "Round 10 (whole documents) trained and read under the scaffold: sealed D1/D2 and the stranger test (waves 1-3)" || true
echo "== done $(date -u +%FT%TZ)"
