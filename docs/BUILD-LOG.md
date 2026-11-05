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

## 2026-11-03 — round 7 (00:32–04:51 UTC, third attempt): stranger 39/45, no invented element, six real pieces rejected
- Attempt 1 died with the session at step 220 (≈ USD 3); attempt 2 refused because the stale checkpoint sat where the adapter goes
  (volume rm, no GPU cost); attempt 3 ran detached (modal run --detach, Python start_new_session): 1,137 steps, 4.1 h, ≈ USD 16.
- Stranger (44 files): element 39/45 (r6 27/45), invented 17 → 0, rejected real pieces 0 → 6: the four loteamento memórias
  (Valongo, Cascais ×3), the OA coordinator blank minuta, the Caxinas estimate letter. Facts 17/21 (two invented values on noise
  files: "custo elegível" of a funding sheet, a clause number of a tender spec; two near-misses). Sealed D1 1135/1145 (10 ITED
  projects called item 9 — the sealed ITED doc is the old plain shape), D2 100 %, D0 passages 90-100 %, exigido 39 %.
- D12 (docs/DECISIONS.md): D1 names the piece, D3 checks the fit; only termos are procedure-specific. Prompt v5 (rules 1 and 3);
  sealed D1 (v4 kept as d1-test-v4.jsonl) and stranger regenerated with the same ids and answers.
- r8 data: 30 % of long memórias headed by another operation (alvará de loteamento, DLOT lines, município as requerente) still
  labelled item 9; coordinator blank minuta 12 %; estimate as the architects' letter (areas per space, cost per m2, total);
  D2 questions asked of noise files answered null (50 % of noise files). Chain training/runs/overnight-r8.sh ready — needs go (≈ USD 15).

## 2026-11-03 — round 8 (12:05–16:26 UTC, first attempt, ≈ USD 16): stranger 42/45, facts 19/21, sealed D1/D2 100 %
- Back: 4 loteamento memórias (D12), OA coordinator blank minuta; noise-file facts now null. Left: OA conclusion termo → 27.k,
  forest-defence element list → item 9 (both right in r7), Caxinas estimate letter still rejected (no total within the window).
- Gate "≥ 42/45 → D3" met. Next: D3 verdict + convite (code), next round only when D3 needs it.

## 2026-11-03 evening — fresh batch (wave 3, 32 files nobody tuned on): 27/32, one invented fact with a fabricated quote
- 32 new public files (14 new municipalities + OE + Azores civil protection), 15 candidates dropped for private identifiers; keys committed
  c3ae780 before any output; second keyer (fresh Claude agent, no access to keys/scores; Codex blocked by the permission layer) agrees 31/32.
- r8 adapter, scored once: element 27/32 (24/26 unambiguous, 28/32 on the second keys), invented 1 (index of drawings → plantas), rejected 2
  (bench detail sheet, priced bill of quantities — both ambiguous), two memórias with structure chapters in the index → estabilidade (window).
- Facts 6/8: the Nazaré memória cost "1 888 000,00 €" with a quoted sentence that is not in the document (first fabricated fact on a real
  file; the quote-in-text guard catches it); Moimenta "90" dias given as months.
- Old 44 files unchanged in the same run (42/45, 19/21). Wave 3 stays held out; r9 plan in the report. Spend: ≈ USD 1.

## 2026-11-03 night — D13 hard scaffold (no round 9): generator/guard.py, reader --guard, checker over r8's answers
- generator/guard.py (stdlib): grammar_for(task, prompt) → xgrammar EBNF from the prompt alone (shortlist lines, «[página n]»
  blocks); check(task, prompt, text) → None or why not; CLI marks a finished run's answers "guard": why. generator/test_guard.py:
  2 399 keys (sealed D1/D2 + stranger) all inside the language, 9 bad shapes refused. Grammar size 75 B – 86 KB (D1 carries 43 law texts).
