# Answer correctness (LLM judge)

| metric | value |
|---|---|
| answers judged | 40 |
| mean score (points / max points) | 75% |
| fully correct (every fact scored 2) | 14 / 40 |
| hallucination flagged | 2 / 40 |

## By lang

| lang | n | mean score | hallucinations |
|---|---|---|---|
| en | 18 | 76% | 0 |
| it | 22 | 75% | 2 |

## By type

| type | n | mean score | hallucinations |
|---|---|---|---|
| cross | 2 | 42% | 0 |
| definition | 6 | 81% | 0 |
| not_in_corpus | 2 | 100% | 0 |
| parameter | 8 | 75% | 1 |
| paraphrase | 3 | 72% | 0 |
| point | 8 | 75% | 1 |
| procedure | 1 | 100% | 0 |
| rule | 10 | 73% | 0 |

## Lowest scores

| id | score | hallucination | notes |
|---|---|---|---|
| q12 | 33% | False | The answer correctly identifies the building limits for the 'Zona edificata' but fails to address the hierarchy of the PTC over the PGT and omits the requirements for the 'Zona di riorganizzazione funzionale'. |
| q24 | 33% | False | The answer correctly addresses the base index but omits the mandatory requirements for additional floor area. |
| q36 | 33% | False | The answer correctly identifies the prohibition on new construction but fails to address the rules for existing buildings or the scope of the protected areas. |
| q37 | 33% | False | The answer correctly identifies the hierarchy of the PTC but fails to mention the specific constraints for the agricultural belt or the version of the PTC. |
| q07 | 50% | False | The answer correctly identifies the allowed interventions but incorrectly adds 'new construction' and fails to mention the relevant tables. |
| q21 | 50% | False | The answer correctly identifies the prohibitions but misses the specific definition of the class and the restriction on land morphology. |
| q38 | 50% | False | The answer correctly identifies the 100m restriction but misses the hierarchical relationship between the PTC and PGT. |
| q05 | 50% | False | The answer fails to address the requirement for service areas when building works are involved and unnecessarily restricts the scope of the first fact. |

