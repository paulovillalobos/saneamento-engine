# Decisions

- D1 (2026-10-27): new repo, assets copied from rjue-engine and ccp-engine with commit shas; nothing imported live.
- D2: Modal app name `saneamento`, adapters in volume `amalia-saneamento-lora`; `amalia-weights` read-only.
- D3: expedientes are written from the law (Annex V elements, VI formats, VII wording, RJUE conditions) using real public pieces as raw material; no invented law, no citizen data.
- D4: sealed held-out = 100 expedientes frozen before round 1; three metrics: element id, facts exact with page, invented documents (must be 0).
- D5 (2026-10-27): expedientes are rendered by generator/pdfgen.py (native PDF writer: Helvetica/WinAnsi text, vector drawings, PNG images), not by a browser; finish()/sign() are the exam's, verbatim. Thousands of documents per minute; the page of every fact is known at write time.
- D6: planted-error catalogue (generator/expedientes.py ERRORS): missing_required, template_wording_missing, unsigned, not_pdf, not_pdfa, value_mismatch, impossible_value, wrong_site, expired_insurance, wrong_signer; 0-4 per expediente; a noise file (invoice, CV, letter) in half of them.
- D7: the Annex VII wording differs by section: I (project authors) «observa as normas legais e regulamentares aplicáveis à pretensão»; II (specialty projects) «Observa as normas legais e regulamentares aplicáveis, com exceção de nenhuma». Labels carry the section's phrase.
- D8: sealed sets = sealed/d0-test.jsonl (10 % of passages, by passage), sealed/expedientes (seed 777000, 20 expedientes) → d1-test, d2-test. Training seeds start at 1 and never equal 777000. PDFs are not committed (deterministic from the seed); keys, labels and rows are.
- D9: reader prompts show the file's extracted text (first 3 500 characters, pages marked) — what a técnico's PDF viewer shows — never the PDF bytes.
- D10 (2026-10-27): the reader does NOT memorise the law. r1b trained on every passage (3 phrasings, 2 epochs) and still invented the text of
  505/558 passages it had seen (median similarity 0.07 to the real text). The law is data in the engine; the reader receives the relevant
  passages in the prompt and must select and copy. D0 v3 = selection among candidate passages (hard negatives: siblings), copy verbatim,
  abstain when the right passage is not offered. D1 v2 = the CPEDI element shortlist (id + text) in the prompt. D2 unchanged.
  Inference may give the whole CPEDI block (216 passages ≈ 13.5k tokens, prefix-cached); training uses shortlists so a row stays ≈ 1-3k tokens.

## D11 — the file name must not carry the label (2026-10-28)
A probe on round 5 showed the reader classified real memórias by their file name: real text renamed to the generator's
slot-stem name was right 3/3, generated text under a real name was right 3/3, every content ablation was wrong.
Rule: in training, a large share of file names say nothing or lie (generator/d1d2.py opaque_name); the sealed generated
sets keep their names (they measure the lab), the stranger test keeps the real names (it measures the world).
Corollary: a sealed set built by the same generator cannot detect a shortcut the generator itself creates; the stranger
test is the only gate that counts for shipping, and it must grow (more real memórias, termos, plantas with real names).

## D12 — D1 names the piece; D3 checks the fit to the request (2026-11-03)
Round 7 rejected the four real memórias of the stranger test (Valongo, three Cascais) because their headers name a
loteamento and prompt v4 listed "loteamento" among the other procedures. The reader applied the rule consistently; the
key and the rule disagreed. Decision: D1 answers "which element is this piece" by the nature of the piece — a memória
descritiva e justificativa of any operação urbanística is item 9, a projeto de estabilidade is item 27.i.i, whatever
operation or requerente the header names. Whether the piece describes THIS request (site, operation, requerente, areas)
is a D3 check made through D2 facts. The one exception stays: termos de responsabilidade are procedure-specific in the
law itself (utilização, conclusão, receção de obras de urbanização have their own legal basis), so a termo of another
procedure is not an element of this request. Prompt v5 says both things in rules 1 and 3; the stranger keys are unchanged.

