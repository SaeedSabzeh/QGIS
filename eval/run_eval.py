"""Phase 4 evaluation: retrieval recall, LLM citation accuracy, LLM-as-judge, constraint points.

    python eval/run_eval.py --mode retrieval [--keywords question|gold-free] [--keywords-from F.jsonl]
    python eval/run_eval.py --mode llm --provider gemini --model gemini-3.8-flash [--sleep 4]
    python eval/run_eval.py --mode judge --provider gemini --model gemini-3.8-flash [--input F.jsonl]
    python eval/run_eval.py --mode constraints          # live query of the 20 points, writes checklist

Ranking used for recall@k and MRR (retrieval mode). For a question we run core.retrieval.retrieve
the way core.pipeline.ask does before the LLM call:
  1. the articles mapped from the point's findings, in role order: governing (`articles`), then
     general, explanatory, candidate (each in the order of the zone/constraint map);
  2. then the BM25 extras for the keyword string, normative documents before explanatory ones,
     score order inside each group (retrieve() does this partition).
Questions without a point have no mapped articles, so the ranking is the BM25 order alone.
Extras are taken with k=10 so that the list is long enough for recall@10; the real prompt uses
the first retrieval.extras_k() extras, 5 with mapped articles and 8 without (reported as "in prompt"). Questions with `gold_articles: []` ("not in the
corpus") are left out of the retrieval metrics. Gold-only recall is fractional per question
(|gold in top k| / |gold|); "hit" counts a question when at least one gold article is in the
top k; "hit+acc" also accepts `acceptable_articles`.

Point results (the raw ArcGIS answers) are cached in eval/results/point_cache.json so that runs
are repeatable and offline after the first time; `--refresh` queries again.
"""

import argparse
import datetime
import glob
import json
import os
import re
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import llm, pipeline, retrieval, services  # noqa: E402

EVAL_DIR = ROOT / "eval"
RESULTS_DIR = EVAL_DIR / "results"
QUESTIONS_FILE = EVAL_DIR / "questions.yaml"
POINTS_FILE = EVAL_DIR / "constraint_points.yaml"
CACHE_FILE = RESULTS_DIR / "point_cache.json"
RUBRIC_FILE = EVAL_DIR / "rubric.md"
CHECKLIST_FILE = EVAL_DIR / "constraint_checklist.md"

VIEWER_LOMBARDIA = "https://www.geoportale.regione.lombardia.it/"
VIEWER_MILANO = "https://geoportale.comune.milano.it/"


def today():
    return datetime.date.today().isoformat()


# ---------------------------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------------------------
def _yaml():
    try:
        import yaml
    except ImportError:  # pragma: no cover
        sys.exit("PyYAML is needed for the evaluation (pip install pyyaml)")
    return yaml


def load_questions(path=QUESTIONS_FILE):
    with open(path, encoding="utf-8") as fh:
        return _yaml().safe_load(fh)


def load_points(path=POINTS_FILE):
    with open(path, encoding="utf-8") as fh:
        return _yaml().safe_load(fh)


def point_key(point):
    return "%.4f,%.4f" % (point[0], point[1])


def load_cache(path=CACHE_FILE):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def save_cache(cache, path=CACHE_FILE):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, ensure_ascii=False, indent=1, sort_keys=True)


def get_raw(point, cache, refresh=False, offline=False, fetch=None, cache_path=CACHE_FILE):
    """Raw `services.query_all` result for `point` (lat, lon); cached. None point -> empty."""
    if point is None:
        return {"point": None, "layers": {}, "errors": {}}
    key = point_key(point)
    if key in cache and not refresh:
        return cache[key]
    if offline:
        raise SystemExit("point %s is not in the cache and --offline was given" % key)
    raw = services.query_all(point[0], point[1], fetch=fetch)
    if raw.get("errors") and len(raw["errors"]) == len(raw["layers"]):
        raise SystemExit("all map layers failed for %s: %s" % (key, next(iter(raw["errors"].values()))))
    cache[key] = raw
    save_cache(cache, cache_path)
    return raw


# ---------------------------------------------------------------------------------------------
# Metrics (pure functions)
# ---------------------------------------------------------------------------------------------
def recall_at_k(ranked, gold, k):
    """Fraction of the gold ids found in the first k ranked ids (None when gold is empty)."""
    if not gold:
        return None
    top = set(ranked[:k])
    return sum(1 for g in gold if g in top) / len(gold)


