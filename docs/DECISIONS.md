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

## D19 — The sealed expedientes through the verdict layer (2026-11-05 evening)
- Why: Paulo, "run the sealed ones through it now". The exam has 3 folders and 11 planted errors; sealed/expedientes has 20
  folders, 55 planted errors of 10 kinds (3 the exam does not plant: wrong site, expired insurance, wrong signer) and 20 honesty
  items, frozen before any training round. First run of check() on them.
- What the sealed keys needed that the exam did not, added in engine/application.py: (1) expired_insurance — the reader's
  «validade_seguro_fim» on every insurance slot (engine/cpedi.json facts_by_passage V.14 / V.27.m) against submitted_at; dates in ISO,
  dd/mm/yyyy or «31 de dezembro de 2026». (2) wrong_site — the «localizada em …» of memória and termos must begin with the request's
  site (submission.json). (3) wrong_signer — the signing certificate is parsed out of the PDF (CMS /Contents → openssl pkcs7 -print_certs);
  rule in the table: one certificate, one declarant — the certificate that signs the project authors' termos (V.11) belongs to their
  declarant; a termo of another declarant (coordinator V.12, works director V.27.k) under the same certificate is wrong_signer. The
  planted error lives only in the certificate: the text still says «Assinado digitalmente por <the declarant>». (4) a mandatory
  municipal slot with no file is a finding even when a sibling slot carries the same Annex V element (V.14: one insurance per author);
  conditional law → not_assessed (TRDFO/SRCDFO, «quando exista»).
- Code-only: 45/55, 0 false alarms, 20/20 honest. With the reader (r11, 1 916 questions over 23 folders in one Modal call, 2 refused,
  load 146 s + generate 165 s, ≈ USD 0.25): 55/55, 0 false alarms, 20/20 honest, 0 review, 5 not read (engine/SCORES-sealed.md).
- Two reader habits surfaced and were answered in code, not by retraining: (a) asked for the implantação, the reader quotes the
  memória's quadro sinóptico and gives the first number in it («superfície do terreno 1200 m2; área da parcela 1200 m2; área de
  implantação de 277 m2» → 1200), 2 false alarms on the exam, 2 on the sealed set; rule names_fact(): the segment of the quote that
  holds the value must name the fact asked (keyword per field), otherwise the reading is «not_read», never a finding. (b) «superfície
  do terreno» read as área da parcela: kept (the training keys define parcela by parcela|terreno|lote; Annex I-C separates them, the
  generator makes them equal; a real divergence would show as a value_mismatch with both quotes).
