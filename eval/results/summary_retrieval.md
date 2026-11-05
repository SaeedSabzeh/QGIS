# Retrieval evaluation

Keywords: question text as keywords (no LLM rewrite). 38 questions scored (2 "not in the corpus" left out), 9 with a point.

Ranking: mapped governing articles first (then general, explanatory, candidate), then BM25 order (normative before explanatory). recall is fractional over the gold ids.

## Overall (map where a point is given, plus BM25)

| metric | value |
|---|---|
| recall@5 | 72% |
| recall@10 | 83% |
| MRR | 0.623 |
| hit@5 | 74% |
| hit@5 incl. acceptable | 82% |
| gold in the real prompt (5 extras) | 86% |

## Contribution of the map (BM25 alone vs map + BM25)

| subset | n | BM25 recall@5 | map+BM25 recall@5 | BM25 recall@10 | map+BM25 recall@10 | BM25 MRR | map+BM25 MRR | gold in real prompt (map + 5 extras) |
|---|---|---|---|---|---|---|---|---|
| all scored | 38 | 79% | 72% | 89% | 83% | 0.716 | 0.623 | 86% |
| questions with a point | 9 | 72% | 44% | 89% | 61% | 0.718 | 0.327 | 100% |

Mapped articles per question with a point: mean 30.4, max 38 (they all go before the BM25 extras, so top-k recall with a point is lower than BM25 alone; the real prompt keeps all of them plus 5 extras).

## By document of the first gold article

| document | n | recall@5 | recall@10 | MRR |
|---|---|---|---|---|
| DP | 3 | 100% | 100% | 1.000 |
| PR | 24 | 81% | 83% | 0.664 |
| PS | 7 | 57% | 86% | 0.501 |
| PTC | 4 | 25% | 62% | 0.311 |

## By language

| language | n | recall@5 | recall@10 | MRR |
|---|---|---|---|---|
| en | 17 | 65% | 85% | 0.557 |
| it | 21 | 79% | 81% | 0.677 |

## By question type

| question type | n | recall@5 | recall@10 | MRR |
|---|---|---|---|---|
| cross | 2 | 0% | 50% | 0.127 |
| definition | 6 | 83% | 83% | 0.708 |
| parameter | 8 | 62% | 88% | 0.568 |
| paraphrase | 3 | 100% | 100% | 0.778 |
| point | 8 | 50% | 62% | 0.350 |
| procedure | 1 | 100% | 100% | 1.000 |
| rule | 10 | 95% | 95% | 0.850 |

## Misses at 5 (gold not fully in the top 5)

| id | lang | gold | top 5 ranked | MRR |
|---|---|---|---|---|
| q03 | en | PR-art-6 | PTC-all-A, PR-art-29, PTC-art-26, PR-art-16, PR-art-5 | 0.00 |
| q19 | en | PR-art-43 |  | 0.00 |
| q12 | it | PR-art-35 | PR-art-44, PR-art-6, PR-art-8, PR-art-13, PS-art-11 | 0.03 |
| q30 | it | PS-art-12 | PTC-art-26, PTC-all-A, PR-art-45, PR-art-34, PR-art-1 | 0.03 |
| q35 | it | PTC-art-44 | PTC-art-26, PTC-all-A, PR-art-45, PR-art-34, PR-art-1 | 0.03 |
| q34 | en | PTC-art-42 | PTC-all-A, PS-art-12, PR-art-41, PR-art-35, PTC-art-1 | 0.10 |
| q24 | en | PS-art-11 | PR-art-41, PS-art-9, PR-art-16, PR-art-26, PR-art-33 | 0.11 |
| q29 | en | PS-art-8 | PR-art-44, PR-art-6, PR-art-8, PR-art-13, PS-art-11 | 0.11 |
| q38 | it | PTC-art-42, PR-art-50 | PR-art-35, PS-art-12, PS-art-10, PTC-all-A, PTC-art-1 | 0.11 |
| q37 | en | PR-art-35, PTC-art-25 | PTC-art-26, PTC-all-A, PR-art-45, PR-art-34, PR-art-1 | 0.14 |
| q04 | it | PR-art-6, PR-art-17 | PR-art-9, PR-art-6, PR-art-5, PR-art-16, PR-art-13 | 0.50 |

