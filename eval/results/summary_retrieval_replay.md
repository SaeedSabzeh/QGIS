# Retrieval evaluation

Keywords: keywords from eval/results/llm_gemini-3.8-flash_2026-11-05.jsonl (replayed, question text where missing). 38 questions scored (2 "not in the corpus" left out), 9 with a point.

Ranking: mapped governing articles first (then general, explanatory, candidate), then BM25 order (normative before explanatory). recall is fractional over the gold ids.

## Overall (map where a point is given, plus BM25)

| metric | value |
|---|---|
| recall@5 | 80% |
| recall@10 | 89% |
| MRR | 0.716 |
| hit@5 | 82% |
| hit@5 incl. acceptable | 84% |
| gold in the real prompt (5 extras with a point, 8 without) | 99% |

## Contribution of the map (BM25 alone vs map + BM25)

| subset | n | BM25 recall@5 | map+BM25 recall@5 | BM25 recall@10 | map+BM25 recall@10 | BM25 MRR | map+BM25 MRR | gold in real prompt (map + 5 extras, 8 without a point) |
|---|---|---|---|---|---|---|---|---|
| all scored | 38 | 88% | 80% | 99% | 89% | 0.804 | 0.716 | 99% |
| questions with a point | 9 | 78% | 44% | 100% | 61% | 0.696 | 0.326 | 100% |

Mapped articles per question with a point: mean 30.4, max 38 (they all go before the BM25 extras, so top-k recall with a point is lower than BM25 alone; the real prompt keeps all of them plus 5 extras).

## By document of the first gold article

| document | n | recall@5 | recall@10 | MRR |
|---|---|---|---|---|
| DP | 3 | 100% | 100% | 1.000 |
| PR | 24 | 85% | 92% | 0.787 |
| PS | 7 | 57% | 86% | 0.434 |
| PTC | 4 | 75% | 75% | 0.570 |

## By language

| language | n | recall@5 | recall@10 | MRR |
|---|---|---|---|---|
| en | 17 | 82% | 97% | 0.773 |
| it | 21 | 79% | 83% | 0.669 |

## By question type

| question type | n | recall@5 | recall@10 | MRR |
|---|---|---|---|---|
| cross | 2 | 50% | 75% | 0.571 |
| definition | 6 | 100% | 100% | 0.875 |
| parameter | 8 | 88% | 100% | 0.893 |
| paraphrase | 3 | 100% | 100% | 0.833 |
| point | 8 | 50% | 62% | 0.349 |
| procedure | 1 | 100% | 100% | 1.000 |
| rule | 10 | 85% | 95% | 0.738 |

## Misses at 5 (gold not fully in the top 5)

| id | lang | gold | top 5 ranked | MRR |
|---|---|---|---|---|
| q35 | it | PTC-art-44 | PTC-art-26, PTC-all-A, PR-art-45, PR-art-34, PR-art-1 | 0.03 |
| q12 | it | PR-art-35 | PR-art-44, PR-art-6, PR-art-8, PR-art-13, PS-art-11 | 0.03 |
| q30 | it | PS-art-12 | PTC-art-26, PTC-all-A, PR-art-45, PR-art-34, PR-art-1 | 0.03 |
| q29 | en | PS-art-8 | PR-art-44, PR-art-6, PR-art-8, PR-art-13, PS-art-11 | 0.11 |
| q11 | it | PR-art-25 | PTC-art-25, PTC-art-27, PTC-art-19, PTC-art-26, PTC-all-A | 0.12 |
| q24 | en | PS-art-11 | PR-art-9, PR-art-10, PR-art-5, PR-art-13, PR-art-33 | 0.14 |
| q37 | en | PR-art-35, PTC-art-25 | PTC-art-26, PTC-all-A, PR-art-45, PR-art-34, PR-art-1 | 0.14 |
| q04 | it | PR-art-6, PR-art-17 | PR-art-5, PR-art-6, PR-art-9, PR-art-26, PR-art-13 | 0.50 |

