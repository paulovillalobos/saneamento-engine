#!/bin/zsh
set -e
cd ~/Downloads/saneamento-engine
PY=/Users/baphomet/Downloads/rjue-engine/.venv/bin/python
MODAL=~/Downloads/foaap-core/.venv-modal/bin/modal
echo "== regenerate training expedientes (80, D14 window + scaffold-clean keys) $(date -u +%FT%TZ)"
rm -rf training/expedientes
$PY -I generator/expedientes.py --n 80 --seed 1 2>&1 | tail -1
echo "== D1/D2 rows with augmentation"
$PY -I generator/d1d2.py --src training/expedientes --out training/data --augment 2>&1 | tail -3
git add training/expedientes training/data/d1 training/data/d2 && git commit -q -m "Training set for round 9: every key inside the scaffold language (D13), 11k window with signal pages (D14), memória cost/prazo on later pages, days-vs-months, index and opinion noise" || true
echo "== train r9 $(date -u +%FT%TZ)"
mkdir -p training/runs/r9
$MODAL run --detach modal/train_lora.py --run r9 > training/runs/r9/train.log 2>&1 &
TRAIN=$!
# watchdog: if the log stops growing for 15 minutes (the container died: "Runner terminated"), kill the hung client and go on with the last checkpoint
LAST=0; STALL=0
while kill -0 $TRAIN 2>/dev/null; do
  sleep 60; SZ=$(wc -c < training/runs/r9/train.log)
  if [ "$SZ" = "$LAST" ]; then STALL=$((STALL+1)); else STALL=0; LAST=$SZ; fi
  if [ $STALL -ge 15 ]; then echo "!! trainer log stalled 15 min, killing the client $(date -u +%FT%TZ)"; kill $TRAIN; break; fi
done
wait $TRAIN 2>/dev/null
grep -o "'examples': [0-9]*\|'steps': [0-9]*, 'seconds': [0-9.]*\|'checkpoint': [0-9]*" training/runs/r9/train.log | tail -3
$MODAL volume ls amalia-saneamento-lora 2>/dev/null | grep -q "amalia-saneamento-r9" || { echo "!! no r9 adapter on the volume, stopping $(date -u +%FT%TZ)"; exit 1; }
echo "== evaluate r9 under the scaffold $(date -u +%FT%TZ)"
($MODAL run modal/reader.py --jsonl sealed/d0-test.jsonl --out training/runs/r9/d0.json --lora r9 > training/runs/r9/d0.log 2>&1 &)
$MODAL run modal/reader.py --jsonl sealed/d1-test.jsonl --out training/runs/r9/d1.json --lora r9 --guard > training/runs/r9/d1.log 2>&1
sleep 30
($MODAL run modal/reader.py --jsonl sealed/d2-test.jsonl --out training/runs/r9/d2.json --lora r9 --guard > training/runs/r9/d2.log 2>&1 &)
$MODAL run modal/reader.py --jsonl sealed/stranger-test.jsonl --out training/runs/r9/stranger.json --lora r9 --guard > training/runs/r9/stranger.log 2>&1
while pgrep -f "reader.py --jsonl sealed/d" >/dev/null; do sleep 20; done
echo "== r8 under the scaffold, on the r8-window rows (baseline; stranger limited to waves 1-2) $(date -u +%FT%TZ)"
mkdir -p training/runs/r8-guard
($MODAL run modal/reader.py --jsonl sealed/d2-test-r8.jsonl --out training/runs/r8-guard/d2.json --lora r8 --guard > training/runs/r8-guard/d2.log 2>&1 &)
$MODAL run modal/reader.py --jsonl sealed/stranger-test-r8.jsonl --out training/runs/r8-guard/stranger.json --lora r8 --guard --limit 66 > training/runs/r8-guard/stranger.log 2>&1
while pgrep -f "reader.py --jsonl sealed/d2-test-r8" >/dev/null; do sleep 20; done
for s in d0 d1 d2 stranger; do f=$([ $s = stranger ] && echo sealed/stranger-test.jsonl || echo sealed/$s-test.jsonl); [ -f training/runs/r9/$s.json ] && python3 -I generator/score.py --rows $f --answers training/runs/r9/$s.json --record training/runs/r9/SCORES.md | grep "^- " || echo "$s: no answers"; done
for s in d2 stranger; do f=$([ $s = stranger ] && echo sealed/stranger-test-r8.jsonl || echo sealed/d2-test-r8.jsonl); [ -f training/runs/r8-guard/$s.json ] && python3 -I generator/score.py --rows $f --answers training/runs/r8-guard/$s.json --record training/runs/r8-guard/SCORES.md | grep "^- " || echo "r8-guard $s: no answers"; done
git add training/runs/r9 && git commit -q -m "Round 9 trained and read under the scaffold: sealed D1/D2 and the stranger test (waves 1-3)" || true
echo "== done $(date -u +%FT%TZ)"
