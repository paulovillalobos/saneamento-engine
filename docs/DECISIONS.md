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
