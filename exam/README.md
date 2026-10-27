# The exam

Three simulated applications for a building prior communication (comunicação prévia de
obras de edificação) in Celorico de Basto, and the answer key a correct engine must match.
Written before the engine can read applications, so every later step is measured against it.

Everything is fictional and every page says **DOCUMENTO SIMULADO — SEM VALOR LEGAL**: the
people, NIF 999999990 (the generic "consumidor final" number, not a person), the address,
the policies. Signatures use a test CA (`pki/`) and are not qualified signatures.

| Dossier | Content | What the engine must report |
|---|---|---|
| A | Everything the law asks for, slot by slot (Celorico's NoPaper codes) | Only the generator's known limit (no DWG of the site plan) |
| B | A without the charges estimate (V.27.g) and the photographs (V.15) | Both missing, with the law quote |
| C | A with traps | A ".pdf" that is an image; a PDF without PDF/A identification; an unsigned declaration; a declaration without the Annex VII wording; built area 554 vs 610 m² between documents; plot area typed 120 instead of 1200 |

In every dossier the engine must also say it **cannot decide** three things (status
`not_assessed`): whether the test signatures are qualified, whether external opinions are
needed, whether a gas project is needed. Guessing is scored as wrong.

Known limits, recorded in the answer key rather than hidden:
- no DWG of the site plan (Annex VI n.º 1 b)): it cannot be produced here, so even A lacks it;
- PDF/A conformance is claimed, not validated (no reference validator on this machine);
  those items are `provisional` and not scored;
- the Annex I-C field labels in the planning summary were transcribed by Claude from the
  official image; the answer key's legal judgments follow the AI-reviewed rule pack and are
  not human-approved.

## Files

    build.py        generates pki/, dossiers/, answers.json, manifest.json (new bytes on every run)
    answers.json    the answer key; every law quote is checked against the law text by verify.py
    manifest.json   sha256 of every generated file; verify.py checks it
    score.py        runs engine/application.py on each dossier and scores it (--record appends to scores.jsonl)
    scores.jsonl    score history, one line per recorded run
    pki/            test CA and test signer certificates (private keys are not committed)

The engine contract: `engine/application.py` exposing `check(dossier_dir)` returning a list
of `{"status": "finding" | "not_assessed", "type", "slot"?, "file"?, "field"?, "rule"?, "law_ref"?, "quote"?}`.
