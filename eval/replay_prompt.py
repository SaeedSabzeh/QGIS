"""Count the adjudicated article IDs actually present in each built prompt."""

import argparse
import inspect
import sys
from pathlib import Path


def run(root):
    sys.path.insert(0, str(root / "eval"))
    import run_eval as evaluation

    from core import prompts, retrieval

    rewrite_file = root / "eval/results/llm_gemini-3.8-flash_2026-11-06.jsonl"
    rewrites = evaluation.load_replay(rewrite_file)
    questions, cache = evaluation.load_questions(), evaluation.load_cache()
    by_id = retrieval.articles_by_id()
    keeps_original = "original_question" in inspect.signature(retrieval.retrieve).parameters
    for mode in ("question text", "archived keywords"):
        covered = total = complete = assessed = 0
        missing = {}
        for question in questions:
            gold = set(question.get("gold_articles", []))
            if not gold:
                continue
            text = question["question"]
            keywords = rewrites.get(question["id"], text) if mode == "archived keywords" else text
            raw = evaluation.get_raw(question.get("point"), cache, offline=True)
            optional = {"original_question": text} if keeps_original else {}
            found = retrieval.retrieve(raw, keywords, **optional)
            prompt = prompts.build_answer_prompt(
                text, found["findings"], [by_id[aid] for aid in found["ids"]],
                keywords=keywords, provenance=found["provenance"])
            sent = set(prompt["article_ids"])
            covered += len(gold & sent)
            total += len(gold)
            complete += gold <= sent
            assessed += 1
            if gold - sent:
                missing[question["id"]] = sorted(gold - sent)
        print(f"{mode}: {covered}/{total} article targets, {complete}/{assessed} complete questions")
        print("Omitted targets:", missing)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    run(parser.parse_args().source.resolve())
