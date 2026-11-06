# saneamento-engine

**The técnico's desk for Portuguese urban licensing.** An expediente (the zip a municipality's platform exports) goes in; out comes,
for every element Portaria n.º 320/2026/1 requires of that request, *present / missing / cannot be decided*, with the file, the page,
the quoted sentence and the article, plus the draft of the *convite ao aperfeiçoamento*. Public door: **[lei.foaap.app](https://lei.foaap.app)**,
a question in a técnico's own words answered with the law's own sentences.

> **AMALIA lê. O código decide. O técnico assina.**
> The model reads. The code decides. The técnico signs.

## What it is

- **The law as data.** Portaria 320/2026/1 (Annexes V, VI, VII) and the RJUE decomposed into 642 passages with byte offsets and
  SHA-256 hashes; 88 rules with their conditions quoted from the passage itself (`law/`, `structure/`). The municipality's upload form
  is a mapping *onto* those passages (`celorico/mapping/`), never a hand-typed checklist.
- **A Portuguese sovereign model that cannot invent.** [AMALIA-9B](https://huggingface.co/amalia-llm/AMALIA-9B-0626-DPO) (Apache 2.0,
  NOVA · IST · Coimbra · Porto · Minho) fine-tuned here with LoRA on the Portaria and on public municipal documents. It answers two
  questions per file, *which element is this* and *what value does it state*, under a grammar built from the document's own text
  (`generator/guard.py`): the element id must be one printed in the prompt, the citation must be the law's words letter by letter, a value
  must be a token of the page it names. A checker re-verifies every answer; a refused answer is shown to the técnico as *not read*, never
  counted.
- **Code decides.** `engine/application.py`: inventory, required list, element check, facts compared across files, format checks
  (PDF/A mark, signature certificate parsed from the CMS, Annex VII wording, the DWG the law adds). Interpretation rules for the
  conditional elements live in a table with a *why* per line (`engine/cpedi.json`); a jurist changes the table, not the code.
- **"Cannot decide" is a scored success.** Whether a gas project is needed, whether external opinions are mandatory: the engine names
  the missing fact instead of guessing. Guessing counts as wrong on every test set.
- **Every claim is a number from a run.** Sealed sets frozen before training; a stranger test of real documents from other
  municipalities nobody tuned on; scores recorded per round with the commit hash.

## Numbers (2026-11-06)

| Test | Result |
|---|---|
| Exam: 3 simulated expedientes, 11 planted defects, 9 "cannot decide" items | **11/11 found · 0 false alarms · 9/9 honest** |
| Sealed: 20 simulated expedientes, 55 planted defects of 10 kinds, frozen before any training | **55/55 · 0 false alarms · 20/20 honest** |
| Strangers: 106 readings of real documents from 30+ municipalities, never tuned on | elements **74/77** (ceiling 76), facts 22/29 (ceiling 27) |
| Invented quotes or elements, under the grammar | **0** |

Rounds 1–12 with every number, including the rounds that failed and why: `docs/REPORT-2026-10-28.md`. Decisions D1–D26 with their
reasons: `docs/DECISIONS.md`. How the engine compares with Catala, OpenFisca, BOPS and Lupapiste: `docs/COMPARE-OPEN.md`.

## Try it

- **Ask the law**: [lei.foaap.app](https://lei.foaap.app). Passages are found by code in milliseconds; AMALIA confirms the passage
  in seconds (about 20 s when she has been idle, nothing is kept warm).
- **Run a verdict locally** (needs Python 3.9+ and `pypdf`; the reader is optional):

```bash
python3 -I engine/application.py exam/dossiers/C        # verdict.json, convite.md, verdict.html under engine/verdicts/
python3 -I exam/score.py                                 # the exam, replayed from stored reader answers
tools/check.sh                                           # everything that must be green before a commit
```

- **The screens** (`engine/static/`): an inbox with work states, the expediente as a three-pane view (findings and law in the middle,
  the PDF at the quoted page on the right), the law page. Hosted on Modal (`modal/service.py`); the reader wakes from a GPU memory
  snapshot (`modal/reader_warm.py`). A local server with the same routes: `engine/serve_local.py`.

## Layout

| | |
|---|---|
| `law/`, `structure/` | the law as data |
| `celorico/` | one municipality in full: catalogue, slot mapping, PDM, RMOU, sample |
| `engine/` | the verdict layer, the law search, the screens, the service's pure parts, tests' fixtures |
| `generator/` | the guard (grammar + checker), simulated expedientes with answer keys, the privacy scan |
| `exam/`, `sealed/` | acceptance sets with planted errors and their scorers |
| `sources/real/` | public documents used for training and for the stranger test, each with its provenance |
| `training/`, `modal/` | data per round, LoRA runs, the reader, the hosted service |
| `tests/`, `tools/check.sh` | 25 tests and the check that gates every commit |
| `docs/` | the report, the decision log, the build log, the comparisons |

## Rules the project keeps

No citizen data, ever: every simulated person carries NIF 999999990 and every page says SIMULADO; every real document is a public
publication listed in `sources/real/PROVENANCE.md` and scanned by `generator/privacy.py`. Passive reading of public sites only. The
sealed sets are never trained on. AI proposes, code checks, a person decides.

## Status

Built in three weeks, November 2026, by one person and the tools in this repository. One municipality wired (Celorico de Basto) and one
procedure (comunicação prévia de obras de edificação); the law is national and the next proofs are a second procedure and a second
municipality as table changes. Not legal advice. Not a decision system: the mayor decides, as the RJUE says.

AMALIA citation: Simplício et al., *AMALIA*, PROPOR 2026.