## D13 — the hard scaffold: the reader can only say what the prompt holds (2026-11-03)
The fresh batch showed a fabricated fact with a fabricated quote on a real file (Nazaré, page 5 of a four-page window).
Paulo's call: no round 9; scaffold first, ccp-engine style (readers/quote_grammar.py), so that she "can only answer what
she has been trained with". Decision: the decoder follows a grammar built from each prompt by generator/guard.py, and the
same language is checked in Python after decoding.
- D1: the element id is one printed in the shortlist, the citation is that line's law text letter by letter, or
  {null, "", nao_e_elemento|ilegivel}; a file that is not a PDF admits only {null, "", ilegivel}.
- D2: value and quote are token-aligned pieces of ONE shown page and «pagina» is that page's number, or the null answer.
  Tokens: runs of digits, runs of letters, each other mark alone («1.900,00m2» holds «1.900,00»). Pages and answer strings
  are compared after whitespace collapse. The rule the grammar cannot say, the checker adds: the value is inside the quote.
- Sentences use the trained JSON spacing («, » and «: »), as every training answer was written.
- An answer the checker refuses is wrong, not an abstention: the scorer counts «recusado» as a miss in every field, the
  product sends the file to the técnico as not read.
What the scaffold cannot do: stop a real number that answers another question (Moimenta «90» days for months) or a real
element id for a file that is not that element. Those stay measured by the keys. Nothing is trained; the r8 adapter is
read with --guard and the keys say what changed. D0 (the law tasks) keeps its schema: not in the file path of D3.