def hit_at_k(ranked, targets, k):
    """1.0 when at least one target id is in the first k ranked ids, else 0.0."""
    return 1.0 if set(ranked[:k]) & set(targets) else 0.0


def reciprocal_rank(ranked, gold):
    """1 / rank of the first gold id (0 when none is ranked)."""
    for i, aid in enumerate(ranked, 1):
        if aid in gold:
            return 1.0 / i
    return 0.0


def citation_scores(cited, gold, acceptable=()):
    """(precision, recall); precision None when nothing was cited, recall None when gold is []."""
    cited = list(dict.fromkeys(cited))
    ok = set(gold) | set(acceptable)
    prec = (sum(1 for c in cited if c in ok) / len(cited)) if cited else None
    rec = (sum(1 for g in gold if g in cited) / len(gold)) if gold else None
    return prec, rec


def mean(values):
    vals = [v for v in values if v is not None]
    return (sum(vals) / len(vals)) if vals else None


def group_mean(rows, key_fn, field):
    """{group: mean of row[field]} (None values skipped)."""
    groups = {}
    for r in rows:
        groups.setdefault(key_fn(r), []).append(r.get(field))
    return {g: mean(v) for g, v in sorted(groups.items())}


def fmt(v, pct=True):
    if v is None:
        return "n/a"
    return ("%.0f%%" % (100 * v)) if pct else ("%.3f" % v)


def md_table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def gold_doc(q):
    return q["gold_articles"][0].split("-")[0] if q.get("gold_articles") else "none"


# ---------------------------------------------------------------------------------------------
# Retrieval mode
# ---------------------------------------------------------------------------------------------
def rank_question(raw, keywords, k=10, data_dir=None):
    """(ranked ids, mapped ids) for one question; see the module docstring for the ordering."""
    findings = retrieval.lookup(raw, data_dir) if raw.get("layers") else []
    ret = retrieval.retrieve(raw, keywords, k=k, findings=findings, data_dir=data_dir)
    return ret["ids"], ret["mapped"], ret["extras"]


def keywords_for(q, mode="question", replay=None):
    if replay is not None and q["id"] in replay:
        return replay[q["id"]]
    return q["question"]  # "question" and "gold-free": no rewrite, the question text itself


def load_replay(path):
    """{id: keywords} from an llm jsonl written by --mode llm."""
    out = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                r = json.loads(line)
                if r.get("keywords"):
                    out[r["id"]] = r["keywords"]
    return out


def retrieval_rows(questions, cache, keywords_mode="question", replay=None, refresh=False,
                   offline=False, fetch=None, data_dir=None, cache_path=CACHE_FILE):
    rows = []
    for q in questions:
        gold, acc = q.get("gold_articles") or [], q.get("acceptable_articles") or []
        kw = keywords_for(q, keywords_mode, replay)
        raw = get_raw(q.get("point"), cache, refresh, offline, fetch, cache_path)
        ranked, mapped, extras = rank_question(raw, kw, 10, data_dir)
        base_ranked, _, _ = rank_question(get_raw(None, cache), kw, 10, data_dir)
        in_prompt = set(mapped) | set(extras[:retrieval.extras_k(len(mapped))])
        row = {
            "id": q["id"], "lang": q["lang"], "doc": gold_doc(q), "type": q.get("type"),
            "has_point": bool(q.get("point")), "gold": gold, "ranked": ranked[:10],
            "mapped": mapped, "bm25_ranked": base_ranked[:10], "keywords": kw,
            "r5": recall_at_k(ranked, gold, 5), "r10": recall_at_k(ranked, gold, 10),
            "mrr": reciprocal_rank(ranked, gold) if gold else None,
            "hit5": hit_at_k(ranked, gold, 5) if gold else None,
            "hit5_acc": hit_at_k(ranked, gold + acc, 5) if gold else None,
            "in_prompt": (sum(1 for g in gold if g in in_prompt) / len(gold)) if gold else None,
            "bm25_r5": recall_at_k(base_ranked, gold, 5),
            "bm25_r10": recall_at_k(base_ranked, gold, 10),
            "bm25_mrr": reciprocal_rank(base_ranked, gold) if gold else None,
        }
        rows.append(row)
    return rows


