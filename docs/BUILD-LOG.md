# Build log

- 2026-10-27 scaffold: layout, provenance, assets copied, train_lora.py copied unmodified (re-point before first run).
- 2026-10-27 D0: generator/d0.py → 3 041 train rows / 344 sealed over 553 passages (Annex V, VI, VII; RJUE 9, 11, 23); check_d0.py 0 problems.
- 2026-10-27 generator: pdfgen.py + expedientes.py (57-58 files each, keys, labels) + d1d2.py (D1 element rows, D2 fact rows); sealed 20 expedientes, training 60; modal/reader.py (base or adapter, guided JSON per task), generator/score.py, modal/train_lora.py re-pointed (rounds r1-r3).
- 2026-10-27 base AMALIA on sealed D0 launched on Modal (training/runs/base/).
- 2026-10-27 r1 (D0 v1, 56 steps, 287 s, loss 0.53): sealed D0 v1 = passage id 97 % on transcreve but citacao 1 % — a held-out PASSAGE cannot be
  transcribed by anyone who never saw it; the D0 sealed design was wrong for a memorisation set → D0 v2 (every passage in training, one held-out
  phrasing per task, nao_sei probes on invented ids; reader schema allows {"resposta": "nao_sei"}). r1 on D2: valor 71 % → 57 %, invented 17 → 112:
  training the law alone makes the reader guess more on documents; D2 must be in every mix from the round it is introduced (cumulative, as planned).

## 2026-10-28 03:20 UTC — r4 landed, r5 launched
- r4 (overnight chain): sealed D1 100 %, D2 100 %, D0 elemento_doc 1 % → 98 % (base_legal dropped), proibido answer 56 → 83 %,
  exigido 51 → 59 %; stranger D1 5/11 → 6/11 with 0 false positives (the checklist/list noise worked). Still wrong: the four
  real memórias and the OA minuta, all "not an element". Cause read from the prompts: within 3,500 characters a real memória is
  a cover page + dotted index (looks like the list noise); Valongo opens as a reply to an ofício; the minuta extracts one word
  per line with a preamble. None of those shapes existed in training.
- Stranger key "49 977,00 m2" → "49 977,00" (values carry no unit anywhere in the set); r4 D2 stranger is 7/7 on the fixed key.
- r5 data (training only): cover+index and ofício-reply memórias (50 % long), four title spellings, minuta preamble on 15 % of
  termos, augmentation 45 % with one-word-per-line layout. Chain: training/runs/overnight-r5.sh → training/runs/r5/.
- Report for the morning: docs/REPORT-2026-10-28.md.

## 2026-10-28 07:10 UTC — r5 landed (no stranger gain), cause found by probe, r6 launched
- r5: lab held (D1/D2 100 %, D0 94-100 %); stranger 6/11 (minuta +1, Alcácer list −1, 4 real memórias still "not an element").
- Probe 1 (municipality swap both ways): no effect. Probe 2 (10 ablations × 3 real memórias): only the FILE NAME flips the
  answer — real text under MDARQ-memoria-descritiva.pdf → correct 3/3; generated text under the real name → correct 3/3.
  The training names (slot-stem) and all stranger_name styles leaked the label. D11 recorded in DECISIONS.md.
- r6 data: opaque_name() on 40 % of base D1 rows and 50 % of augmented rows (2,445/6,707 rows), incl. lying names.
- Chain: training/runs/overnight-r6.sh → training/runs/r6/. Third training of the night (hard stop reached after it).

## 2026-10-28 14:30 UTC — r6 landed: stranger 18/18
- r6 attempt 1 died at step 1010/1017 ("Runner terminated") before save; attempt 2 (10:50→14:20 UTC) with checkpoints every
  100 steps. Stranger: 11/11 element, 6/6 quotes, 7/7 facts — the four real memórias, the minuta and the Alcácer list all
  right. Lab held (D1/D2 100 %, D0 95-100 % on passages); elemento_doc tipo 57 → 84 %; exigido 45 % (only column left).
- Lesson of the night (D11): the sealed generated sets could not see the file-name shortcut; only real files with real names
  did. Grow the stranger test to 40-50 files before D3. Night spend ≈ USD 56 (r4 13, r5 14, probes 1, r6 ×2 28).

## 2026-10-28 afternoon — stranger test v2 (44 files), r6 = 27/45, r7 data ready
- 33 new public files (real names kept; 3 dropped for private identifiers); keys in generator/stranger.py; 66 rows.
- r6 on v2: element 27/45 (17 invented), quotes 14/15, facts 18/21. Patterns: documents ABOUT elements called the element
  (13); termos of other procedures called item k/11 (5); speciality memórias typed "drawn" (2); narrative estimate missed (1).
- r7 data: noise_about() 15 kinds + other-procedure termos, 2-5 noise files per expediente, doc_special_memory(),
  doc_estimate() narrative variant. Chain training/runs/overnight-r7.sh awaits approval (≈ USD 14).

## 2026-10-28 evening — prompt audit before r7 (Paulo: "check the prompt, check the data")
- The D1 prompt never defined "is the element": nothing about documents ABOUT elements, termos of other procedures, or how to pick
  escrito/desenhado. D1 prompt v3 adds four rules: (1) the file is the element only when it is the piece itself, filled or blank
  minuta; (2) norms, regulations, posturas, guides, notes, lists, checklists, deliberations, internal notes, instructions, manuals,
  tender specs, project sheets, diagnostics, minutes are not elements; (3) termos of other procedures (utilização, conclusão,
  receção de obras de urbanização, loteamento) are not elements of this request; (4) escrito = text piece even with tables/figures,
  desenhado = drawn piece. Sealed D1 regenerated with v3 (same 1,145 ids and answers; v2 kept as d1-test-v2.jsonl); stranger regenerated.
- Data: every expediente now carries 3-7 noise files (noise share 1.2 % → 7.3 %); norms/manuals/guides have long variants.
- r6 on the v3 prompt without retraining: 26/45 (unchanged) — the adapter was trained without the rules, so the rules only
  count once r7 trains on prompts that carry them.

## 2026-11-02 — prompt v4: every stranger file decided by a written rule
- Applied the rules by hand to all 45 stranger D1 rows: two files no rule named (Cascais regulation annex, Leiria survey
  criteria) and three only implied (OA analysis, Amarante explanatory note, Funchal business memo). Rule 2 now names annexes/
  chapters/articles of regulations, criteria, analyses, opinions, presentations, explanatory notes; rule 1 says the item-9
  memória describes the work of the request and a business/application memória is not an element.
- Generator: noise kinds anexo-regulamento, analise, nota-explicativa, memoria-candidatura; noise files carry real-looking
  names (no OUTDOC prefix — the file-name shortcut on negatives); 12 % of author termos come as blank minutas (rule 1);
  opaque names on half the rows. Negatives now 14 % of D1 rows (was 1.2 % in r6).
- Sealed D1 and stranger regenerated with v4 (same ids and answers). r7 not yet trained: awaiting Modal go (≈ USD 14).