- Statuses: «absent» added — the reader says the document does not state the fact (fogos on a memória of a warehouse): an answer,
  not a failure; «not_read» is now only a refused or neighbour-quoting answer. Scorer: a value_mismatch on the field of a planted
  impossible_value is the same typo seen twice (the exam's also_accept), not an alarm.
- Observed: the same prompt can get a different answer in a different batch (exam A's implantação right in the first read, the
  quadro's first number in the second; temperature 0, vLLM batching). The code rule above makes the verdict stable either way.
- Still not done: real stranger documents are single files without a folder, slot or key, so check() does not apply to them as
  expedientes; what applies is the element and fact reading already scored per round. The second procedure is next.

## D20 — The verdict layer hosted: nothing on a laptop (2026-11-05 night)
- Why: Paulo, "we need a backend and a front end, nothing can depend on my computer". The engine was a command on the Mac.
- What: modal/service.py, one Modal app «saneamento-service»: a FastAPI web endpoint (upload page in Portuguese, list page, verdict
  page, convite.md, verdict.json, the uploaded PDFs), a volume «saneamento-store» (/store/<municipality>/<id>/files, reads, verdict.*,
  meta.json), a worker function process_expediente (reader through the deployed app «saneamento-reader», Function.from_name; then
  application.verdict) spawned by the web request, a status endpoint the page polls. Key = Modal secret «saneamento-token» (X-API-Key
  header or the session cookie the page sets; local copy deploy/.saneamento-token, gitignored). Image carries engine/, generator/, law/,
  structure/, celorico/ and exam/dossiers/ (demo buttons A, B, C); no training data, no sealed set. URL printed by modal deploy
  (…saneamento-service-web.us-east.modal.run); health /v1/saude public; everything else needs the key.
- Why Modal and not Cloud Run tonight: the reader already lives there, so storage sits next to the GPU and no second cloud, no cross-cloud
  token, no bucket (gcloud's storage command is broken on this Mac). Region us-east: fine for simulated expedientes; before a câmara
  uploads a real file, storage and reader move to the EU together (the same move Paulo wants for the CCP engine). No Supabase yet: files
  are the source of truth; a database comes with the second municipality, users and roles, and the audit trail.
- Found on the first hosted run: a web request on Modal must answer within 150 s; the reader loads in ≈ 150 s when cold, so the first
  synchronous run never returned (no log line, empty body). Fix: the worker. Measured after it: demo B code-only ready in 1.9 s; demo C
  with the reader, cold, ready in 268 s wall (257.0 s inside the worker), 8 findings, 17 not assessed,
  2 review, 0 not read — the same verdict as the local run. Sealed S777000-0007 uploaded as a zip,
  code-only: 3 findings in 0.6 s (unsigned TREECP, DWG, wrong signer from the certificate; openssl is in the image).
- Not done: EU hosting; a warm reader (every cold run pays ≈ 2.5 min of model loading); accounts and roles (one key = one municipality);
  Celorico's own convite template; a public demo mode (today nobody enters without the key; the repo has no remote).
- Finished-product rating given to Paulo: 6 (engine 9). A 10 = a técnico in Celorico runs a real expediente without us in the room:
  EU move, warm reader, template, accounts. Shell, not engine; three to four days.

## D21 — The técnico's screens: inbox and the three-pane expediente view (2026-11-05 night)
- Why: Paulo looked at build.palantir.com and asked which interface fits; the answer was Palantir's "full object view, high density"
  (identity rail · tabbed content · document preview · side drawer) plus the action-oriented inbox for the list. "Build it now."
- What: engine/ui.py, plain HTML + JS over verdict.json, no framework. inbox(rows): one card per expediente with state (novo → em
  análise → convite enviado → saneado), responsável, counters, one-click state buttons; the header strip counts total / with
  deficiencies / clean. app(): dark header strip (expediente, operation, the five counters, the reader), left rail (identity +
  sections), middle tabs Elementos (the findings table, then the Annex V table one row per element) · Factos (divergent facts, then
  every fact read with its quote) · Convite (editable draft, copy, download) · Ficheiros (per file: PDF, PDF/A, signature + certificate
  CN, pages, element read); right pane = the PDF in an iframe opened at the quoted page (#page=n) when a finding, a quote, an element
  or a file is clicked; drawer under the content = não avaliado / para revisão / não lido / sem valor. Law text collapsed per finding
  (details), evidence quotes always open. Type weight 500 minimum, no grey text.
- Service: GET /expedientes → ui.inbox; GET /expedientes/{id}/ → ui.app (verdict.html stays as a file); POST /v1/expedientes/{id}/trabalho
  {estado, responsavel} → meta.json (+ historico). Deployed and checked: inbox lists 4, app page served, state change to em_analise with
  a responsável persisted, unknown state → 422.
- Preview without a server: ui.app(inline=…) embeds the verdict (the local http server was refused by the sandbox; a file inside
  the project folder renders live in the browser pane). Screenshot checked at 800 px: rail, tabs, findings with evidence, PDF pane.
- Not done: the PDF pane depends on the browser's viewer honouring #page (Chrome, Edge, Firefox do; Safari ignores it); no
  highlight of the quote inside the PDF; the convite edits are not saved server-side (copy/download only); one shared key.

## D22 — «Pergunte à lei» and the screens copied from Palantir (2026-11-05 night)
- Why: Paulo saw build.palantir.com: "wide, simple, I loved it; ours is stale and sad". And: "should the user be able to talk with
  AMALIA? we have the whole law decomposed, why are we scoped to Celorico?" Then: "copy literally the images I send you".
- Screens (engine/ui.py, Blueprint = Palantir's open-source design system, CSS from a CDN; Source Sans; no framework): «Pergunte à lei»
  copies the "Request / Feedback Configuration" layout — purple band with icon tile, title and one-line subtitle; left: question card
  with one blue «Submeter», answer card, «Passagens encontradas» card with a pager; right: «Configuração» panel with the scope, who
  answers, six example questions, one green button. The expediente copies the "full object view, high density" layout — identity rail
  (icon + requerente, Deficiências / Elementos / Documentos, the facts), tabs with icons (Deficiências · Revisão · Elementos · Factos ·
  Ficheiros · Convite), content left, «Pré-visualização do documento» right (the PDF at the quoted page), the counters as a strip above.
  Inbox restyled the same way. Checked in the browser pane at 800 px: both read as the originals, with our content.
- Not a chat. A chat box is where invention returns. engine/law_search.py: the técnico's question → BM25-style search over the
  decomposed law (Portaria 320/2026/1 Annex V/VI/VII leaves + RJUE articles from structure/decreto-lei-108-2026.json) → candidate
  passages quoted letter by letter; «exigido sempre / condicional / não» decided by CODE from the rule pack (conditions of the passage;
  a V element outside the CPEDI lists = não); AMALIA, when asked, picks the passage among the candidates with the D0 «exigencia» task
  it was trained on (round 11: passage 94 %, citação 93 %; its own «exigido» label 53 % and therefore unused). The pick counts only
  when the passage id is a candidate and the citation equals the passage text (law_search.check); otherwise the code's first
  candidate stands and the page says so.
- Service: GET /lei public, POST /v1/lei public (code answer at once; AMALIA's pick in a worker, answer_law.spawn, ≤ 40 per hour per
  container, result under /store/_lei/<id>.json, GET /v1/lei/{id} polled by the page). No key, no citizen data: a question about the
  Portaria is public. First public door of the product.
- Scope: the law is national; the verdict needs a municipality's slot mapping (Celorico checked line by line; rjue-engine holds other
  mapped catalogues). «Pergunte à lei» needs none.
- Six questions checked code-only: gas project → V.27.i.iv condicional «quando exigível»; levantamento → V.7 condicional «sempre que
  haja alteração da topografia…»; fotografias → V.15; DWG → VI.1.b; pareceres externos → RJUE art. 13-B + V.27.h; prazo do convite →
  RJUE art. 11 n.º 5 / n.º 2 a). Hosted run with AMALIA: see BUILD-LOG.

## D23 — Code to 10: tests on every commit, pages as files, constants as data (2026-11-05 night)
- Why: Paulo, "is our code a 10/10?" → 7.5: no tests on the verdict layer, screens as JavaScript inside Python strings, service state
  in a process dict, constants in code. "So make it a 10 then."
- Tests: tests/ (stdlib unittest, 24 tests): rules (number words and formats, dates, the quote-names-the-fact rule, the declarant,
  the signing certificate from a real exam PDF), the exam replayed from engine/reads (11/11, 0 false alarms, 9/9), the sealed set
  (55/55, 0, 20/20; skipped where the PDFs are not on the machine), the verdict's shape, the table as the source; «Pergunte à lei»
  (six questions, scope, the checker's refusals); the pages (every placeholder filled, inline previews, no grey text in the CSS);
  the service's pure parts (ids never a path, the zip intake flattening and filtering, the listing, the work state, the shared
  hourly budget). tools/check.sh = scaffold tests + engine tests + the two scorers; installed as the pre-commit hook
  (tools/install-hooks.sh): a red check refuses the commit. .github/workflows/check.yml runs the same when the repo has a remote.
- Pages: engine/static/{app.css, lei.html, app.html, inbox.html}; engine/ui.py is a 40-line renderer that fills __CSS__, __HEAD__,
  __DATA__, __PDF_BASE__, __BACK__, __STATES__ and refuses a page with a placeholder left. The inbox renders client-side from
  GET /v1/expedientes (JSON), so the same file serves the service and a file preview.
- Service: engine/web.py holds the pure parts (new_id, safe_id, unzip_to, listing, status_of, set_work, take_budget); modal/service.py
  is the HTTP layer over them. The reader's hourly budget moved from a process dict to a counter file in the volume (all
  containers see it). Found by the hosted check: the status endpoint reported the técnico's work state («em_analise») in the
  field the page polls for «pronto» → status_of now keeps the processing state in «estado» and the work state in «trabalho».
- Data: engine/cpedi.json now also holds fact_keywords, number_words, months, site_pattern, declarant_pattern, work_states,
  finding_labels; application.py reads them. A jurist or a técnico changes vocabulary without touching code.
- Check at this commit: 24 tests OK, exam 11/11, sealed 55/55, hosted routes verified after redeploy.
- TRAP (cost three redeploys): after `modal deploy`, a warm container of the previous version kept answering for minutes, so the
  status route still showed the old shape. `modal app stop saneamento-service --yes` then `modal deploy` gives fresh containers.
  Verify a deploy on a route whose output changed, never on one that looks the same either way.
- What is still not 10: one shared key (users come with the second técnico); the pages' JavaScript has no tests of its own (the
  browser pane screenshot is the check); the service module itself is exercised only live (its logic is in web.py, tested).
