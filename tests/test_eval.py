import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import llm, retrieval  # noqa: E402

_spec = importlib.util.spec_from_file_location("run_eval", ROOT / "eval" / "run_eval.py")
ev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ev)

ALL_IDS = {a["id"] for a in retrieval.load_articles()}


# ---------------------------------------------------------------- question set
def test_questions_schema_and_ids():
    qs = ev.load_questions()
    assert len(qs) == 40
    ids = [q["id"] for q in qs]
    assert len(set(ids)) == 40
    for q in qs:
        assert q["lang"] in ("it", "en")
        assert q["question"].strip() and q["type"]
        pt = q["point"]
        assert pt is None or (len(pt) == 2 and 45.3 < pt[0] < 45.6 and 9.0 < pt[1] < 9.4)
        gold, acc = q["gold_articles"], q.get("acceptable_articles", [])
        assert len(gold) <= 3
        for aid in gold + acc:
            assert aid in ALL_IDS, (q["id"], aid)
        assert 1 <= len(q["answer_key"]) <= 4
        if not gold:
            assert q["type"] == "not_in_corpus"
            assert q["answer_key"] == ["says the supplied texts do not cover it"]
    assert sum(1 for q in qs if not q["gold_articles"]) == 2
    langs = [q["lang"] for q in qs]
    assert 12 <= langs.count("en") <= 28


def test_constraint_points():
    pts = ev.load_points()
    assert len(pts) == 20 and len({p["id"] for p in pts}) == 20
    tests = {(45.4642, 9.19), (45.4781, 9.2269), (45.5281, 9.205), (45.452, 9.176),
             (45.417, 9.235), (45.465, 9.256)}
    assert tests <= {(p["lat"], p["lon"]) for p in pts}


# ---------------------------------------------------------------- metrics
def test_metrics_toy():
    ranked = ["a", "b", "c", "d", "e", "f"]
    assert ev.recall_at_k(ranked, ["a", "f"], 5) == 0.5
    assert ev.recall_at_k(ranked, ["a", "f"], 10) == 1.0
    assert ev.recall_at_k(ranked, [], 5) is None
    assert ev.hit_at_k(ranked, ["x", "c"], 3) == 1.0
    assert ev.hit_at_k(ranked, ["f"], 5) == 0.0
    assert ev.reciprocal_rank(ranked, ["c", "e"]) == 1 / 3
    assert ev.reciprocal_rank(ranked, ["z"]) == 0.0
    assert ev.citation_scores(["a", "x"], ["a", "b"], ["x"]) == (1.0, 0.5)
    assert ev.citation_scores(["x", "y"], ["a"]) == (0.0, 0.0)
    assert ev.citation_scores([], ["a"]) == (None, 0.0)
    assert ev.citation_scores(["a"], []) == (0.0, None)
    assert ev.mean([1, None, 3]) == 2 and ev.mean([None]) is None


def test_declines_heuristic():
    assert ev.declines("", "The supplied texts do not cover this.")
    assert ev.declines("I testi forniti non contengono questa informazione.", "")
    assert not ev.declines("La fascia e' di 10 metri.", "The strip is 10 m.")


def test_llm_metrics_toy():
    recs = [
        {"id": "a", "lang": "en", "gold": ["PR-art-6"], "acceptable": ["PR-art-5"],
         "cited_articles": ["PR-art-6", "PR-art-9"], "rejected_citations": ["ZZ-art-1"],
         "context_ids": ["PR-art-6"], "answer_it": "", "answer_en": "x", "model": "m",
         "latency_s": 1.0},
        {"id": "b", "lang": "it", "gold": [], "acceptable": [], "cited_articles": [],
         "rejected_citations": [], "context_ids": [],
         "answer_en": "The supplied texts do not cover it.", "answer_it": "", "model": "m",
         "latency_s": 3.0},
    ]
    per, agg = ev.llm_metrics(recs)
    assert agg["citation_precision"] == 0.5 and agg["citation_recall"] == 1.0
    assert agg["rejected_rate"] == 1 / 3
    assert agg["nic_n"] == 1 and agg["nic_declined"] == 1 and agg["nic_cited_nothing"] == 1
    assert agg["latency_median"] == 2.0 and agg["models"] == {"m": 2}
    assert "citation precision" in ev.llm_summary(per, agg)


def test_retrieval_rows_without_network(tmp_path):
    qs = [{"id": "t1", "question": "indice di edificabilita territoriale unico", "lang": "it",
           "point": None, "gold_articles": ["PR-art-6"], "type": "x"},
          {"id": "t2", "question": "non in corpus", "lang": "it", "point": None,
           "gold_articles": [], "type": "not_in_corpus"}]
    rows = ev.retrieval_rows(qs, {}, offline=True, cache_path=tmp_path / "c.json")
    assert rows[0]["r10"] == 1.0 and rows[0]["mrr"] > 0
    assert rows[1]["r5"] is None and rows[1]["mrr"] is None
    text = ev.retrieval_summary(rows)
    assert "recall@5" in text and "BM25 alone" in text


