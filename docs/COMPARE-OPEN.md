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