def retrieval_summary(rows, label="question text as keywords"):
    scored = [r for r in rows if r["gold"]]
    lines = ["# Retrieval evaluation", "",
             "Keywords: %s. %d questions scored (%d \"not in the corpus\" left out), %d with a point."
             % (label, len(scored), len(rows) - len(scored),
                sum(1 for r in scored if r["has_point"])), "",
             "Ranking: mapped governing articles first (then general, explanatory, candidate), then "
             "BM25 order (normative before explanatory). recall is fractional over the gold ids.", ""]
    all_cols = [("recall@5", "r5"), ("recall@10", "r10"), ("MRR", "mrr"),
                ("hit@5", "hit5"), ("hit@5 incl. acceptable", "hit5_acc"),
                ("gold in the real prompt (5 extras with a point, 8 without)", "in_prompt")]
    lines += ["## Overall (map where a point is given, plus BM25)", "",
              md_table(["metric", "value"], [
                  [name, fmt(mean(r[f] for r in scored), pct=(f != "mrr"))
                   if f != "mrr" else fmt(mean(r[f] for r in scored), pct=False)]
                  for name, f in all_cols]), ""]
    pts = [r for r in scored if r["has_point"]]
    lines += ["## Contribution of the map (BM25 alone vs map + BM25)", "",
              md_table(["subset", "n", "BM25 recall@5", "map+BM25 recall@5", "BM25 recall@10",
                        "map+BM25 recall@10", "BM25 MRR", "map+BM25 MRR", "gold in real prompt (map + 5 extras, 8 without a point)"], [
                  ["all scored", len(scored), fmt(mean(r["bm25_r5"] for r in scored)),
                   fmt(mean(r["r5"] for r in scored)), fmt(mean(r["bm25_r10"] for r in scored)),
                   fmt(mean(r["r10"] for r in scored)), fmt(mean(r["bm25_mrr"] for r in scored), False),
                   fmt(mean(r["mrr"] for r in scored), False), fmt(mean(r["in_prompt"] for r in scored))],
                  ["questions with a point", len(pts), fmt(mean(r["bm25_r5"] for r in pts)),
                   fmt(mean(r["r5"] for r in pts)), fmt(mean(r["bm25_r10"] for r in pts)),
                   fmt(mean(r["r10"] for r in pts)), fmt(mean(r["bm25_mrr"] for r in pts), False),
                   fmt(mean(r["mrr"] for r in pts), False), fmt(mean(r["in_prompt"] for r in pts))]]),
              "", "Mapped articles per question with a point: mean %.1f, max %d (they all go before the "
              "BM25 extras, so top-k recall with a point is lower than BM25 alone; the real prompt keeps "
              "all of them plus 5 extras)." % (
                  mean(len(r["mapped"]) for r in pts) or 0, max([len(r["mapped"]) for r in pts] or [0])), ""]
    for title, fn in (("document of the first gold article", lambda r: r["doc"]),
                      ("language", lambda r: r["lang"]), ("question type", lambda r: r["type"])):
        groups = {}
        for r in scored:
            groups.setdefault(fn(r), []).append(r)
        lines += ["## By %s" % title, "",
                  md_table([title.split(" of")[0], "n", "recall@5", "recall@10", "MRR"], [
                      [g, len(v), fmt(mean(x["r5"] for x in v)), fmt(mean(x["r10"] for x in v)),
                       fmt(mean(x["mrr"] for x in v), False)] for g, v in sorted(groups.items())]), ""]
    misses = sorted((r for r in scored if r["r5"] < 1), key=lambda r: (r["r5"], r["mrr"]))
    lines += ["## Misses at 5 (gold not fully in the top 5)", "",
              md_table(["id", "lang", "gold", "top 5 ranked", "MRR"], [
                  [r["id"], r["lang"], ", ".join(r["gold"]), ", ".join(r["ranked"][:5]),
                   "%.2f" % r["mrr"]] for r in misses]), ""]
    return "\n".join(lines)


def cmd_retrieval(args):
    questions = load_questions()
    cache = load_cache()
    replay = load_replay(args.keywords_from) if args.keywords_from else None
    label = ("keywords from %s (replayed, question text where missing)" % args.keywords_from
             if replay else "question text as keywords (no LLM rewrite)")
    rows = retrieval_rows(questions, cache, args.keywords, replay, args.refresh, args.offline)
    text = retrieval_summary(rows, label)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    suffix = "" if not replay else "_replay"
    (RESULTS_DIR / ("summary_retrieval%s.md" % suffix)).write_text(text + "\n", encoding="utf-8")
    with open(RESULTS_DIR / ("retrieval_%s%s.json" % (today(), suffix)), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)
    print(text)


