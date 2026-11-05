# LLM evaluation: gemini-3.8-flash

40 answers (38 scored for citations, 2 "not in the corpus").
Models used: gemini-3.1-flash-lite x37, gemini-3.5-flash x3.

| metric | value |
|---|---|
| citation precision (cited in gold+acceptable / cited) | 96% |
| citation recall (gold cited / gold) | 92% |
| gold article present in the prompt context | 93% |
| answers with no accepted citation | 3% |
| rejected-citation rate (invented ids / all cited) | 0% |
| questions with at least one rejected citation | 0 |
| reply was not valid JSON | 0 |
| not-in-corpus: answer declines (heuristic regex) | 2 / 2 |
| not-in-corpus: cited nothing | 2 / 2 |
| latency mean / median / max (s) | 33.3 / 27.1 / 86.7 |

## By document

| document | n | citation precision | citation recall | gold in context |
|---|---|---|---|---|
| DP | 3 | 100% | 100% | 100% |
| PR | 24 | 98% | 94% | 94% |
| PS | 7 | 93% | 86% | 86% |
| PTC | 4 | 83% | 88% | 100% |

## By language

| language | n | citation precision | citation recall | gold in context |
|---|---|---|---|---|
| en | 17 | 98% | 94% | 94% |
| it | 21 | 94% | 90% | 93% |

## Questions with missed gold or rejected citations

| id | gold | cited | rejected | gold in context |
|---|---|---|---|---|
| q04 | PR-art-6, PR-art-17 | PR-art-6 |  | 50% |
| q11 | PR-art-25 |  |  | 0% |
| q24 | PS-art-11 | PR-art-33 |  | 0% |
| q38 | PTC-art-42, PR-art-50 | PR-art-35, PTC-art-42 |  | 100% |