- modal/reader.py --guard: builds the grammar locally, decoder gets StructuredOutputsParams(grammar=…), xgrammar backend; meta "guard".
- generator/score.py: "guard" answers = recusado, wrong in every field (denominators kept).
- The checker over r8's existing answers (no GPU): sealed D1 0/1 145 refused; sealed D2 75/1 148 refused — 56 quotes copied
  from the generator's own cut-mid-word window («omunicação prévia…», « da obra, baseada…»: the model learned the key's
  artefact), 19 small-integer facts (pisos, fogos: «1», «3») whose quote is a random line holding that digit — both are
  DATA DEBTS of generator/d1d2.py line_with(), to fix before any next round. Stranger 44: 2/21 refused (an ellipsis «...»
  in a value; a case change «Estrutura Residencial» for «ESTRUTURA RESIDENCIAL») = the two facts r8 already had wrong.
  Wave 3: 6/29 refused — Nazaré «1 888 000,00 €» page 5 (pages 1–4 shown) and Moimenta «90» page 3 (pages 1–2 shown; the
  phrase is on page 1): both fabrications caught by the page alone; Santiago right value, page 3 for page 2; Vagos right
  value, «****» inserted in the quote; plus the two above. Under the grammar none of the six can be written as they were.
- Next (needs the go, ≈ USD 1–2, one container): read sealed D1/D2 + stranger 44 + wave 3 with r8 --guard → training/runs/r8-guard/.
  That is wave 3's second and last scoring (the product reader is the guarded one). No training.

## 2026-11-03 night — round 9 prepared: scaffold from the start (D14)
- Finding: 77 of 4 601 r8 training fact rows had keys outside the window (38 pages never shown, 39 values cut) → trained fabrication of pages.
- generator/d1d2.py: window() 11 000 chars (2 head pages, densest signal pages, rest), quote_for() aligned quotes, guard.check() gate on every
  row (dropped rows listed), ABSENT by field (memória cost/prazo hard negatives). expedientes.py: memória cost (30 % of long) and prazo in
  months / days, noise «indice-pecas» ×2 and «parecer-externo». stranger.py uses the same window and quote. guard.py header regex.
- Sealed rows regenerated (D1 1 145, D2 1 190; r8-window copies kept as *-r8.jsonl), stranger regenerated (106 rows, keys unchanged);
  test_guard: 2 441 keys inside the language. 12-expediente sample: D1 prompt mean 11.3k chars (max 20.7k), 2 of 601 fact rows dropped.
