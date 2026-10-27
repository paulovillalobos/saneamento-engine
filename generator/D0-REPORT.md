# D0 report

seed 20261027; passages covered 762 (every passage in training; the sealed set is one held-out phrasing per task plus nao_sei probes)

| task | train | sealed |
|---|---|---|
| alinea_de | 203 | 203 |
| elemento_doc | 184 | 92 |
| exigencia | 232 | 116 |
| localiza | 1183 | 539 |
| proibido | 36 | 18 |
| transcreve | 1813 | 604 |

total train 3651, sealed 1572; every `citacao` is a verbatim passage of structure/*.json (checked by generator/check_d0.py); nao_sei probes: train 262, sealed 52.
