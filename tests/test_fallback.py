"""Model fallback timing / ordering, Retry-After capping and progress messages.

Everything is offline and uses a fake clock: the fake transport and the fake sleep advance it,
so nothing really waits.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from core import ask, llm, pipeline  # noqa: E402

OK = {"candidates": [{"content": {"parts": [{"text": '{"answer_it": "x"}'}]}}]}


class World:
    """Fake clock + scripted transport. Each step: (seconds_taken, reply_or_exception)."""

    def __init__(self, *steps):
        self.now = 0.0
        self.steps = list(steps)
        self.calls = []   # (model, timeout_given)
        self.sleeps = []

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds

    def transport(self, url, headers, payload, timeout):
        model = url.split("/models/")[1].split(":")[0]
        self.calls.append((model, timeout))
        took, step = self.steps.pop(0) if self.steps else (0.0, llm.LLMError("x", transient=True))
        # a hung request is cut off by its timeout
        self.now += min(took, timeout)
        if isinstance(step, Exception):
            raise step
        return step

    def client(self, **kw):
        return llm.GeminiClient("k", model="p", fallbacks=("f1", "f2"), transport=self.transport,
                                sleep=self.sleep, clock=self.clock, rng=lambda: 1.0, **kw)


HANG = (10 ** 6, llm.LLMError("request failed: timed out", transient=True))


def busy(status=503, retry_after=None, took=0.2):
    return (took, llm.LLMError("HTTP %s" % status, status=status, retry_after=retry_after,
                               transient=status in llm.TRANSIENT_STATUSES))


def test_timeout_goes_straight_to_next_model_without_retry():
    w = World(HANG, HANG, (1.0, OK))
    msgs = []
    c = w.client()
    assert c.complete({"user": "U"}, on_progress=msgs.append) == '{"answer_it": "x"}'
    assert [m for m, _ in w.calls] == ["p", "f1", "f2"]
    assert w.sleeps == []  # a slow failure is never retried on the same model
    assert c.last_model == "f2"
    # 20 s for the first two models, the generous timeout only for the last one
    assert [t for _, t in w.calls] == [20.0, 20.0, 25.0]
    assert w.now == 20 + 20 + 1
    assert msgs == ["Trying p...", "p not responding, trying f1...",
                    "f1 not responding, trying f2..."]


def test_last_model_gets_full_timeout_when_time_allows():
    w = World(busy(), busy(), (1.0, OK))   # p: 503 twice (fast), f1 answers
    c = w.client()
    c.complete({"user": "U"})
    assert [m for m, _ in w.calls] == ["p", "p", "f1"]
    one = llm.GeminiClient("k", model="solo", fallbacks=(), transport=w.transport,
                           sleep=w.sleep, clock=w.clock, rng=lambda: 1.0)
    w.steps = [(1.0, OK)]
    one.complete({"user": "U"})
    assert w.calls[-1] == ("solo", llm.DEFAULT_LAST_TIMEOUT)


def test_503_gets_one_quick_retry_then_falls_back():
    w = World(busy(), busy(), (1.0, OK))
    msgs = []
    c = w.client()
    c.complete({"user": "U"}, on_progress=msgs.append)
    assert [m for m, _ in w.calls] == ["p", "p", "f1"]
    assert w.sleeps == [2.0] and 1.0 <= w.sleeps[0] <= 2.0 + 1e-9
    assert msgs == ["Trying p...", "p busy, trying f1..."]


def test_404_falls_back_immediately_and_says_unavailable():
    w = World((0.1, llm.LLMError("HTTP 404", status=404)), (1.0, OK))
    msgs = []
    w.client().complete({"user": "U"}, on_progress=msgs.append)
    assert [m for m, _ in w.calls] == ["p", "f1"] and w.sleeps == []
    assert msgs[-1] == "p unavailable, trying f1..."


def test_worst_case_is_capped_by_the_budget():
    w = World(HANG, HANG, HANG)
    c = w.client()
    with pytest.raises(llm.LLMError):
        c.complete({"user": "U"})
    assert [m for m, _ in w.calls] == ["p", "f1", "f2"]
    assert w.now == llm.DEFAULT_BUDGET <= 75  # 20 + 20 + 25
    assert c.last_model is None


def test_worst_case_without_hangs_is_short():
    w = World(*[busy()] * 6)
    c = w.client()
    with pytest.raises(llm.LLMError) as e:
        c.complete({"user": "U"})
    assert e.value.status == 503
    assert w.now < 10 and len(w.sleeps) == 3


def test_budget_stops_the_chain_and_reports_last_error():
    w = World(HANG, (0.0, OK))
    c = w.client(budget=21)   # only 1 s left after the first hang: not enough for another try
    with pytest.raises(llm.LLMError) as e:
        c.complete({"user": "U"})
    assert [m for m, _ in w.calls] == ["p"] and e.value.transient


def test_per_call_budget_override():
    w = World(HANG, HANG)
    c = w.client()
    with pytest.raises(llm.LLMError):
        c.complete({"user": "U"}, budget=llm.KEYWORDS_BUDGET)
    assert w.now <= llm.KEYWORDS_BUDGET and len(w.calls) == 1  # 10 s budget: first hang eats it all
    assert w.calls[0][1] == 10.0


def test_retry_after_short_is_honoured_long_is_not():
    w = World(busy(429, retry_after=4), (1.0, OK))
    w.client().complete({"user": "U"})
    assert w.sleeps == [4.0] and [m for m, _ in w.calls] == ["p", "p"]

    w = World(busy(429, retry_after=30), (1.0, OK))
    msgs = []
    w.client().complete({"user": "U"}, on_progress=msgs.append)
    assert w.sleeps == [] and [m for m, _ in w.calls] == ["p", "f1"]  # not worth waiting 30 s
    assert msgs[-1] == "p busy, trying f1..."


def test_retry_after_cap_boundary():
    w = World(busy(429, retry_after=llm.DEFAULT_MAX_DELAY), (1.0, OK))
    w.client().complete({"user": "U"})
    assert w.sleeps == [llm.DEFAULT_MAX_DELAY]


def test_non_transient_error_stops_without_progress_noise():
    w = World((0.1, llm.LLMError("HTTP 403", status=403)))
    msgs = []
    with pytest.raises(llm.LLMError) as e:
        w.client().complete({"user": "U"}, on_progress=msgs.append)
    assert e.value.status == 403 and msgs == ["Trying p..."]


def test_defaults_fit_the_target():
    assert llm.DEFAULT_MAX_ATTEMPTS == 2 and llm.DEFAULT_MAX_DELAY <= 5
    assert llm.DEFAULT_TIMEOUT == 20 and llm.DEFAULT_LAST_TIMEOUT == 45
    assert llm.DEFAULT_BUDGET + llm.KEYWORDS_BUDGET <= 75


# ---- pipeline / CLI progress ---------------------------------------------------------------
def _fetch(url, timeout):
    if "/20/" in url:
        return {"features": [{"attributes": {"AMB_URB": 23, "COD_DEST1": 100}}]}
    return {"features": []}


class ProgressClient:
    model, last_model = "fake", "fake"

    def __init__(self):
        self.calls = []

    def complete(self, parts, on_progress=None, budget=None):
        self.calls.append(budget)
        if on_progress:
            on_progress("Trying fake...")
        if "keywords" in parts["system"]:
            return '{"keywords_it": "distanze"}'
        return '{"answer_it": "a", "answer_en": "b", "cited_articles": []}'


def test_pipeline_reports_progress_in_order_with_keyword_budget():
    res = pipeline.query_point(45.4642, 9.19, fetch=_fetch)
    msgs = []
    client = ProgressClient()
    ans = pipeline.ask("distanze?", res, client, on_progress=msgs.append)
    assert ans["answer_it"] == "a"
    assert msgs == ["Preparing the search...", "Trying fake...", "Asking the model...",
                    "Trying fake..."]
    assert client.calls == [llm.KEYWORDS_BUDGET, None]
    # on_progress stays optional
    pipeline.ask("distanze?", res, ProgressClient())


def test_cli_prints_progress_to_stderr_only():
    import io
    out, err = io.StringIO(), io.StringIO()
    hits = {"point": {"lat": 0, "lon": 0}, "errors": {},
            "layers": {20: [{"AMB_URB": 23, "COD_DEST1": 100}]}}
    reply = {"candidates": [{"content": {"parts": [{"text": '{"keywords_it": "x", '
                                                            '"answer_it": "a", "answer_en": "b", '
                                                            '"cited_articles": []}'}]}}]}
    code = ask.run(["1", "2", "q"], query_fn=lambda a, b: hits,
                   transport=lambda *a: reply, env={"GEMINI_API_KEY": "k"}, out=out, err=err,
                   sleep=lambda s: None)
    assert code == 0
    assert "Trying gemini-" in err.getvalue() and "Trying gemini-" not in out.getvalue()
