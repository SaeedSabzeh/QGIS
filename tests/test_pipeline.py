import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import llm, pipeline  # noqa: E402


def _fetch(url, timeout):
    if "/20/" in url:  # TUC layer: one hit, as in Milan
        return {"features": [{"attributes": {"AMB_URB": 23, "COD_DEST1": 100}}]}
    if "/21/" in url:
        raise OSError("boom")
    return {"features": []}


def test_query_point_no_key_mode():
    res = pipeline.query_point(45.4642, 9.19, fetch=_fetch)
    assert res["errors"] and not res["all_failed"]
    assert res["findings"]
    assert res["articles"] and all(a["roles"] for a in res["articles"])
    assert {"id", "number", "title", "text", "roles"} <= set(res["articles"][0])


def test_all_failed_flag():
    def bad(url, timeout):
        raise OSError("down")
    assert pipeline.query_point(0, 0, fetch=bad)["all_failed"]


class FakeClient:
    model, last_model = "fake", "fake"

    def __init__(self, fail_keywords=False):
        self.fail_keywords = fail_keywords

    def complete(self, parts, **kw):
        if "keywords" in parts["system"]:
            if self.fail_keywords:
                raise llm.LLMError("nope")
            return '{"keywords_it": "distanze"}'
        return '{"answer_it": "a", "answer_en": "b", "cited_articles": ["PR-art-1", "PR-art-999"]}'


def test_ask_flags_rejected_citation_and_survives_keyword_failure():
    res = pipeline.query_point(45.4642, 9.19, fetch=_fetch)
    ans = pipeline.ask("distanze?", res, FakeClient(fail_keywords=True))
    assert "PR-art-999" in ans["rejected_citations"]
    assert ans["warnings"] and ans["model"] == "fake"
    assert pipeline.check_connection(FakeClient()) == "fake"
