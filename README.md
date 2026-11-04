# saneamento-engine

The técnico's desk for one municipality, Celorico de Basto: an expediente (the zip a NoPaper installation delivers) comes in; out
comes, per element of Portaria 320/2026/1 Annex V required for that request, present / missing / not required here, with the
file, the page, the facts read and the article, and the draft of the convite ao aperfeiçoamento (RJUE art. 11.º). AMALIA,
fine-tuned here, reads documents and facts; code decides; every quote is checked against the PDF text before it counts.

Separate from rjue-engine (the law and the catalogue) and ccp-engine (public procurement): copies in, nothing shared live.
See sources/PROVENANCE.md.

Layout
- law/, structure/      the law as data, from rjue-engine
- celorico/             the whole picture of one municipality: catalogue, mapping, RMOU, PDM, taxas, geo, the sample
- sources/real/         real public pieces: memórias descritivas, official termo minutas, file-naming norms
- exam/                 the three day-one dossiers with planted errors, answer key and scorer (baseline 0/11)
- generator/            expedientes written from the law + real pieces, with answer keys; guard.py; ceiling.py = the whole-document ceiling with a large general model; ocr.py = OCR for pages without text; privacy.py = private-identifier scan before a real document enters; realtrain.py = rows from the real training documents (sources/real/train, D17); guard.py = the hard scaffold (D13)
- sealed/               held-out expedientes frozen before any training (to build)
- training/, modal/     data per round, LoRA runs on Modal (app saneamento, volume amalia-saneamento-lora)
- docs/                 DECISIONS.md, BUILD-LOG.md

Rules: no citizen data, ever; passive reading of public sites only; AI proposes, code checks, a person decides; the sealed set is
never trained on; every claim in a dossier is a number from a run.