# ---------------------------------------------------------------------------------------------
# LLM mode
# ---------------------------------------------------------------------------------------------
DECLINE_PATTERNS = [
    r"do(?:es)? not (?:cover|contain|include|address|provide|specify|mention)", r"not covered",
    r"not (?:present|available|found|included|contained|addressed|specified) in",
    r"no (?:information|provision|rule|text|article)", r"outside (?:the|these) (?:supplied|provided)",
    r"cannot (?:be )?(?:answer|find|determine)", r"unable to",
    r"non (?:contengono|contiene|coprono|copre|trattano|tratta|e' presente|è presente|sono presenti|risulta|specifica)",
    r"non (?:e'|è) (?:disciplinat|previst|trattat|coperto|riportat)", r"non sono (?:disciplinat|previst|trattat|coperti)",
    r"nessuna (?:informazione|disposizione|norma|indicazione)", r"al di fuori dei testi",
    r"non (?:posso|e possibile|è possibile) (?:rispondere|determinare)",
]
_DECLINE = re.compile("|".join(DECLINE_PATTERNS), re.IGNORECASE)


def declines(answer_it, answer_en):
    """Heuristic: does the answer say that the supplied texts do not cover the question?"""
    return bool(_DECLINE.search(answer_it or "") or _DECLINE.search(answer_en or ""))


def latest_file(pattern):
    files = sorted(glob.glob(str(RESULTS_DIR / pattern)))
    return files[-1] if files else None


def read_jsonl(path):
    rows = []
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    rows.append(json.loads(line))
    return rows


def safe_name(model):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", model)


def point_result(raw):
    """What pipeline.ask needs from a click: the raw answer and the findings."""
    findings = retrieval.lookup(raw) if raw.get("layers") else []
    return {"raw": raw, "findings": findings}


