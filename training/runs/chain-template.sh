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
git add training/expedientes training/data/d1 training/data/d2 && git commit -q -m "Training set for round 6: same expedientes, D1 rows with uninformative file names (40 % base, 50 % augmented)" || true
echo "== train rN $(date -u +%FT%TZ)"
mkdir -p training/runs/rN
$MODAL run modal/train_lora.py --run rN > training/runs/rN/train.log 2>&1 &
TRAIN=$!
# watchdog: if the log stops growing for 15 minutes (the container died: "Runner terminated"), kill the hung client and go on with the last checkpoint
LAST=0; STALL=0
while kill -0 $TRAIN 2>/dev/null; do
  sleep 60; SZ=$(wc -c < training/runs/rN/train.log)
  if [ "$SZ" = "$LAST" ]; then STALL=$((STALL+1)); else STALL=0; LAST=$SZ; fi
  if [ $STALL -ge 15 ]; then echo "!! trainer log stalled 15 min, killing the client $(date -u +%FT%TZ)"; kill $TRAIN; break; fi
done
wait $TRAIN 2>/dev/null
grep -o "'examples': [0-9]*\|'steps': [0-9]*, 'seconds': [0-9.]*\|'checkpoint': [0-9]*" training/runs/rN/train.log | tail -3
$MODAL volume ls amalia-saneamento-lora 2>/dev/null | grep -q "amalia-saneamento-rN" || { echo "!! no rN adapter on the volume, stopping $(date -u +%FT%TZ)"; exit 1; }
echo "== evaluate rN $(date -u +%FT%TZ)"
($MODAL run modal/reader.py --jsonl sealed/d0-test.jsonl --out training/runs/rN/d0.json --lora rN > training/runs/rN/d0.log 2>&1 &)
$MODAL run modal/reader.py --jsonl sealed/d1-test.jsonl --out training/runs/rN/d1.json --lora rN > training/runs/rN/d1.log 2>&1
sleep 30
($MODAL run modal/reader.py --jsonl sealed/d2-test.jsonl --out training/runs/rN/d2.json --lora rN > training/runs/rN/d2.log 2>&1 &)
$MODAL run modal/reader.py --jsonl sealed/stranger-test.jsonl --out training/runs/rN/stranger.json --lora rN > training/runs/rN/stranger.log 2>&1
while pgrep -f "reader.py --jsonl sealed/d" >/dev/null; do sleep 20; done
for s in d0 d1 d2 stranger; do f=$([ $s = stranger ] && echo sealed/stranger-test.jsonl || echo sealed/$s-test.jsonl); [ -f training/runs/rN/$s.json ] && python3 -I generator/score.py --rows $f --answers training/runs/rN/$s.json --record training/runs/rN/SCORES.md | grep "^- " || echo "$s: no answers"; done
git add training/runs/rN && git commit -q -m "Round 6 trained and scored on the sealed sets and the stranger test" || true
echo "== done $(date -u +%FT%TZ)"
