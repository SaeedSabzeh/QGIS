# LLM evaluation: gemini-3.8-flash

38 answers (37 scored for citations, 1 "not in the corpus").
Models used: gemini-3.1-flash-lite x28, gemini-3.5-flash x10.

| metric | value |
|---|---|
| citation precision (cited in gold+acceptable / cited) | 84% |
| citation recall (gold cited / gold) | 93% |
| gold article present in the prompt context | 93% |
| answers with no accepted citation | 0% |
| rejected-citation rate (invented ids / all cited) | 2% |
| questions with at least one rejected citation | 1 |
| reply was not valid JSON | 0 |
| not-in-corpus: answer declines (heuristic regex) | 1 / 1 |
| not-in-corpus: cited nothing | 1 / 1 |
| latency mean / median / max (s) | 17.9 / 13.5 / 45.5 |

## By document

| document | n | citation precision | citation recall | gold in context |
|---|---|---|---|---|
| DP | 3 | 100% | 100% | 100% |
| PR | 24 | 87% | 94% | 94% |
| PS | 7 | 79% | 100% | 100% |
| PTC | 3 | 61% | 67% | 67% |

## By language

| language | n | citation precision | citation recall | gold in context |
|---|---|---|---|---|
| en | 17 | 84% | 94% | 94% |
| it | 20 | 84% | 92% | 92% |

## Questions with missed gold or rejected citations

| id | gold | cited | rejected | gold in context |
|---|---|---|---|---|
| q03 | PR-art-6 | PR-art-16, PR-art-23 |  | 0% |
| q04 | PR-art-6, PR-art-17 | PR-art-6 |  | 50% |
| q13 | PR-art-34 | PR-art-34, PR-art-13, PR-art-21, PR-art-23 | PR-art-19 | 100% |
| q38 | PTC-art-42, PR-art-50 | PR-art-35, PS-art-12, PTC-art-1, PTC-all-A |  | 0% |

Not answered yet (rerun to resume): q36, q39