def run_llm(questions, client, out_path, cache, sleep=0.0, limit=None, refresh=False,
            offline=False, fetch=None, sleep_fn=time.sleep, max_errors=5, log=print):
    """Ask every question not yet in `out_path` (jsonl), appending one record per answer.

    Failed requests (llm.LLMError) are NOT written, so a rerun retries them; the run stops after
    `max_errors` failures in a row. Returns (records written now, failed ids)."""
    done = {r["id"] for r in read_jsonl(out_path)}
    todo = [q for q in questions if q["id"] not in done]
    if limit:
        todo = todo[:limit]
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    written, failed, streak = [], [], 0
    for n, q in enumerate(todo):
        raw = get_raw(q.get("point"), cache, refresh, offline, fetch)
        t0 = time.time()
        try:
            ans = pipeline.ask(q["question"], point_result(raw), client)
        except llm.LLMError as exc:
            failed.append(q["id"])
            streak += 1
            log("  %s FAILED: %s" % (q["id"], str(exc)[:200]))
            if streak >= max_errors:
                log("stopping after %d failures in a row; rerun to resume" % streak)
                break
            continue
        streak = 0
        rec = {
            "id": q["id"], "question": q["question"], "lang": q["lang"], "point": q.get("point"),
            "gold": q.get("gold_articles") or [], "acceptable": q.get("acceptable_articles") or [],
            "answer_it": ans.get("answer_it"), "answer_en": ans.get("answer_en"),
            "cited_articles": ans.get("cited_articles", []),
            "rejected_citations": ans.get("rejected_citations", []),
            "parse_error": bool(ans.get("parse_error")), "model": ans.get("model"),
            "latency_s": round(time.time() - t0, 2), "keywords": ans.get("keywords"),
            "context_ids": [a["id"] for a in ans.get("articles", [])],
            "warnings": ans.get("warnings", []), "date": today(),
        }
        with open(out_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        written.append(rec)
        log("  %s ok (%s, %.1fs) cited=%s" % (q["id"], rec["model"], rec["latency_s"],
                                              rec["cited_articles"]))
        if sleep and n < len(todo) - 1:
            sleep_fn(sleep)
    return written, failed


def llm_metrics(records):
    """Per-record scores plus aggregates for the jsonl records of --mode llm."""
    per = []
    for r in records:
        gold, acc = r.get("gold") or [], r.get("acceptable") or []
        cited, rej = r.get("cited_articles") or [], r.get("rejected_citations") or []
        prec, rec = citation_scores(cited, gold, acc)
        ctx = r.get("context_ids") or []
        per.append({
            "id": r["id"], "lang": r["lang"], "gold": gold, "cited": cited, "rejected": rej,
            "precision": prec, "recall": rec, "n_cited": len(cited), "n_rejected": len(rej),
            "gold_in_context": (sum(1 for g in gold if g in ctx) / len(gold)) if gold else None,
            "not_in_corpus": not gold, "parse_error": bool(r.get("parse_error")),
            "declines": declines(r.get("answer_it"), r.get("answer_en")),
            "model": r.get("model"), "latency_s": r.get("latency_s"),
            "doc": gold[0].split("-")[0] if gold else "none",
        })
    scored = [p for p in per if not p["not_in_corpus"]]
    nic = [p for p in per if p["not_in_corpus"]]
    tot_c = sum(p["n_cited"] for p in per)
    tot_r = sum(p["n_rejected"] for p in per)
    lat = [p["latency_s"] for p in per if p["latency_s"] is not None]
    agg = {
        "n": len(per), "n_scored": len(scored),
        "citation_precision": mean(p["precision"] for p in scored),
        "citation_recall": mean(p["recall"] for p in scored),
        "gold_in_context": mean(p["gold_in_context"] for p in scored),
        "no_citation_rate": (sum(1 for p in scored if not p["n_cited"]) / len(scored)) if scored else None,
        "rejected_rate": (tot_r / (tot_c + tot_r)) if (tot_c + tot_r) else None,
        "questions_with_rejected": sum(1 for p in per if p["n_rejected"]),
        "parse_errors": sum(1 for p in per if p["parse_error"]),
        "nic_n": len(nic),
        "nic_declined": sum(1 for p in nic if p["declines"]),
        "nic_cited_nothing": sum(1 for p in nic if not p["n_cited"]),
        "latency_mean": statistics.mean(lat) if lat else None,
        "latency_median": statistics.median(lat) if lat else None,
        "latency_max": max(lat) if lat else None,
        "models": {m: sum(1 for p in per if p["model"] == m) for m in sorted({p["model"] for p in per if p["model"]})},
    }
    return per, agg


def llm_summary(per, agg, title="LLM evaluation"):
    lines = ["# %s" % title, "",
             "%d answers (%d scored for citations, %d \"not in the corpus\")." % (agg["n"], agg["n_scored"], agg["nic_n"]),
             "Models used: %s." % ", ".join("%s x%d" % kv for kv in agg["models"].items()), "",
             md_table(["metric", "value"], [
                 ["citation precision (cited in gold+acceptable / cited)", fmt(agg["citation_precision"])],
                 ["citation recall (gold cited / gold)", fmt(agg["citation_recall"])],
                 ["gold article present in the prompt context", fmt(agg["gold_in_context"])],
                 ["answers with no accepted citation", fmt(agg["no_citation_rate"])],
                 ["rejected-citation rate (invented ids / all cited)", fmt(agg["rejected_rate"])],
                 ["questions with at least one rejected citation", agg["questions_with_rejected"]],
                 ["reply was not valid JSON", agg["parse_errors"]],
                 ["not-in-corpus: answer declines (heuristic regex)", "%d / %d" % (agg["nic_declined"], agg["nic_n"])],
                 ["not-in-corpus: cited nothing", "%d / %d" % (agg["nic_cited_nothing"], agg["nic_n"])],
                 ["latency mean / median / max (s)", "%s / %s / %s" % tuple(
                     "n/a" if agg[k] is None else "%.1f" % agg[k]
                     for k in ("latency_mean", "latency_median", "latency_max"))]]), ""]
    scored = [p for p in per if not p["not_in_corpus"]]
    for title2, fn in (("document", lambda p: p["doc"]), ("language", lambda p: p["lang"])):
        groups = {}
        for p in scored:
            groups.setdefault(fn(p), []).append(p)
        lines += ["## By %s" % title2, "",
                  md_table([title2, "n", "citation precision", "citation recall", "gold in context"], [
                      [g, len(v), fmt(mean(x["precision"] for x in v)), fmt(mean(x["recall"] for x in v)),
                       fmt(mean(x["gold_in_context"] for x in v))] for g, v in sorted(groups.items())]), ""]
    bad = [p for p in scored if (p["recall"] or 0) < 1 or p["rejected"]]
    lines += ["## Questions with missed gold or rejected citations", "",
              md_table(["id", "gold", "cited", "rejected", "gold in context"], [
                  [p["id"], ", ".join(p["gold"]), ", ".join(p["cited"]), ", ".join(p["rejected"]),
                   fmt(p["gold_in_context"])] for p in bad]), ""]
    return "\n".join(lines)


def cmd_llm(args):
    key = os.environ.get("GEMINI_API_KEY", "") if args.provider == "gemini" else None
    if args.provider == "gemini" and not key:
        sys.exit("GEMINI_API_KEY is not set in the environment")
    fallbacks = tuple(f for f in (args.fallbacks or "").split(",") if f) if args.fallbacks is not None \
        else llm.DEFAULT_GEMINI_FALLBACKS
    client = llm.make_client(args.provider, args.model, api_key=key, fallbacks=fallbacks)
    model = args.model or client.model
    out = args.out or latest_file("llm_%s_*.jsonl" % safe_name(model)) \
        or str(RESULTS_DIR / ("llm_%s_%s.jsonl" % (safe_name(model), today())))
    print("writing to %s (resumes: %d done)" % (out, len(read_jsonl(out))))
    questions = load_questions()
    cache = load_cache()
    written, failed = run_llm(questions, client, out, cache, sleep=args.sleep, limit=args.limit,
                              refresh=args.refresh, offline=args.offline)
    per, agg = llm_metrics(read_jsonl(out))
    text = llm_summary(per, agg, "LLM evaluation: %s" % model)
    if failed:
        text += "\nNot answered yet (rerun to resume): %s\n" % ", ".join(failed)
    (RESULTS_DIR / "summary_llm.md").write_text(text + "\n", encoding="utf-8")
    print(text)


# ---------------------------------------------------------------------------------------------
# Judge mode (LLM as judge, rubric in eval/rubric.md)
# ---------------------------------------------------------------------------------------------
JUDGE_SYSTEM_TAIL = """
Reply with a single JSON object and nothing else:
{"facts": [{"fact": "<the key fact, copied>", "score": 0, "evidence": "<short quote or reason>"}, ...],
 "hallucination": false, "notes": "<one short sentence>"}
There must be exactly one entry in "facts" per key fact, in the same order. score is 0, 1 or 2."""


def build_judge_prompt(rec, answer_key, rubric):
    answer = rec.get("answer_en") or rec.get("answer_it") or ""
    user = ("QUESTION:\n%s\n\nKEY FACTS (what a correct answer must state):\n%s\n\n"
            "ANSWER TO JUDGE:\n%s\n\nARTICLES THE ANSWER CITED: %s\n\nReturn the JSON object now."
            % (rec["question"], "\n".join("%d. %s" % (i, f) for i, f in enumerate(answer_key, 1)),
               answer, ", ".join(rec.get("cited_articles") or []) or "none"))
    return {"system": rubric + "\n" + JUDGE_SYSTEM_TAIL, "user": user}


def parse_judge(text, n_facts):
    """(scores list of n_facts ints, hallucination bool, notes) from the judge reply; raises
    ValueError when it cannot be used."""
    obj = llm._extract_json(text)
    facts = obj.get("facts")
    if not isinstance(facts, list) or len(facts) != n_facts:
        raise ValueError("expected %d facts" % n_facts)
    scores = []
    for f in facts:
        s = int(f.get("score") if isinstance(f, dict) else f)
        if s not in (0, 1, 2):
            raise ValueError("score out of range")
        scores.append(s)
    return scores, bool(obj.get("hallucination")), str(obj.get("notes") or "")


def run_judge(records, questions, client, out_path, rubric, sleep=0.0, sleep_fn=time.sleep,
              max_errors=5, log=print):
    qs = {q["id"]: q for q in questions}
    done = {r["id"] for r in read_jsonl(out_path)}
    todo = [r for r in records if r["id"] not in done and r["id"] in qs]
    written, failed, streak = [], [], 0
    for n, rec in enumerate(todo):
        key = qs[rec["id"]]["answer_key"]
        try:
            text = client.complete(build_judge_prompt(rec, key, rubric))
            scores, hall, notes = parse_judge(text, len(key))
        except (llm.LLMError, ValueError, TypeError, AttributeError) as exc:
            failed.append(rec["id"])
            streak += 1
            log("  %s judge FAILED: %s" % (rec["id"], str(exc)[:200]))
            if streak >= max_errors:
                break
            continue
        streak = 0
        out = {"id": rec["id"], "scores": scores, "max": 2 * len(key),
               "fraction": sum(scores) / (2 * len(key)), "hallucination": hall, "notes": notes,
               "judge_model": client.last_model or client.model, "lang": rec["lang"],
               "type": qs[rec["id"]].get("type"), "date": today()}
        with open(out_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(out, ensure_ascii=False) + "\n")
        written.append(out)
        if sleep and n < len(todo) - 1:
            sleep_fn(sleep)
    return written, failed


def judge_summary(rows, title="Answer correctness (LLM judge)"):
    if not rows:
        return "# %s\n\nNo judged answers.\n" % title
    full = sum(1 for r in rows if r["scores"] and all(s == 2 for s in r["scores"]))
    lines = ["# %s" % title, "",
             md_table(["metric", "value"], [
                 ["answers judged", len(rows)],
                 ["mean score (points / max points)", fmt(mean(r["fraction"] for r in rows))],
                 ["fully correct (every fact scored 2)", "%d / %d" % (full, len(rows))],
                 ["hallucination flagged", "%d / %d" % (sum(1 for r in rows if r["hallucination"]), len(rows))]]), ""]
    for name in ("lang", "type"):
        groups = {}
        for r in rows:
            groups.setdefault(r.get(name), []).append(r)
        lines += ["## By %s" % name, "",
                  md_table([name, "n", "mean score", "hallucinations"], [
                      [g, len(v), fmt(mean(x["fraction"] for x in v)),
                       sum(1 for x in v if x["hallucination"])] for g, v in sorted(groups.items(), key=lambda kv: str(kv[0]))]), ""]
    weak = sorted(rows, key=lambda r: r["fraction"])[:8]
    lines += ["## Lowest scores", "",
              md_table(["id", "score", "hallucination", "notes"], [
                  [r["id"], fmt(r["fraction"]), r["hallucination"], r["notes"]] for r in weak]), ""]
    return "\n".join(lines)


def cmd_judge(args):
    key = os.environ.get("GEMINI_API_KEY", "") if args.provider == "gemini" else None
    if args.provider == "gemini" and not key:
        sys.exit("GEMINI_API_KEY is not set in the environment")
    src = args.input or latest_file("llm_*.jsonl")
    if not src:
        sys.exit("no llm_*.jsonl found: run --mode llm first or pass --input")
    fallbacks = tuple(f for f in (args.fallbacks or "").split(",") if f) if args.fallbacks is not None \
        else llm.DEFAULT_GEMINI_FALLBACKS
    client = llm.make_client(args.provider, args.model, api_key=key, fallbacks=fallbacks)
    out = args.out or str(RESULTS_DIR / ("judge_%s_%s.jsonl" % (
        re.sub(r"^llm_|_\d{4}-\d{2}-\d{2}$", "", Path(src).stem), today())))
    rubric = RUBRIC_FILE.read_text(encoding="utf-8")
    written, failed = run_judge(read_jsonl(src), load_questions(), client, out, rubric, sleep=args.sleep)
    text = judge_summary(read_jsonl(out))
    if failed:
        text += "\nNot judged yet (rerun to resume): %s\n" % ", ".join(failed)
    (RESULTS_DIR / "summary_judge.md").write_text(text + "\n", encoding="utf-8")
    print(text)


# ---------------------------------------------------------------------------------------------
# Constraints mode
# ---------------------------------------------------------------------------------------------
def summarize_findings(res):
    """Compact, human-readable view of a pipeline.query_point result."""
    out = []
    for f in res["findings"]:
        out.append({"layer": f["layer"], "category": f["category"], "label": f["label"],
                    "values": f["values"], "matched": f["matched_values"],
                    "articles": f["articles"], "general": f["general_articles"],
                    "verify": f["verify"]})
    return out


def run_constraints(points, cache, refresh=True, fetch=None, cache_path=CACHE_FILE):
    results = []
    for p in points:
        raw = get_raw([p["lat"], p["lon"]], cache, refresh, False, fetch, cache_path)
        findings = retrieval.lookup(raw)
        ret = retrieval.retrieve(raw, None, findings=findings)
        results.append({
            "id": p["id"], "name": p["name"], "lat": p["lat"], "lon": p["lon"],
            "errors": raw.get("errors", {}), "layers_total": len(raw.get("layers", {})),
            "layers_with_hits": sorted(k for k, v in raw.get("layers", {}).items() if v),
            "findings": summarize_findings({"findings": findings}),
            "articles": ret["ids"], "date": today(),
        })
    return results


def finding_line(f):
    vals = ", ".join("%s=%s" % kv for kv in f["values"].items() if kv[0] != "SCHEDA_NEW")
    art = ", ".join(f["articles"]) or "-"
    return "%s (%s) [%s] -> %s%s" % (f["label"], f["layer"], vals or "no attributes", art,
                                      " (VERIFY)" if f["verify"] else "")


def checklist_md(results):
    lines = ["# Constraint checklist (to be checked by a human)", "",
             "NOT VERIFIED. Each row is what the plugin reports for a point (live query of the regional "
             "ArcGIS services on %s). To check a point, open a viewer, go to the coordinates, switch on "
             "the PGT / Natura 2000 / PGRA layers and compare. Tick a box only after comparing." % today(),
             "",
             "Viewers (generic entry pages; type the coordinates in their search box):",
             "- Geoportale Lombardia: %s" % VIEWER_LOMBARDIA,
             "- Geoportale del Comune di Milano: %s" % VIEWER_MILANO,
             "- Each row also has an OpenStreetMap link to see where the point is.", ""]
    for r in results:
        osm = "https://www.openstreetmap.org/?mlat=%.5f&mlon=%.5f#map=17/%.5f/%.5f" % (
            r["lat"], r["lon"], r["lat"], r["lon"])
        lines += ["## %s. %s" % (r["id"], r["name"]), "",
                  "- Coordinates: lat %.5f, lon %.5f (WGS84); lat, lon for the viewer search: `%.5f, %.5f`"
                  % (r["lat"], r["lon"], r["lat"], r["lon"]),
                  "- Links: [map](%s) · [Geoportale Lombardia](%s) · [Geoportale Milano](%s)"
                  % (osm, VIEWER_LOMBARDIA, VIEWER_MILANO)]
        if r["errors"]:
            lines.append("- Layer errors (%d of %d): %s" % (len(r["errors"]), r["layers_total"],
                                                           ", ".join(sorted(r["errors"]))))
        if r["findings"]:
            lines.append("- Plugin findings:")
            lines += ["  - " + finding_line(f) for f in r["findings"]]
        else:
            lines.append("- Plugin findings: none (no layer returned a feature)")
        lines += ["- Articles shown: %s" % (", ".join(r["articles"]) or "none"),
                  "- [ ] zoning / urban fabric matches the viewer",
                  "- [ ] geological feasibility class matches",
                  "- [ ] Natura 2000 matches (hit or no hit)",
                  "- [ ] flood hazard / risk (PGRA) matches",
                  "- Notes: ", ""]
    return "\n".join(lines)


def cmd_constraints(args):
    points = load_points()
    cache = load_cache()
    results = run_constraints(points, cache, refresh=not args.offline)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / ("constraints_%s.json" % today())
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=1)
    CHECKLIST_FILE.write_text(checklist_md(results) + "\n", encoding="utf-8")
    n_err = sum(1 for r in results if r["errors"])
    n_find = sum(len(r["findings"]) for r in results)
    print("%d points, %d findings, %d points with layer errors; wrote %s and %s"
          % (len(results), n_find, n_err, path, CHECKLIST_FILE))


