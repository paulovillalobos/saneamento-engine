# training/runs/r12/d0.json

model amalia-llm/AMALIA-9B-0626-DPO@c4614b9b5c7b adapter amalia-saneamento-r12 answered 1531 skipped 0 load 126.2s gen 144.6s

- **alinea_de** n=203; passagem 196/203 (97%); citacao 196/203 (97%); ambos 196/203 (97%); nao_sei 4
- **elemento_doc** n=91; passagem 90/91 (99%); citacao 90/91 (99%); ambos 90/91 (99%); tipo 68/91 (75%)
- **exigencia** n=116; passagem 101/116 (87%); citacao 103/116 (89%); ambos 101/116 (87%); exigido 62/116 (53%); nao_sei 1
- **localiza** n=492; passagem 475/492 (97%); citacao 473/492 (96%); ambos 472/492 (96%); inventado 5; nao_sei 1; probes nao_sei 42/47
- **proibido** n=30; passagem 28/30 (93%); citacao 29/30 (97%); ambos 28/30 (93%); resposta 29/30 (97%)
- **transcreve** n=491; passagem 491/491 (100%); citacao 490/491 (100%); ambos 490/491 (100%); inventado 9; probes nao_sei 52/61

# training/runs/r12/d1.json

model amalia-llm/AMALIA-9B-0626-DPO@c4614b9b5c7b adapter amalia-saneamento-r12 answered 1145 skipped 0 load 147.7s gen 111.8s

- **d1_elemento** n=1145; citacao 1071/1071 (100%); elemento 1145/1145 (100%); tipo 1145/1145 (100%)

# training/runs/r12/d2.json

model amalia-llm/AMALIA-9B-0626-DPO@c4614b9b5c7b adapter amalia-saneamento-r12 answered 1190 skipped 0 load 123.6s gen 67.9s

- **d2_facto** n=1190; valor 1190/1190 (100%); pagina 1035/1035 (100%); valor_e_pagina 1035/1035 (100%); citacao_contem 1035/1035 (100%)

# training/runs/r12/stranger.json

model amalia-llm/AMALIA-9B-0626-DPO@c4614b9b5c7b adapter amalia-saneamento-r12 answered 106 skipped 0 load 148.6s gen 103.9s

- **d1_elemento** n=77; citacao 25/32 (78%); elemento 69/77 (90%); tipo 68/77 (88%); inventado 1
- **d2_facto** n=29; valor 25/29 (86%); pagina 5/7 (71%); valor_e_pagina 4/7 (57%); citacao_contem 4/7 (57%); inventado 1; perdido 1


## The checker over round 12 (generator/guard.py, 2026-11-05 23:50 UTC)

d1 1145 checked / 0 refused · d2 1190 / 0 · stranger 106 / 1 refused (valor fora da citação: Valongo cost «49 977,00» quoted from a
sentence that does not hold it). After the checker: elements 69/77, facts 24/29. Cost: 35 539 s of H100 ≈ USD 39 + reads ≈ 1.

| run | el w1 | el w2 | el w3 | fact w1 | fact w2 | fact w3 | el total | fact total |
|---|---|---|---|---|---|---|---|---|
| ceiling | 12/12 | 32/33 | 32/32 | 7/8 | 12/13 | 8/8 | 76/77 | 27/29 |
| r10 | 11/12 | 30/33 | 26/32 | 6/8 | 12/13 | 7/8 | 67/77 | 25/29 |
| r11 | 12/12 | 32/33 | 30/32 | 5/8 | 12/13 | 5/8 | 74/77 | 22/29 |
| r12 | 10/12 | 32/33 | 27/32 | 5/8 | 11/13 | 8/8 | 69/77 | 24/29 |

r12 right where r11 wrong: 4; r12 wrong where r11 right: 7. The seven: five termos de responsabilidade (OA author, OA coordinator,
OA works director, Setúbal author, Setúbal works director) answered «not an element», one price list (Vagos), one drawn piece
(Nazaré stands map); the Valongo cost refused by the checker. The four gains are the wave-3 facts (8/8, back to the ceiling) and
the fogos/pisos values. The rebalanced real D2 rows fixed the facts, as intended, and the ×6 repetition of 42 real fact rows
taught the reader that the one-page real termos are "about" documents: the five termos it lost are exactly the shape the real
training set has few positives for (the OA minutas were keyed as elements in r11's set; the rebalanced file dropped the absent
questions on them).

Verdict: round 12 is not adopted. Elements are the backbone of the verdict (presence per slot); facts are compared by code and a
missing value is filed as not read, never guessed. r11 stays the reader behind the product. Product-level check (sealed + exam
read with r12, engine/reads-r12/) recorded in docs/REPORT-2026-10-28.md when it lands.
