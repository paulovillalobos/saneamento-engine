# Our code against the two open projects that put law into code (2026-11-05)

Read at their HEAD on 2026-11-05: CatalaLang/catala (+ catala-examples) and openfisca/openfisca-core (+ openfisca-france).
Neither reads documents; both turn legal text into executable rules, which is the half of our engine worth comparing.
Rated on architecture, not stack: where the law lives, law in time, explainability, proof.

| | Catala (INRIA, OCaml; used by the French tax administration) | OpenFisca (Python; FR, NZ, and others in production) | saneamento-engine |
|---|---|---|---|
| Where the law lives | Literate files: the article's own text, then a code block that encodes it, article by article (`###### Article L521-1\|LEGIARTI…` then `champ d'application … sous condition …`) | Python classes per variable with a `reference` URL and `label`; dated parameter YAML with `reference` per value | JSON rule per passage: the quote letter by letter, byte offsets, sha256, role, conditions with their phrase and offsets; the Portaria itself decomposed in structure/ (642 passages) |
| Law in time | Dates inside the rules (`sous condition date_courante >= \|2018-01-01\| et …`); versions by repository | First-class: `values: {2005-01-01: 0.5, 2011-01-01: 0.45, 2017-01-01: null}` and `formula_2021_02_05` per variable; the engine picks by period | Not yet. One version of the Portaria (320/2026/1 + retificação 29-A); the plan (D-next) is OpenFisca's shape: validity dates on rules and a verdict that records the law version |
| Explainability | The code sits under the article it encodes; a trace shows which rule fired | Trace per calculation; every parameter has its reference URL | Every finding carries file, page, the document's quote, the article and the law's quote; the engine's interpretation rules in a table with a why each |
| Proof | Test scopes with `assertion`s (allocations familiales: 19 assertions in 2 test files); 346 test files in the language repo | 766 YAML test cases in openfisca-france (input → expected output with error margins); 105 in core | 24 unit tests + two acceptance sets replayed on every commit (exam 11/11, sealed 55/55, 0 false alarms); the sealed set frozen before training; strangers scored per round |
| Documents | None: inputs are typed facts | None: inputs are typed facts | The point: the facts come out of PDFs through a Portuguese model under a grammar, and a checker refuses anything not on the page |
| Honesty about not knowing | Exceptions and conflicts are language features | Null parameter = not applicable | `not_assessed` is a scored success; `review`, `not_read`, `absent` are shown, never guessed |
| Who decides | The code, from typed inputs | The code, from typed inputs | The code, from what the reader read; the técnico signs |

What to take from them, in order:
1. OpenFisca's dated values and dated formulas → our rules gain `valid_from`/`valid_to`, the verdict records the version it judged under, an old expediente can be rechecked under the law of its date. The "law in time" step of the road to 10.
2. Catala's literate form → our rule pack could render as a document: the passage text, then the rule beneath it, for a jurist to read top to bottom. We have the ingredients (quote, offsets, conditions); it is a view, not a change.
3. OpenFisca's YAML test cases → our interpretation table (engine/cpedi.json) deserves one case per line: an expediente shape in, the expected finding out. Today the exam and the sealed set cover them collectively.

What they cannot take from us without the rest of the stack: reading the documents, the grammar that forbids invention, the sealed measurement. Catala and OpenFisca stop where the facts are typed in by a person; our engine starts at the PDF.

# The two open municipal permit systems in production (added 2026-11-05 night)

Read at HEAD on 2026-11-05: unboxed/bops (Back-Office Planning System, MIT, Ruby on Rails, Southwark and partner councils,
England; last commit 2026-11-04) and lupapiste/lupapiste (EUPL 1.2, Clojure + ClojureScript + MongoDB, Finland, Helsinki among
its users; open-source release 2026.1, June 2026). These are the first peers that do our job: receive a permit application,
check it, send the applicant back for what is missing, decide. Same four axes.

| | BOPS (England) | Lupapiste (Finland) | saneamento-engine |
|---|---|---|---|
| Size and proof | 3 914 files, 315 RSpec files; MIT; six years in production | 3 819 files, 667 Clojure test files; EUPL; ten+ years in production, national standard interfaces (KRYSP XML) | ~60 files; 25 unit tests + 2 acceptance sets replayed on every commit; three weeks old |
| Where the law lives | Tables: `Legislation` (title + link), `PolicyClass` / `PolicySection` (permitted development classes typed in by hand, five fixed titles), `Condition` sets. The text of the law is a link, not data | Not in the code: operations and attachment types are configuration (`operations.clj`, 1 400 lines; a 4 054-line `schemas.clj` of form fields), legal references live in i18n strings. A code comment: "Mappings to schemas and attachments are currently random" | The Portaria itself decomposed (642 passages with offsets and hashes), 88 rules with conditions; the municipal slot mapping derived from them |
| What «check» means | A checklist of document tags (`DRAWING_TAGS`, `EVIDENCE_TAGS`, `SUPPORTING_DOCUMENT_TAGS`) ticked by an officer; `ValidationRequest` state machine (pending → open → closed) to ask the applicant for more | Required attachments per operation; a verdict workflow; statements from authorities | The content of each PDF read by a model under a grammar; facts compared across files; signature certificate parsed; every finding with page, quote and article |
| Reads inside the documents | No (no PDF text library in the stack) | Only for stamping and previews (pdfbox); never to decide | Yes: this is the engine |
| Law in time | No model: links to current legislation | No model | Not yet (planned after OpenFisca) |
| AI | None | None | A Portuguese sovereign model, grammar-bound, checked |
| Explainability of a decision | Officer's notes and conditions, auditable workflow | Workflow audit, authority statements | File, page, document quote, law quote, interpretation rule with its why |
| The técnico's work | Mature: validation requests, consultees, conditions, appeals, fees, two-factor auth, GOV.UK design system | Mature: parties, authority statements, verdicts, archiving, e-identification, national integrations | Thin: an inbox with four states, one key |

Ratings on architecture, the way the rest of this file rates:
- BOPS 6: a well-built case-management system with the GOV.UK discipline; the law is a link and the check is a human's tick.
- Lupapiste 6.5: the national plumbing of a country (KRYSP, e-identification, archiving) and a decade of use; the law is config and the
  check is "attachment present".
- saneamento-engine 9 as it stands: the check is the content, the law is data, the proof is measured; everything they have
  around the check (parties, statements, appeals, archiving, users) we do not.

What to take from them: BOPS's `ValidationRequest` state machine is the six-step journey Paulo asked for, with sixteen years of
officer practice behind its states; Lupapiste's "operation → required attachments" is our slot mapping at national scale, and its
authority-statement flow is the model for «pareceres de entidades externas», the element we mark not assessed.
What they would take from us: the check itself. Either could put our verdict layer behind its "request more documents" button.