# ---------------------------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--mode", required=True, choices=["retrieval", "llm", "judge", "constraints"])
    ap.add_argument("--keywords", default="question", choices=["question", "gold-free"],
                    help="retrieval: keyword input; both mean the question text itself (no LLM rewrite)")
    ap.add_argument("--keywords-from", help="retrieval: replay the keywords stored in an llm_*.jsonl")
    ap.add_argument("--provider", default="gemini", choices=["gemini", "ollama"])
    ap.add_argument("--model", help="model id (default: core.llm default for the provider)")
    ap.add_argument("--fallbacks", help="comma separated Gemini fallback models; '' disables them")
    ap.add_argument("--sleep", type=float, default=0.0, help="seconds to wait between requests")
    ap.add_argument("--limit", type=int, help="llm: answer at most N new questions")
    ap.add_argument("--input", help="judge: the llm_*.jsonl to judge (default: the latest)")
    ap.add_argument("--out", help="llm/judge: output jsonl (default: results/<mode>_<model>_<date>.jsonl; "
                                  "llm resumes the latest existing file of the model)")
    ap.add_argument("--refresh", action="store_true", help="query the map services again")
    ap.add_argument("--offline", action="store_true", help="never touch the network (cache only)")
    args = ap.parse_args(argv)
    {"retrieval": cmd_retrieval, "llm": cmd_llm, "judge": cmd_judge,
     "constraints": cmd_constraints}[args.mode](args)


if __name__ == "__main__":
    main()
