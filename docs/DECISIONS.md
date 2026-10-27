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