## D14 — scaffold from the start: the window, the keys and the data of round 9 (2026-11-03)
Paulo: she may say the same thing in other words, she may not say what is not there ("Portugal is in France"), and every
round from now on is trained and read inside the scaffold. Round 9 is the first.
- Keys inside the language. generator/d1d2.py checks every row's key with guard.check() and drops the row when the key is
  outside it (page not shown, value cut); the old training set carried 77 of 4 601 fact rows (1.7 %) whose page was never
  shown or whose value was cut by the 3 500-character window — the generator was teaching her to answer with pages she
  could not see, which is where «page 5» came from. Quotes are now token-aligned pieces of the page (quote_for: the
  labelled line when on the page, else the sentence holding the value, preferring the field's keyword), never the 60-char
  window cut mid-word that round 8 learned to copy.
- The window. window(): the first 2 pages, then the pages with the most signals (amounts, areas, dates, prazos,
  signatures), then the rest in order, 11 000 characters in all, each page cut at 2 500 on a word boundary; the header
  lists the pages shown when not all. The grammar admits only shown pages, so an unshown page cannot be cited.
- The data. Long memórias go on past the quadro (solutions, networks) and may state the cost (30 %) and the prazo: in
  months (a fact) or in DAYS (no prazo_meses fact → the question "em meses" is null). Absent-fact questions are asked only
  of files whose labels have no such fact, and now of memórias (cost, prazo). New noise: an index of pieces (written and
  drawn, with scales and sheet sizes) and an external entity's opinion listing the elements it received.
- Sealed. The sealed expedientes are unchanged; their rows are regenerated with the window and the memória absent-facts
  (D2 1 148 → 1 190 rows); the r8-window rows stay as sealed/*-r8.jsonl for the r8-under-scaffold baseline. The stranger
  rows are regenerated with the window, keys unchanged. Wave 3 is scored by r9 under the scaffold: its second and last.
- Reads: r9 on D1/D2/stranger with --guard; r8 with --guard on the r8-window rows (sealed D2, stranger waves 1-2) as the
  "scaffold alone" baseline. D0 keeps its schema.

## D15 — The ceiling, and the scoring conventions it fixed (2026-11-04)
- Before any round 10, measure what the stranger rows allow: a large general model (Claude Opus 5.5) reads the same 106 rows,
  same prompts, same shortlist, same JSON, whole document (every page, uncut, in order), no training. generator/ceiling.py
  builds the prompts and collects; the readers see prompts/ only, never a key. Result 76/77 elements, 27/29 facts, wave 3
  40/40 → the documents allow ≈ 97%; the gap to AMALIA (61/77 elements under r9) is ours: the window.
- A fact's value is unit-tolerant in the scorer (score.py val()): «1.900,00m2», «1.900,00 m2» and «1.900,00» are the same
  value. Reason: the prompt asks for the exact text as it appears and both are that text; the keys were written without the
  unit by habit. Applies to every run equally.
- Keys: a wave-1 or wave-2 key may be corrected when a reader shows the document says otherwise (tuned set); a wave-3 key
  never (held-out set). Corrected today: Valongo custo_total null → «2.125.000€» page 4 (Estimativa orçamental total of the
  obras de urbanização). The r8-window copy of the row carries the same key.
- Direction: the base model's context is 32,768 tokens (Llama architecture; our 8,192 was a training-script setting, the
  11,000-character window a generator setting). Round 10 reads whole documents; no page selection; keys still gated by the
  scaffold; "about an element" negatives at a fixed share in every mix. Real public documents enter TRAINING only from a
  collection kept apart from the test.
- OCR (generator/ocr.py): pages with < 80 characters of pypdf text go through ocrmypdf --skip-text -l por once (cached in
  sources/.ocr-cache, ignored by git); recovered text is prefixed «[texto OCR]». The real corpus has 8 such pages in 6 files,
  all blank/image-only, 0 recovered: no scanned document in the test today.

## D16 — Round 10: whole documents, as long as the real ones (2026-11-04)
- The view: window() shows the WHOLE document, every page uncut in order, up to 65 000 characters (the base model's 32 768-token
  context minus prompt and answer); only a longer document loses its last pages, and then the header lists the pages shown so
  the grammar admits only those. D14's 11 000 / 2 500 / 2 and the signal-page order are retired: one view for both tasks, the
  document as it is. train_lora.py r10: max_len 32 768, tokens_per_batch 32 768.
- The length: our documents ran 1–6 pages (sealed memórias all 1 page; training memórias 1/3/5/6; noise 1); real memórias run
  5–34, real norms and regulations 4–40. The ceiling read the long ones whole and got them; AMALIA never saw one in training.
  stretch() lengthens with numbered chapters (memória sentences from the real pool; article templates for regulations), optional
  repeated letterhead per chapter: long memórias 6–24 pages with the cost/prazo in the second half and a few chapters after;
  speciality memórias 4–16 when long; 40 % of noise documents 5–30 pages. 12-expediente sample: memórias 1–19 pages, noise
  1–29, D1 prompts median 11k / p90 21k / max 76k chars, 0 keys dropped by the gate.
- Sealed expedientes stay frozen (1-page documents); their rows are regenerated with the whole-document view (r9-view copies as
  sealed/*-r9.jsonl). The stranger test, regenerated whole, is the gate. The r9 adapter is read on the whole-document stranger rows
  as the "view alone" baseline (training/runs/r9-whole/; smoke: 650 KB D2 grammars compile, 6 rows in 21 s).
- Expected cost 2–3× round 9 (longer rows, attention quadratic): ≈ USD 30–45. Approved by Paulo 2026-11-04 ("go, run round 10
  with whole documents").
- Outcome (2026-11-04 19:35 UTC): training killed by Modal's 6 h function timeout at step ~1035 of ~1050; the step-1000
  checkpoint (learning rate ≈ 5 % of peak there) is the r10 adapter, named as such in training/runs/r10/MANIFEST.json; timeout now
  12 h. Stranger, whole documents: elements 67/77 (r9 61, ceiling 76), facts 25/29 (r9 25, ceiling 27), wave 3 33/40 (r9 34,
  ceiling 40), fabricated 0. The r9 adapter on the whole view scored 59/77: the gain is from training on long documents, not from
  the view. Wave 3 did not move: its misses are document shapes absent from the generator (park/road memórias with engineering
  chapters, priced bills of quantities, technical notes) → the next data is a real-document TRAINING collection apart from the test.

## D17 — Real public documents for TRAINING, apart from the test (2026-11-04)
- Why: round 10 proved the generated expedientes teach everything they contain and that the wave-3 misses are document SHAPES
  the generator never produced (park and road memórias with engineering chapters, priced and unpriced bills of quantities, technical
  notes, blank 2026 forms). Paulo's call: "get the real documents for training". The ceiling showed the text of these documents is
  enough to read them right.
- What: sources/real/train — 111 public PDFs from municipalities and public bodies NOT in the stranger test (Melgaço, Sabugal,
  Peniche, Lisboa and its juntas, Angra, Condeixa, Borba, Arganil, Lousã, Figueira de Castelo Rodrigo, Tomar, Porto de Mós,
  Oliveira de Azeméis, Póvoa de Lanhoso, Ponte da Barca, Mealhada, Viana do Castelo, Sardoal, Sabrosa, Fronteira, Sines, Ílhavo,
  Aveiro, S. João da Madeira, Feira, Murtosa, Praia da Vitória, CCDR-LVT, APA, LNEC, Provedor de Justiça, Madeira DRE). Provenance
  in sources/real/PROVENANCE.md. Found by six parallel searches by document shape; downloaded as published; names kept.
- Privacy gate: generator/privacy.py scans every file (natural-person NIF, phones, ID words, personal e-mail, professional numbers)
  with context; a human decides. Dropped: a school safety plan with staff mobiles, a memória with an architect's OA number, a
  memória naming a private owner with his property articles. Public bodies' own numbers and officials signing in function stay.
- Keys: generator/realtrain.py KEYS, by hand, same conventions as the test: a memória of any operation = item 9 (incl. urbanisation
  road memórias, D12); speciality memórias = their 27.i item (water/sewage networks of a loteamento keyed 27.i.v); plano de
  acessibilidades memória = 27.b.vi; priced price lists / orçamentos = 27.f; unpriced quantity maps, cadernos de encargos, PSS,
  PPGRCD, blank forms, norms, guides, regulations, fee tables, avisos, leaflets, service proposals = not an element; an external
  entity's opinion letter (APA) = 27.h (noted ambiguous: here on a plan). Days-only deadlines → prazo null. 111 documents:
  72 D1 positives / 261 negatives across 3 name variants; 230 D2 rows (one fact + two absent questions per document).
- Rows: training/data/real/train.jsonl (563), INDEX.md with the key table. Each document → 3 D1 rows (real name; opaque name;
  damaged text under a stranger name) + D2 rows, all gated by guard.check (0 dropped). HARD RULE in code: a train file whose sha256
  matches any test file stops the build. Whole-document view, 65k-char cap (p90 prompt 64.7k chars, max 75.7k).
- r11 = r10 data + real set repeated 3× (modal/train_lora.py RUNS r11). Chain training/runs/overnight-r11.sh; needs Paulo's go
  (≈ USD 25-30, 6-7 h at 32k; timeout now 12 h).
- Paulo's go 2026-11-04: weight 6, not 3. Ran 2026-11-04 23:30 → 11-05 10:33 UTC, clean finish, ≈ USD 44 (11 h: the long real rows).
- Outcome (training/runs/r11/SCORES.md): elements 74/77 (r10 67, ceiling 76), wave 3 30/32 (r10 26), about-element documents
  all rejected, invented 0, fabricated 0, refused 0. Facts 22/29 (r10 25): six values answered "not present". Cause found after the
  run: the real D2 rows were 229 absent against 1 value (two absent questions per document, almost no keyed values) ×6 in the mix.
  Decision stands; the real set needs balanced fact rows (D17 fix, USD 0) before round 12.
- D17 fix (2026-11-05 midday, USD 0): fact values read off the 44 element documents by four readers, kept only when printed as a
  whole token of one page (build check), short values pinned to their page (realtrain.py KEYS tuple takes an optional page);
  absent question only on documents that state a value, one each. 20 values : 22 null. Real memórias rarely print these facts;
  no value was invented to balance the file. r12 = r11 recipe on the rebalanced file (modal/train_lora.py RUNS r12,
  training/runs/overnight-r12.sh, no regeneration). Needs Paulo's go (≈ USD 44 at ×6).


## D18 — The verdict layer: folder in, findings out (2026-11-05)
- Why: the exam (exam/) had scored 0 since 2026-10-14 because nothing took a whole expediente and produced findings; the reader
  answered one question per document and the law sat as data. Paulo: "why not today" — the layer does not depend on round 12,
  and a model with no product around it is a slide.
- What: engine/application.py, check(folder) → items with a status. Five steps: inventory (slot from the file name, PDF bytes,
  pdfaid mark, /Sig, text per page); required list (every Annex V document element for a CPEDI, its Celorico slots from the
  mapping, mandatory/optional from the catalogue: mandatory + no file = finding missing_required with the law's quote; conditional
  + no file = not_assessed naming the condition); element check (the reader's guarded D1 answer against the slot; another family =
  «review» for the técnico, never a finding; refused = not_read); facts (the reader's D2 answers on REQ, MDARQ, EOCT, CEO; code
  compares across files = value_mismatch with both quotes, within a file parcela < implantação = impossible_value; null or
  refused = not_read); format (not a PDF, no PDF/A mark, unsigned where the slot says S, V.11 termo without the Annex VII core
  wording, PI without a .dwg/.dxf). engine/read.py builds the prompts with generator/d1d2.py's own templates and runs
  modal/reader.py --guard once for all folders, guard.apply over the answers. Output per expediente: verdict.json, convite.md
  (one numbered paragraph per finding with the article and the quotes), verdict.html (yes/no per element).
- Interpretation rules in code, each with its why, in engine/cpedi.json: V.27.g estimativa dos encargos required on every new
  building (no Celorico slot: recognised by its text under OUTDOC); V.15 registo fotográfico required (the condition qualifies the
  neighbours, not the record); V.27.h / V.10 external opinions, gas, seismic, HVAC, electromechanical, cedências, logradouro =
  not_assessed with the missing fact named; V.27.a satisfied by the certidão (CRP); V.27.b.v propriedade horizontal optional.
  Proposed by Claude from the rule pack; a jurist may overturn any line by editing the table, no code changes.
- Result (exam/scores.jsonl, 2026-11-05 16:42 UTC): 11/11 findings, 0 false alarms, 9/9 honest not-assessed, on A, B and C.
  Code-only (before the reads): 9/11, 0 false alarms, 9/9. The reads (r11 adapter, 222 questions, 0 refused, load 126 s +
  generate 13 s on the L40S, ≈ USD 0.15) added the two fact findings: 554 vs 610 m² between requerimento and memória, and the
  plot typed 120 against an implantação of 277 (and 1200 in the memória). One bug found and fixed on the way: the memória says
  «dois pisos» and «um fogo», the requerimento says 2 and 1; the first comparison flagged them (6 false alarms) → number words.
  Reader vs slot: 2 «review» items per dossier — LEVT-termo-levantamento (a termo de responsabilidade filed in the levantamento
  slot: the reader says V.11, the slot says V.7; both are right) and SRITED-seguro (the reader says not an element; the ITED
  author's insurance is V.14). Shown to the técnico, not in the convite.
- Not done here: the convite is Portuguese but its wording is the engine's, not Celorico's minuta; verdicts are files under
  engine/verdicts/ (no database until a second municipality or técnico); the sealed expedientes and the real strangers have not
  been run through check() yet (next); PDF/A conformance stays provisional; signature qualification stays not_assessed.
