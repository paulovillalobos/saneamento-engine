# training/runs/r11/d0.json

model amalia-llm/AMALIA-9B-0626-DPO@c4614b9b5c7b adapter amalia-saneamento-r11 answered 1531 skipped 0 load 143.4s gen 142.5s

- **alinea_de** n=203; passagem 198/203 (98%); citacao 198/203 (98%); ambos 198/203 (98%); nao_sei 1
- **elemento_doc** n=91; passagem 89/91 (98%); citacao 89/91 (98%); ambos 89/91 (98%); tipo 69/91 (76%)
- **exigencia** n=116; passagem 109/116 (94%); citacao 108/116 (93%); ambos 108/116 (93%); exigido 61/116 (53%); nao_sei 4
- **localiza** n=492; passagem 473/492 (96%); citacao 471/492 (96%); ambos 469/492 (95%); inventado 5; probes nao_sei 42/47
- **proibido** n=30; passagem 28/30 (93%); citacao 29/30 (97%); ambos 28/30 (93%); resposta 25/30 (83%)
- **transcreve** n=491; passagem 486/491 (99%); citacao 485/491 (99%); ambos 485/491 (99%); inventado 13; nao_sei 3; probes nao_sei 48/61

# training/runs/r11/d1.json

model amalia-llm/AMALIA-9B-0626-DPO@c4614b9b5c7b adapter amalia-saneamento-r11 answered 1145 skipped 0 load 148.5s gen 106.9s

- **d1_elemento** n=1145; citacao 1071/1071 (100%); elemento 1145/1145 (100%); tipo 1145/1145 (100%)

# training/runs/r11/d2.json

model amalia-llm/AMALIA-9B-0626-DPO@c4614b9b5c7b adapter amalia-saneamento-r11 answered 1190 skipped 0 load 146.3s gen 69.0s

- **d2_facto** n=1190; valor 1190/1190 (100%); pagina 1035/1035 (100%); valor_e_pagina 1035/1035 (100%); citacao_contem 1035/1035 (100%)

# training/runs/r11/stranger.json

model amalia-llm/AMALIA-9B-0626-DPO@c4614b9b5c7b adapter amalia-saneamento-r11 answered 106 skipped 0 load 142.8s gen 102.8s

- **d1_elemento** n=77; citacao 29/32 (91%); elemento 74/77 (96%); tipo 74/77 (96%)
- **d2_facto** n=29; valor 22/29 (76%); pagina 1/7 (14%); valor_e_pagina 0/7 (0%); citacao_contem 1/7 (14%); perdido 6


# Checker (generator/guard.py CLI → *-checked.json)

sealed D1 0 refused, sealed D2 0 refused, stranger 0 refused (round 10: 2 refused).

# Stranger test per wave (scratchpad script over *-checked.json; el = element id right, fact = value right, unit-tolerant)

| run | el w1 | el w2 | el w3 | fact w1 | fact w2 | fact w3 | el total | fact total | w3 total |
|---|---|---|---|---|---|---|---|---|---|
| ceiling (Opus, no training) | 12/12 | 32/33 | 32/32 | 7/8 | 12/13 | 8/8 | 76/77 | 27/29 | 40/40 |
| r9 (11k view) | 8/12 | 26/33 | 27/32 | 6/8 | 12/13 | 7/8 | 61/77 | 25/29 | 34/40 |
| r10 (whole documents) | 11/12 | 30/33 | 26/32 | 6/8 | 12/13 | 7/8 | 67/77 | 25/29 | 33/40 |
| **r11 (real documents ×6)** | 12/12 | 32/33 | 30/32 | 5/8 | 12/13 | 5/8 | **74/77** | **22/29** | **35/40** |

r11 right where r10 wrong: 8 rows; r11 wrong where r10 right: 4 rows.

Misses (10): 3 elements → null (Vila do Conde estimativa 27.f, Nazaré bancadas 27.b.iv, Vagos lista de preços 27.f);
6 facts → null where the document holds the value (Valongo cost + area ×2, Lagos 1.900,00, Santiago do Cacém 181.182,57,
Vagos 2.963.691,24 €, Valpaços use); 1 quote with a trailing ellipsis (OA termo, value right). Cause of the six: the real
training set carried 229 absent-fact rows against 1 fact with a value (two absent questions per document, almost no
keyed values), repeated 6× = 1,374 "not present" fact rows in the mix.
