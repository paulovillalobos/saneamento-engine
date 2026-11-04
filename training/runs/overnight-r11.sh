#!/bin/zsh
# Round 11 (D17): r10 data + the real public documents keyed by hand (training/data/real, repeated 3×). No regeneration: d0/d1/d2 are r10's.
cd ~/Downloads/saneamento-engine
MODAL=~/Downloads/foaap-core/.venv-modal/bin/modal
echo "== train r11 $(date -u +%FT%TZ)"
mkdir -p training/runs/r11
$MODAL run --detach modal/train_lora.py --run r11 > training/runs/r11/train.log 2>&1 &
TRAIN=$!
LAST=0; STALL=0
while kill -0 $TRAIN 2>/dev/null; do
  sleep 60; SZ=$(wc -c < training/runs/r11/train.log)
  if [ "$SZ" = "$LAST" ]; then STALL=$((STALL+1)); else STALL=0; LAST=$SZ; fi
  if [ $STALL -ge 25 ]; then echo "!! trainer log stalled 25 min, killing the client $(date -u +%FT%TZ)"; kill $TRAIN; break; fi
done
wait $TRAIN 2>/dev/null || echo "!! trainer client exited non-zero (timeout or error) $(date -u +%FT%TZ); going on with whatever checkpoint is on the volume"
grep -o "'examples': [0-9]*\|'steps': [0-9]*, 'seconds': [0-9.]*\|'checkpoint': [0-9]*" training/runs/r11/train.log | tail -3
$MODAL volume ls amalia-saneamento-lora 2>/dev/null | grep -q "amalia-saneamento-r11" || { echo "!! no r11 adapter on the volume, stopping $(date -u +%FT%TZ)"; exit 1; }
echo "== evaluate r11 under the scaffold $(date -u +%FT%TZ)"
($MODAL run modal/reader.py --jsonl sealed/d0-test.jsonl --out training/runs/r11/d0.json --lora r11 > training/runs/r11/d0.log 2>&1 &)
$MODAL run modal/reader.py --jsonl sealed/d1-test.jsonl --out training/runs/r11/d1.json --lora r11 --guard > training/runs/r11/d1.log 2>&1
sleep 30
($MODAL run modal/reader.py --jsonl sealed/d2-test.jsonl --out training/runs/r11/d2.json --lora r11 --guard > training/runs/r11/d2.log 2>&1 &)
$MODAL run modal/reader.py --jsonl sealed/stranger-test.jsonl --out training/runs/r11/stranger.json --lora r11 --guard > training/runs/r11/stranger.log 2>&1
while pgrep -f "reader.py --jsonl sealed/d" >/dev/null; do sleep 20; done
for s in d0 d1 d2 stranger; do f=$([ $s = stranger ] && echo sealed/stranger-test.jsonl || echo sealed/$s-test.jsonl); [ -f training/runs/r11/$s.json ] && python3 -I generator/score.py --rows $f --answers training/runs/r11/$s.json --record training/runs/r11/SCORES.md | grep "^- " || echo "$s: no answers"; done
git add training/runs/r11 && git commit -q -m "Round 11 (real documents in the mix) trained and read under the scaffold: sealed D1/D2 and the stranger test (waves 1-3)" || true
echo "== done $(date -u +%FT%TZ)"