def test_retrieval_with_cached_point():
    raw = {"point": {"lat": 1, "lon": 2},
           "layers": {"pgt_fattibilita_geo": [{"CLASSE": 2}]}, "errors": {}}
    ranked, mapped, extras = ev.rank_question(raw, "", 10)
    assert "PR-art-44" in mapped and ranked[: len(mapped)] == mapped and extras == []


# ---------------------------------------------------------------- llm mode with a fake transport
def _reply(text):
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


class FakeTransport:
    def __init__(self, fail_ids=()):
        self.calls = []
        self.fail_ids = set(fail_ids)

    def __call__(self, url, headers, payload, timeout):
        system = payload["systemInstruction"]["parts"][0]["text"]
        user = payload["contents"][0]["parts"][0]["text"]
        self.calls.append(user)
        if "search keywords" in system:
            return _reply(json.dumps({"keywords_it": "indice edificabilita territoriale"}))
        if "grader" in system:
            return _reply(json.dumps({"facts": [
                {"fact": "f1", "score": 2, "evidence": "e"},
                {"fact": "f2", "score": 1, "evidence": "e"}], "hallucination": False,
                "notes": "ok"}))
        for fid in self.fail_ids:
            if fid in user:
                raise llm.LLMError("HTTP 400 bad", status=400, transient=False)
        return _reply(json.dumps({"answer_it": "risposta", "answer_en": "answer",
                                  "cited_articles": ["PR-art-6", "ZZ-art-1"]}))


def _client(transport):
    return llm.make_client("gemini", "fake-model", api_key="k", transport=transport,
                           fallbacks=(), sleep=lambda s: None)


QS = [
    {"id": "t1", "question": "QQ-one indice di edificabilita", "lang": "it", "point": None,
     "gold_articles": ["PR-art-6"], "acceptable_articles": [], "answer_key": ["a", "b"],
     "type": "x"},
    {"id": "t2", "question": "QQ-two indice territoriale", "lang": "en", "point": None,
     "gold_articles": ["PR-art-6"], "acceptable_articles": [], "answer_key": ["a", "b"],
     "type": "x"},
]


def test_llm_mode_writes_and_resumes(tmp_path):
    out = tmp_path / "llm_fake.jsonl"
    logs = []
    t1 = FakeTransport(fail_ids=["QQ-two"])
    written, failed = ev.run_llm(QS, _client(t1), out, {}, log=logs.append)
    assert [r["id"] for r in written] == ["t1"] and failed == ["t2"]
    rows = ev.read_jsonl(out)
    assert len(rows) == 1
    r = rows[0]
    assert r["rejected_citations"] == ["ZZ-art-1"] and "PR-art-6" in r["cited_articles"]
    assert r["model"] == "fake-model" and r["latency_s"] >= 0 and r["keywords"]
    assert r["answer_it"] == "risposta" and r["answer_en"] == "answer"
    # resume: only the failed question is asked again
    t2 = FakeTransport()
    written, failed = ev.run_llm(QS, _client(t2), out, {}, log=logs.append)
    assert [r["id"] for r in written] == ["t2"] and not failed
    assert not any("QQ-one" in c for c in t2.calls)
    assert len(ev.read_jsonl(out)) == 2
    per, agg = ev.llm_metrics(ev.read_jsonl(out))
    assert agg["n"] == 2 and agg["questions_with_rejected"] == 2


def test_llm_mode_sleep_option(tmp_path):
    waits = []
    ev.run_llm(QS, _client(FakeTransport()), tmp_path / "o.jsonl", {}, sleep=2.5,
               sleep_fn=waits.append, log=lambda m: None)
    assert waits == [2.5]


def test_judge_mode_with_fake_transport(tmp_path):
    src = tmp_path / "llm.jsonl"
    ev.run_llm(QS, _client(FakeTransport()), src, {}, log=lambda m: None)
    out = tmp_path / "judge.jsonl"
    rubric = (ROOT / "eval" / "rubric.md").read_text(encoding="utf-8")
    written, failed = ev.run_judge(ev.read_jsonl(src), QS, _client(FakeTransport()), out, rubric,
                                   log=lambda m: None)
    assert len(written) == 2 and not failed
    assert written[0]["scores"] == [2, 1] and written[0]["fraction"] == 0.75
    text = ev.judge_summary(ev.read_jsonl(out))
    assert "mean score" in text
    again, _ = ev.run_judge(ev.read_jsonl(src), QS, _client(FakeTransport()), out, rubric,
                            log=lambda m: None)
    assert again == []


def test_parse_judge_rejects_bad_reply():
    with pytest.raises(ValueError):
        ev.parse_judge('{"facts": [{"score": 5}]}', 1)
    with pytest.raises(ValueError):
        ev.parse_judge('{"facts": []}', 2)


def test_constraints_run_with_fake_fetch(tmp_path):
    def fetch(url, timeout):
        if "/12/" in url:
            return {"features": [{"attributes": {"COD_NUC": 15}}]}
        return {"features": []}
    pts = [{"id": "p", "name": "x", "lat": 45.46, "lon": 9.19}]
    res = ev.run_constraints(pts, {}, fetch=fetch, cache_path=tmp_path / "c.json")
    assert res[0]["findings"] and "PR-art-18" in res[0]["articles"]
    md = ev.checklist_md(res)
    assert "NOT VERIFIED" in md and "45.46000" in md and "- [ ] zoning" in md