- modal/train_lora.py RUNS r9; training/runs/overnight-r9.sh: regenerate 80 expedientes → train → r9 reads with --guard (D0 schema) →
  r8 --guard baseline on the r8-window rows → scores. Expected ≈ USD 20–25 (longer rows than r8's 4.1 h).

## 2026-11-04 01:25 UTC — round 9 done first attempt (≈ USD 18, spend to date ≈ USD 110)
- Chain overnight-r9.sh: regen 80 expedientes (4 930 files, D1 7 098 rows, D2 4 718 rows, 17 keys dropped by the gate) → train r9
  (H100 4.1 h, 1 154 steps, 15 227 examples, ckpt 1100) → reads with --guard (d0 schema): sealed D1 1 145/1 145, D2 1 190/1 190 value+page,
  quote holds value 1 035/1 035; stranger 106: elements 61/77 (waves 1-2 34/45, wave 3 27/32), facts 27/29 (26/29 after the checker).
- Checker over the guarded answers (guard.py CLI → *-checked.json): r9 sealed 0 refused; r9 stranger 2 refused (OA termo "…" value;
  Lagos 1.900,00 quoted from another sentence of the right page). r8-guard sealed D2: 53 refused (the cut-mid-word quotes), stranger 0.
- Wave 3 second and last scoring = r9 under the scaffold: 34/40 (r8 free was 32/40); facts 7/8 with ZERO fabricated values/pages/quotes;
  elements 27/32 (Amadora 34-page memória → null; Setúbal author termo → null; Nazaré bench sheet, Vagos LPU ambiguous; Marinha Grande
  quantities map → planta de cedências invented).
- Regression found: elements on the 44 tuned files 42 → 34. Shape: long real memórias (Cascais 23–30 pp) shown as pages 1, 2 + five dense
  middle pages → "not an element"; five about-element docs (ANEPC note, Leiria annex, Maia survey, Seixal postura, OA fiscalização termo)
  called the element again. Cause = the D14 window view, not the scaffold. No change to any key.
- Chain bug fixed for the record: overnight-r9.sh line 40 committed the outputs with the round-8 message; HEAD amended.
- Next (no training, ≈ USD 2): head-whole + signal-pages view, read the 44 files with r8 and r9 under the scaffold, keep the better pair; then D3.

## 2026-11-04 morning — the ceiling (Claude Opus 5.5, whole documents, 11 readers, no GPU) + OCR step + scorer D15
- generator/ceiling.py build/collect: 106 whole-document prompts (2.77 M chars ≈ 0.92 M tokens, max 103 k chars), answers in
  training/runs/ceiling-opus/raw/, collected to stranger.json + stranger-checked.json (checker refused 0), SCORES.md.
  Result: elements 76/77 (miss: IPCB student memória → null, defensible), facts 27/29 unit-tolerant (OA wording copied short;
  Valpaços «lar de idosos» p4 for the capitalised use of p1), wave 3 40/40. Agreed with the key on every row the keyers called ambiguous.
- generator/score.py val(): value compared without a trailing unit (m2/m²/€). Rescored: r8 free 69/77 + 23/29, r9 scaffold
  61/77 + 25/29, ceiling 76/77 + 27/29. Wave 3 all rows: r8 32, r9 34, ceiling 40 of 40.
- Key corrected (wave 1, tuned): Valongo custo_total → «2.125.000€» p4; sealed/stranger-test.jsonl regenerated (prompts unchanged,
  1 answer changed), stranger-test-r8.jsonl patched. r9 loses that row (said null), r8 too.
- generator/ocr.py + stranger.py reads through it; brew tesseract + tesseract-lang (por) + ocrmypdf installed. Corpus: 8 text-less
  pages in 6 files, 0 recovered (blank/image covers). No scanned document in the test today.
- Base model fact checked: AMALIA-9B config = LlamaForCausalLM, max_position_embeddings 32768, rope_theta 1e6. The 8,192 was ours.
- Cost: USD 0 on Modal; the ceiling ran on the Claude subscription (≈ 2 M tokens).

## 2026-11-04 13:30 UTC — round 10 prepared and launched: whole documents (D16)
- generator/d1d2.py window(): whole document, 65 000-char budget, pages past it dropped with the header note. generator/expedientes.py:
  stretch() + MEM_CHAPTERS / REG_TEMPLATES / REG_HEADINGS; long memórias 6–24 pp (facts in the second half), speciality memórias 4–16 pp,
  40 % of noise 5–30 pp with repeated letterheads. modal/train_lora.py RUNS r10 hp max_len/tokens_per_batch 32 768.
- Sealed D1/D2 rows regenerated whole (1 145 / 1 190, 0 dropped), stranger regenerated (106; 2 rows lose last pages: Mesão Frio aviso,
  Alcácer list), r9-view copies kept as sealed/*-r9.jsonl; test_guard ok. Smoke --guard r9 on the 6 longest rows: grammars up to 650 KB
  compile, 6/6 answered, 21.5 s generate; r9 on whole documents answers inside the language but wrong on the Valpaços use (trained on short docs).
- Chain training/runs/overnight-r10.sh: regen 80 (seed 1) → d1d2 --augment → commit → train r10 (watchdog 25 min) → r10 reads --guard
  (d0 schema) → r9 --guard on the whole-document stranger rows (baseline) → scores → commit. Log training/runs/overnight-r10.log.

## 2026-11-04 — round 10 training hit the 6 h wall; reads launched from the step-1000 checkpoint
- Claude: the r10 trainer (whole documents, max_len 32 768) ran 525 steps per epoch; Modal's function timeout (6 h) killed it at step ~1035 of ~1050, 21 463 s in. The step-1000 checkpoint (saved every 100 steps since r6) is on the volume as amalia-saneamento-r10. Linear decay to 0: at step 1000 the learning rate was ≈ 5 % of peak, so the lost 50 steps change the adapter very little. Taken as round 10, stated as such in the report.
- Claude: training cost ≈ 6.0 h H100 ≈ USD 24. Timeout raised to 12 h in modal/train_lora.py for the next run.
- Claude: the chain script stopped at the failed `wait` (set -e) before the reads. Reads launched separately with training/runs/overnight-r10-reads.sh (d0, d1 --guard, d2 --guard, stranger --guard, then r9 --guard on the whole-document stranger rows into r9-whole, then score.py).

## 2026-11-04 19:35 UTC — round 10 read and scored
- Claude: reads done in 16 min (d0, d1 --guard, d2 --guard, stranger --guard; r9 --guard on the whole-document stranger rows → training/runs/r9-whole/).
  Checker (guard.py CLI) over every output → *-checked.json: sealed D1/D2 0 refused; stranger r10 2 refused (Valongo area, Lagos area: right value, quote from another sentence); r9-whole 3 refused.
- Claude: sealed D1 1145/1145, D2 1190/1190 value + page + quote. Stranger (whole documents): r10 elements 67/77 (waves 1–2 41/45, wave 3 26/32), facts 25/29, wave 3 total 33/40, fabricated 0;
  r9 on the same whole view 59/77, 24/29, 33/40; ceiling 76/77, 27/29, 40/40. r10 right where r9-whole wrong: 13 rows; the reverse: 4.
- Claude: per-wave comparison script kept in the scratchpad only (one-off); numbers in the report. MANIFEST.json for r10 written by hand from train.log (trainer writes it only on a clean finish).
- Claude: cost: training 6.0 h H100 ≈ USD 24 + reads ≈ USD 1 = ≈ USD 25 (estimate was 30–45). To date ≈ USD 135.
- Paulo: decide the next data step (real-document TRAINING collection, work not money) and whether a round 11 on it (≈ USD 25) gets the go.

## 2026-11-04 evening — real-document TRAINING collection (D17)
- Claude: six parallel searches by shape (general memórias; speciality memórias; quantities and prices; about-element documents; tender packages; small pieces), municipalities of the test excluded. 4 download batches (fetch helper, %PDF check, page count): 117 files landed, Coimbra refused (WAF 403).
- Claude: generator/privacy.py written (number classes by first digit + phone context, ID words, personal e-mail, professional numbers); scan → 3 files dropped for a private person's data, 3 for unreadable text/scans. 111 kept (a last batch of 5 from the tender-package search, whose finding was that works packages sit behind e-procurement logins).
- Claude: generator/realtrain.py written (KEYS by hand → rows with the whole-document view and the scaffold gate; sha256 test guard; INDEX.md). 563 rows, 0 dropped. sources/real/PROVENANCE.md train section with every URL.
- Claude: train_lora.py r11 run (sets d0,d1,d2,real; real ×3), training/runs/overnight-r11.sh ready. Cost so far USD 0.
- Paulo: the go for round 11 (≈ USD 25-30).


## 2026-11-04 23:25 UTC — round 11 launched (commit f2d3090)
- Paulo: "go, run round 11 with weight 6".
- Claude: real set repeated 6× (≈ 3,400 of ≈ 15,000 examples; about half of the element rows). Sentence pool of the generated memórias moved from sources/real/memorias (the four wave-1 TEST memórias, a mild leak of test text into training since round 9) to the 39 memórias of the training collection (3,218 sentences); 80 expedientes regenerated. Chain training/runs/overnight-r11.sh: regen → rows → commit → train r11 (12 h limit) → guarded reads → score → commit. Log training/runs/overnight-r11.log, pid training/runs/r11.pid. Expected ≈ USD 25-30, results ≈ 06:30-07:30 UTC.

## 2026-11-05 10:45 UTC — round 11 done (chain commit 197ded8 + this commit)
- Claude: training finished clean at 10:33 UTC: 1,379 steps, 2 epochs, 11.0 h H100 ≈ USD 43.5 (estimate was 25-30: the real rows are long, 29 s/step vs 21). Reads --guard d0/d1/d2/stranger ≈ USD 1. Total to date ≈ USD 180.
- Claude: checker (guard.py CLI) over every output → *-checked.json: 0 refused anywhere. Per-wave table in training/runs/r11/SCORES.md.
- Claude: stranger elements 74/77 (r10 67, ceiling 76); wave 3 30/32 (r10 26); the four about-element false positives gone; invented 0, fabricated 0. Facts 22/29 (r10 25): six values the documents hold answered null.
- Claude: cause of the fact drop = my data: training/data/real/train.jsonl D2 rows are 229 null vs 1 value (realtrain.py: two absent questions per document, almost no keyed values) ×6 = 1,374 "not present" fact rows. Elements had the test's proportion and gained.
- Claude: report section "Round 11" + "Next (after round 11)", D17 outcome, memory.
- Paulo: decide round 12 on the corrected real set (≈ USD 44 at weight 6, ≈ 25 at weight 3). Fixing the rows costs USD 0 and comes first.

## 2026-11-05 13:30 UTC — D17 fix: real fact rows rebalanced, round 12 chain ready
- Paulo: "fix what makes it go wrong".
- Claude: text of the 111 PDFs dumped; four parallel readers over the 44 element documents (11 fields each) → every declared value with page and line; I kept 20 values printed as whole tokens (two priced-bill totals, Peniche electrical estimate 30 683,21 €, Angra market quadro sinóptico 6 values, Melgaço/Sabugal/Angra terrain areas, uses), 8 traps (Madeira 720 dias, Viana 24-month plan deadline ×2, empty price columns), dropped Póvoa de Lanhoso (OCR without spaces) and Peniche fogos (jumbled table). Short values pinned to their page (Melgaço 17 was quoted from p2 "17 d." in round 11 — fixed).
- Claude: realtrain.py — one absent question, only on documents that state a value. Real set 376 rows: 333 D1, 42 D2 = 20 values : 22 null (round 11: 1 : 229).
- Claude: train_lora.py RUNS r12 (= r11 recipe), training/runs/overnight-r12.sh (no regeneration). Cost so far USD 0.
- Paulo: the go for round 12 (≈ USD 44 at weight 6, ≈ 25 at weight 3).

## 2026-11-05 13:36 UTC — round 12 launched (commit 2cbd64e)
- Paulo: "run 12" (the last data round, as agreed).
- Claude: chain training/runs/overnight-r12.sh detached (pid training/runs/r12.pid, log overnight-r12.log): train r12 (r11 recipe, real set ×6, rebalanced D2 rows) → reads --guard d0/d1/d2/stranger → score → commit. Expected ≈ 11 h + 20 min, ≈ USD 45, end ≈ 01:30 UTC 11-06. Retry rule: `modal volume rm -r amalia-saneamento-lora /amalia-saneamento-r12` first. When it ends: guard.py CLI checker, per-wave table (scratchpad waves11.py pattern), the 7 value rows of the stranger test (r10 4/7, r11 1/7, ceiling 6-7/7), report section "Round 12", 1-10 line in the arc table.

## 2026-11-05 16:45 UTC — the verdict layer (D18): exam 11/11, 0 false alarms, 9/9 honest
- Paulo: "why not today"; "I need the system to be a 10/10". Round 12 keeps training on its H100 (step ≈ 340/1380 at 16:14 UTC).
- Claude: engine/application.py + engine/read.py + engine/cpedi.json; verdicts of A, B, C under engine/verdicts/ (verdict.json,
  convite.md, verdict.html); exam/scores.jsonl two new lines (16:41 with 6 false alarms = number words, 16:42 fixed: 0).
  Reads: engine/reads/dossiers-{A,B,C}/ (prompts + checked answers, r11, 222 questions, 0 refused), ≈ USD 0.15 on the L40S.
- Claude next: sealed expedientes + stranger folders through check(); second procedure (LICEDI/LEGEDI) as a rule-pack change only;
  round 12 scoring when the chain ends (≈ 01:10 UTC 11-06).

## 2026-11-05 17:15 UTC — sealed expedientes through the verdict layer (D19): 55/55, 0 false alarms, 20/20 honest
- Paulo: "run the sealed ones through it now".
- Claude: engine/application.py + expired_insurance, wrong_site, wrong_signer (certificate from the CMS), per-slot mandatory check,
  names_fact() rule, «absent» status, Portuguese dates; engine/score_sealed.py (+ engine/SCORES-sealed.md, engine/sealed-scores.jsonl);
  reads for 23 folders in engine/reads/ (r11, ≈ USD 0.25). Exam re-scored 11/11, 0 FA, 9/9 (exam/scores.jsonl: two lines with
  2 FA between 17:07 and 17:10 are the implantação habit before the rule). Round 12 at step 460/≈1380 (17:10 UTC), untouched.
- Claude next: second procedure (LICEDI / LEGEDI) as a table change; round 12 scoring when the chain ends.

## 2026-11-05 18:20 UTC — hosted service live (D20)
- Paulo: "nothing can depend on my computer"; "how good is it as a finished product?" → 6 (engine 9).
- Claude: modal/service.py deployed (web + worker + volume + secret), modal/reader.py deployed as a persistent app; engine/application.py
  verdict(folder, reads=None); engine/read.py read_with(). First hosted reader run hit Modal's 150 s web timeout → worker + status
  endpoint + polling page. Demo C with reader: 268 s cold, same verdict as local (8 findings). Round 12 at step ≈ 570/1380.
- Claude next: round 12 scoring (chain ends ≈ 01:10 UTC); then second procedure; then the shell items above in Paulo's order.

## 2026-11-05 19:00 UTC — técnico's screens live (D21)
- Paulo: "which Palantir interface fits?" → full object view, high density + inbox; "build it now".
- Claude: engine/ui.py (inbox + three-pane app), service routes + work-state endpoint, deployed; preview checked in the browser pane.
- Claude next: round 12 scoring (chain running, step ≈ 650/1380); second procedure.

## 2026-11-05 20:30 UTC — «Pergunte à lei» + Palantir-layout screens live (D22)
- Paulo: "copy literally the images I send you about Palantir"; talk to AMALIA; why Celorico only.
- Claude: engine/law_search.py, engine/ui.py rewritten on Blueprint (lei, app, inbox), service routes /lei, POST /v1/lei, GET /v1/lei/{id},
  worker answer_law; deployed; /lei public. Hosted check: «Preciso de projeto de gás numa moradia unifamiliar?» → code answer at once
  (V.27.i.iv, condicional «quando exigível»); AMALIA's pick confirmed the same passage after 207 s wall (cold reader; 3.1 s of
  generation), checker accepted. Round 12 at checkpoint 700, still training.

## 2026-11-05 21:30 UTC — code to 10 (D23): 24 tests, pre-commit check, static pages, web.py, constants in the table
- Paulo: "is our code a 10/10?" → "so make it a 10 then".
- Claude: tests/, tools/check.sh (+ pre-commit hook), .github/workflows/check.yml, engine/static/*, engine/ui.py renderer, engine/web.py,
  cpedi.json vocabulary; status/work-state key clash fixed; redeployed and verified. Round 12 ≈ step 760/1379.
