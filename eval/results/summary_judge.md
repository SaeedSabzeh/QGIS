# Answer correctness (LLM judge)

| metric | value |
|---|---|
| answers judged | 38 |
| mean score (points / max points) | 79% |
| fully correct (every fact scored 2) | 17 / 38 |
| hallucination flagged | 1 / 38 |

## By lang

| lang | n | mean score | hallucinations |
|---|---|---|---|
| en | 17 | 79% | 0 |
| it | 21 | 79% | 1 |

## By type

| type | n | mean score | hallucinations |
|---|---|---|---|
| cross | 2 | 33% | 0 |
| definition | 6 | 89% | 0 |
| not_in_corpus | 1 | 100% | 0 |
| parameter | 8 | 66% | 0 |
| paraphrase | 3 | 78% | 0 |
| point | 8 | 81% | 1 |
| procedure | 1 | 100% | 0 |
| rule | 9 | 87% | 0 |

## Lowest scores

| id | score | hallucination | notes |
|---|---|---|---|
| q03 | 33% | False | The answer correctly identifies the base index but fails to provide the maximum thresholds requested. |
| q12 | 33% | False | The answer correctly identifies the building limits for the 'Zona edificata' but fails to address the primacy of the PTC and omits the rules for the 'Zona di riorganizzazione funzionale'. |
| q24 | 33% | False | The answer correctly answers the main question about the basic 0.35 index, but omits the rules for floor area beyond that index. |
| q37 | 33% | False | The answer correctly identifies the hierarchy of the plans but misses the specific qualitative requirements for the agricultural belt and the versioning of the PTC. |
| q38 | 33% | False | The answer failed to provide the specific regulatory constraints requested, despite them being key facts. |
| q19 | 50% | False | The answer correctly identifies the depth ranges but fails to mention the specific map where this zoning is located. |
| q02 | 67% | False | The answer correctly identifies the rules for projections but omits the definition of SCOP. |
| q04 | 67% | False | The answer is accurate regarding the index and conditions but misses the definition of the high accessibility areas. |

