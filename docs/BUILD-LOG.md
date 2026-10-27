# Build log

- 2026-10-27 scaffold: layout, provenance, assets copied, train_lora.py copied unmodified (re-point before first run).
- 2026-10-27 D0: generator/d0.py → 3 041 train rows / 344 sealed over 553 passages (Annex V, VI, VII; RJUE 9, 11, 23); check_d0.py 0 problems.
- 2026-10-27 generator: pdfgen.py + expedientes.py (57-58 files each, keys, labels) + d1d2.py (D1 element rows, D2 fact rows); sealed 20 expedientes, training 60; modal/reader.py (base or adapter, guided JSON per task), generator/score.py, modal/train_lora.py re-pointed (rounds r1-r3).
- 2026-10-27 base AMALIA on sealed D0 launched on Modal (training/runs/base/).
- 2026-10-27 r1 (D0 v1, 56 steps, 287 s, loss 0.53): sealed D0 v1 = passage id 97 % on transcreve but citacao 1 % — a held-out PASSAGE cannot be
  transcribed by anyone who never saw it; the D0 sealed design was wrong for a memorisation set → D0 v2 (every passage in training, one held-out
  phrasing per task, nao_sei probes on invented ids; reader schema allows {"resposta": "nao_sei"}). r1 on D2: valor 71 % → 57 %, invented 17 → 112:
  training the law alone makes the reader guess more on documents; D2 must be in every mix from the round it is introduced (cumulative, as planned).
