# LLM evaluation: gemini-3.8-flash

40 answers (38 scored for citations, 2 "not in the corpus").
Models used: gemini-3.1-flash-lite x40.

| metric | value |
|---|---|
| citation precision (cited in gold+acceptable / cited) | 93% |
| citation recall (gold cited / gold) | 99% |
| gold article present in the prompt context | 99% |
| answers with no accepted citation | 0% |
| rejected-citation rate (invented ids / all cited) | 0% |
| questions with at least one rejected citation | 0 |
| reply was not valid JSON | 0 |
| not-in-corpus: answer declines (heuristic regex) | 2 / 2 |
| not-in-corpus: cited nothing | 2 / 2 |
| latency mean / median / max (s) | 17.9 / 17.2 / 30.4 |

## By document

| document | n | citation precision | citation recall | gold in context |
|---|---|---|---|---|
| DP | 3 | 100% | 100% | 100% |
| PR | 24 | 96% | 98% | 98% |
| PS | 7 | 83% | 100% | 100% |
| PTC | 4 | 83% | 100% | 100% |

## By language

| language | n | citation precision | citation recall | gold in context |
|---|---|---|---|---|
| en | 17 | 95% | 100% | 100% |
| it | 21 | 90% | 98% | 98% |

## Questions with missed gold or rejected citations

| id | gold | cited | rejected | gold in context |
|---|---|---|---|---|
| q04 | PR-art-6, PR-art-17 | PR-art-6 |  | 50% |

