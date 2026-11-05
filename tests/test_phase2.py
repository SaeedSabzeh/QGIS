import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import ask, llm, prompts, retrieval, services  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FAKE = {"a": "https://x.test/MapServer/1", "b": "https://x.test/MapServer/2",
        "c": "https://x.test/MapServer/3"}


def _fake_fetch(url, timeout):
    if "/2/" in url:
        raise OSError("boom")
    if "/3/" in url:
        return {"features": []}
    return {"features": [{"attributes": {"X": 1}}, {"attributes": {"X": 2}}]}


def hit(layers):
    """A query_all-shaped result with the given {layer: [attrs]} hits."""
    return {"point": {"lat": 0, "lon": 0}, "layers": layers, "errors": {}}


DUOMO = hit({
    "pgt_naf": [{"COD_NUC": 15}],
    "pgt_previsioni_tuc": [{"AMB_URB": 23, "COD_DEST1": 100, "DCOD_DEST1": "RESIDENZIALE"}],
    "pgt_sensibilita": [{"CLASSE": 5}],
    "pgt_fattibilita_geo": [{"CLASSE": 2}],
})
LAMBRO = hit({
    "pgt_at": [{"AMB_TRAS": 26, "NOME_AMB": "L'Idroscalo (PCU4)"}],
    "pgt_fattibilita_geo": [{"CLASSE": 3, "FATTORI_PERICOLO": "III - ... - IIIa+IIIc"}],
    "pgra_R3": [{"Ris": "R3", "Danno": "D2"}],
    "pgra_H_RP": [{"Codscenar": "H", "Tritorno": 10, "Nomeelidr": "Lambro"}],
    "pgra_M_RP": [{"Codscenar": "M", "Tritorno": 200}],
    "pgra_L_RP": [{"Codscenar": "L", "Tritorno": 500}],
    "natura2000_zsc": [{"COD_SITO": "IT2050006", "NOME_SITO": "BOSCO DI VANZAGO"}],
})


# ---- services ------------------------------------------------------------------------------
def test_query_all_aggregates_and_tolerates_failure():
    res = services.query_all(45.46, 9.19, fetch=_fake_fetch, services=FAKE)
    assert res["layers"]["a"] == [{"X": 1}, {"X": 2}]
    assert res["layers"]["b"] == [] and "b" in res["errors"] and "boom" in res["errors"]["b"]
    assert res["layers"]["c"] == [] and "c" not in res["errors"]
    assert res["point"] == {"lat": 45.46, "lon": 9.19}


def test_query_all_service_error_payload_is_an_error():
    res = services.query_all(0, 0, fetch=lambda u, t: {"error": {"message": "nope"}},
                             services={"a": FAKE["a"]})
    assert "nope" in res["errors"]["a"]


def test_query_all_uses_lon_lat_order_and_registry():
    seen = []
    services.query_all(45.5, 9.2, fetch=lambda u, t: seen.append(u) or {"features": []})
    assert len(seen) == len(services.SERVICES) == 27
    assert all("geometry=9.2%2C45.5" in u for u in seen)


def test_probe_script_uses_core_registry():
    src = (ROOT / "scripts" / "probe_services.py").read_text(encoding="utf-8")
    assert "from core.services import SERVICES" in src and "_PGT =" not in src


# ---- maps JSON -----------------------------------------------------------------------------
def test_json_maps_match_yaml():
    yaml = pytest.importorskip("yaml")
    for name in ("zone_map", "constraint_map"):
        with open(ROOT / "data" / (name + ".yaml"), encoding="utf-8") as fh:
            expected = yaml.safe_load(fh)
        with open(ROOT / "data" / (name + ".json"), encoding="utf-8") as fh:
            assert json.load(fh) == expected, name + ".json is stale: run scripts/build_maps.py"


# ---- lookup --------------------------------------------------------------------------------
def by_layer(findings):
    return {f["layer"]: f for f in findings}


def test_lookup_duomo():
    f = by_layer(retrieval.lookup(DUOMO))
    assert f["pgt_naf"]["articles"] == [18, 19] and f["pgt_naf"]["general_articles"] == [6, 8, 13]
    tuc = f["pgt_previsioni_tuc"]
    assert tuc["articles"] == [6, 8, 13, 5]  # COD_DEST1=100 adds art. 5
    assert 18 in tuc["candidate_articles"] and tuc["verify"] is True
    assert f["pgt_sensibilita"]["articles"] == [34]
    assert f["pgt_fattibilita_geo"]["articles"] == [44]
    assert f["pgt_fattibilita_geo"]["external_rule"]["external"] is True
    assert f["pgt_naf"]["values"] == {"COD_NUC": 15}


def test_lookup_lambro_and_hazard_mapping():
    f = by_layer(retrieval.lookup(LAMBRO))
    assert f["pgt_at"]["articles"] == [] and f["pgt_at"]["verify"] is True
    assert 53 in f["pgt_at"]["general_articles"]
    assert f["pgt_fattibilita_geo"]["articles"] == [45]
    assert f["pgra_H_RP"]["articles"] == [45, 46]
    assert f["pgra_H_RP"]["values"]["nta_scenario"] == "P3"
    assert f["pgra_M_RP"]["articles"] == [44, 45, 46]
    assert f["pgra_L_RP"]["articles"] == [44]
    assert f["pgra_R3"]["articles"] == [43, 45, 46, 48]
    assert f["pgra_R3"]["external_rule"]["external"] is True
    n2k = f["natura2000_zsc"]
    assert n2k["articles"] == [3, 36] and n2k["values"]["COD_SITO"] == "IT2050006"


def test_lookup_ignores_empty_and_unknown_layers():
    assert retrieval.lookup(hit({"pgt_naf": [], "mystery": [{"A": 1}]})) == []


def test_lookup_geology_class_without_mapping_is_verify():
    f = retrieval.lookup(hit({"pgt_fattibilita_geo": [{"CLASSE": 1}]}))[0]
    assert f["articles"] == [] and f["verify"] is True


def test_provenance_dedups_and_orders():
    prov = retrieval.article_provenance(retrieval.lookup(DUOMO))
    ids = list(prov)
    assert len(ids) == len(set(ids))
    assert ids.index("PR-art-18") < ids.index("PR-art-7")  # direct before general
    assert {p["role"] for p in prov["PR-art-18"]} == {"articles", "candidate_articles"}
    assert {p["layer"] for p in prov["PR-art-6"]} == {"pgt_naf", "pgt_previsioni_tuc"}


# ---- BM25 ----------------------------------------------------------------------------------
def test_tokenize_italian():
    toks = retrieval.tokenize("Nuclei di antica formazione, DELLA città")
    assert "di" not in toks and "della" not in toks and "citt" in toks


def test_bm25_obvious_hits():
    assert retrieval.search("classe di fattibilità geologica III", k=1)[0][0] == "PR-art-45"
    assert retrieval.search("classe IV fattibilità gravi limitazioni", k=1)[0][0] == "PR-art-46"
    assert retrieval.search("nuclei di antica formazione", k=1)[0][0] in ("PR-art-18", "PR-art-19")
    assert retrieval.search("parcheggi privati", k=1)[0][0] == "PR-art-12"
    assert retrieval.search("zzzz qqqq") == []


def test_retrieve_orders_mapped_first_and_dedups():
    res = retrieval.retrieve(DUOMO, "fattibilità geologica classe II parcheggi privati", k=3)
    ids = res["ids"]
    assert ids[: len(res["mapped"])] == res["mapped"]
    assert len(ids) == len(set(ids)) and len(res["extras"]) <= 3
    assert not set(res["extras"]) & set(res["mapped"])
    assert res["provenance"][res["extras"][0]][0]["role"] == "bm25"
    assert retrieval.retrieve(DUOMO)["extras"] == []


# ---- prompts / llm -------------------------------------------------------------------------
def _art(n, text, title="T"):
    return {"id": "PR-art-%d" % n, "number": n, "title": title, "text": text}


def _prov(**roles):
    """_prov(articles=[1], bm25=[2], ...) -> provenance dict."""
    out = {}
    for role, nums in roles.items():
        for n in nums:
            out.setdefault("PR-art-%d" % n, []).append({"role": role})
    return out


def _long_art(n, term_line_at=40, lines=60):
    rows = ["Art. %d testo introduttivo." % n]
    rows += ["comma %d filler generico di norma senza rilievo %s" % (i, "z" * 60)
             for i in range(1, lines)]
    rows[term_line_at] = "comma %d per il piano interrato valgono regole speciali" % term_line_at
    return _art(n, "\n".join(rows))


def test_prompt_contains_rules_findings_and_truncates():
    arts = [_art(1, "x. " * 5000)]
    findings = retrieval.lookup(DUOMO)
    p = prompts.build_answer_prompt("Che cosa posso costruire?", findings, arts,
                                    max_total_chars=1500)
    assert "ONLY" in p["system"] and "answer_it" in p["system"] and "PR-art-1" in p["user"]
    assert "troncato" in p["user"] and "(estratto)" in p["user"] and "VERIFY" in p["user"]
    assert "EXTERNAL RULE" in p["user"]
    assert p["article_ids"] == ["PR-art-1"] and len(p["user"]) < 6000


def test_governing_article_in_full_under_default_budget():
    big = _long_art(45)
    assert len(big["text"]) > 3500
    p = prompts.build_answer_prompt("q", [], [big], provenance=_prov(articles=[45]))
    assert big["text"] in p["user"] and "(estratto)" not in p["user"]
    assert "[...]" not in p["user"] and p["article_ids"] == ["PR-art-45"]


def test_trim_keeps_first_paragraph_query_terms_and_order():
    big = _long_art(45)
    p = prompts.build_answer_prompt("piano interrato", [], [big], keywords="interrato",
                                    provenance=_prov(articles=[45]), max_total_chars=2500)
    u = p["user"]
    assert "(estratto)" in u and "[...]" in u
    assert "Art. 45 testo introduttivo." in u
    assert "comma 40 per il piano interrato" in u
    assert u.index("testo introduttivo") < u.index("comma 40 per il piano")
    body = u[u.index("[PR-art-45] Art."):u.index("QUESTION")]
    assert len(body) < 2600
    nums = [int(l.split()[1]) for l in body.splitlines() if l.startswith("comma ")]
    assert nums == sorted(nums)


def test_priority_governing_extras_general_candidate():
    arts = [_art(i, "w" * 900) for i in (1, 2, 3, 4)]
    prov = _prov(candidate_articles=[1], general_articles=[2], bm25=[3], articles=[4])
    p = prompts.build_answer_prompt("q", [], arts, provenance=prov, max_total_chars=2200)
    assert p["article_ids"][:2] == ["PR-art-4", "PR-art-3"]
    assert "PR-art-1" not in p["article_ids"]
    full = prompts.build_answer_prompt("q", [], arts, provenance=prov)
    assert full["article_ids"] == ["PR-art-4", "PR-art-3", "PR-art-2", "PR-art-1"]


def test_governing_exceeding_budget_trims_longest_last():
    short, long_ = _art(1, "s" * 500), _long_art(2)
    p = prompts.build_answer_prompt("piano interrato", [], [short, long_],
                                    provenance=_prov(articles=[1, 2]), max_total_chars=3000)
    assert p["article_ids"] == ["PR-art-1", "PR-art-2"]
    assert "s" * 500 in p["user"] and "(estratto)" in p["user"]
    assert len(p["user"]) < 3000 + 1500  # budget + findings/question/wrapper overhead


def test_hard_cap_overrides_total():
    big = _art(1, "\n".join("riga %d %s" % (i, "k" * 80) for i in range(500)))
    p = prompts.build_answer_prompt("q", [], [big], provenance=_prov(articles=[1]),
                                    max_total_chars=10 ** 9, hard_cap_chars=5000)
    assert len(p["user"]) < 5000 + 1500


def test_article_ids_only_included():
    arts = [_art(i, "y" * 900) for i in range(1, 6)]
    p = prompts.build_answer_prompt("q", [], arts, max_total_chars=2000)
    assert 0 < len(p["article_ids"]) < 5
    for aid in p["article_ids"]:
        assert "[%s]" % aid in p["user"]
    for a in arts:
        if a["id"] not in p["article_ids"]:
            assert "[%s]" % a["id"] not in p["user"].split("QUESTION")[0].split("ARTICLES")[1]


def test_real_art45_interrato_survives_trimming():
    by_id = retrieval.articles_by_id()
    a45 = by_id["PR-art-45"]
    assert len(a45["text"]) > 15000
    prov = _prov(articles=[45])
    full = prompts.build_answer_prompt("piano interrato", [], [a45], keywords="piano interrato",
                                       provenance=prov)
    assert a45["text"] in full["user"]
    small = prompts.build_answer_prompt("piano interrato", [], [a45], keywords="piano interrato",
                                        provenance=prov, max_total_chars=4000)
    assert "(estratto)" in small["user"] and "interrat" in small["user"][small["user"].index("[PR-art-45]"):]


def test_parse_answer_fences_and_rejection():
    text = ('```json\n{"answer_it": "ok", "answer_en": "fine", '
            '"cited_articles": ["PR-art-45", 99, "art. 12", "PR-art-45", 7]}\n```')
    r = llm.parse_answer(text, ["PR-art-45", "PR-art-12"])
    assert r["cited_articles"] == ["PR-art-45", "PR-art-12"]
    assert r["rejected_citations"] == ["PR-art-99", "PR-art-7"]
    assert r["answer_it"] == "ok" and r["answer_en"] == "fine" and not r["parse_error"]


def test_parse_answer_prose_and_garbage():
    r = llm.parse_answer('Sure! {"answer_it": "a", "answer_en": "b", "cited_articles": []} done',
                         [])
    assert r["answer_it"] == "a" and not r["parse_error"]
    bad = llm.parse_answer("not json at all", ["PR-art-1"])
    assert bad["parse_error"] and bad["cited_articles"] == []


def test_gemini_key_in_header_not_url():
    calls = []

    def transport(url, headers, payload, timeout):
        calls.append((url, headers, payload))
        return {"candidates": [{"content": {"parts": [{"text": '{"answer_it": "x"}'}]}}]}

    c = llm.GeminiClient("SECRET123", model="gemini-test", transport=transport)
    out = c.complete({"system": "S", "user": "U"})
    url, headers, payload = calls[0]
    assert out == '{"answer_it": "x"}'
    assert "SECRET123" not in url and headers["x-goog-api-key"] == "SECRET123"
    assert url.endswith("/models/gemini-test:generateContent")
    assert payload["generationConfig"]["responseMimeType"] == "application/json"
    assert payload["contents"][0]["parts"][0]["text"] == "U"
    assert "SECRET123" not in json.dumps(payload)


def test_gemini_error_never_leaks_key():
    def transport(url, headers, payload, timeout):
        raise llm.LLMError("HTTP 400 for key SECRET123")

    c = llm.GeminiClient("SECRET123", transport=transport)
    with pytest.raises(llm.LLMError) as e:
        c.complete({"user": "U"})
    assert "SECRET123" not in str(e.value)


def test_gemini_blocked_and_requires_key():
    c = llm.GeminiClient("k", transport=lambda *a: {"promptFeedback": {"blockReason": "SAFETY"}})
    with pytest.raises(llm.LLMError, match="SAFETY"):
        c.complete({"user": "U"})
    with pytest.raises(llm.LLMError):
        llm.GeminiClient("")


def test_ollama_request_and_response():
    calls = []

    def transport(url, headers, payload, timeout):
        calls.append((url, payload))
        return {"message": {"content": '{"answer_it": "x"}'}}

    c = llm.make_client("ollama", model="m", base_url="http://h:1/", transport=transport)
    assert c.complete({"system": "S", "user": "U"}) == '{"answer_it": "x"}'
    url, payload = calls[0]
    assert url == "http://h:1/api/chat" and payload["format"] == "json"
    assert payload["stream"] is False and payload["model"] == "m"
    assert [m["role"] for m in payload["messages"]] == ["system", "user"]


# ---- ask.py --------------------------------------------------------------------------------
def test_ask_no_key_prints_findings_and_titles():
    out = io.StringIO()
    code = ask.run(["45.4642", "9.19"], query_fn=lambda lat, lon: DUOMO, env={}, out=out)
    text = out.getvalue()
    assert code == 0
    assert "Nuclei di antica formazione" in text and "PR-art-18" in text
    assert "Classe II - Fattibilit" in text
    assert "not legal advice" in text and "POINT" in text


def test_ask_question_without_key_explains():
    out = io.StringIO()
    code = ask.run(["1", "2", "Can I build?"], query_fn=lambda lat, lon: DUOMO, env={}, out=out)
    assert code == 0 and "GEMINI_API_KEY" in out.getvalue()


def test_ask_with_question_flags_rejected_citation():
    replies = iter([
        '{"keywords_it": "fattibilita geologica classe II"}',
        '{"answer_it": "Risposta", "answer_en": "Answer", '
        '"cited_articles": ["PR-art-44", "PR-art-999"]}',
    ])
    seen = []

    def transport(url, headers, payload, timeout):
        seen.append(headers)
        return {"candidates": [{"content": {"parts": [{"text": next(replies)}]}}]}

    out = io.StringIO()
    code = ask.run(["1", "2", "What is the geological class?"], query_fn=lambda a, b: DUOMO,
                   transport=transport, env={"GEMINI_API_KEY": "k"}, out=out)
    text = out.getvalue()
    assert code == 0 and len(seen) == 2
    assert "Italian keywords: fattibilita geologica classe II" in text
    assert "Answer (EN): Answer" in text and "Cited articles: PR-art-44" in text
    assert "PR-art-999" in text and "WARNING" in text


def test_ask_network_errors_exit_cleanly(capsys):
    def boom(url, headers, payload, timeout):
        raise llm.LLMError("offline")

    out = io.StringIO()
    code = ask.run(["1", "2", "q"], query_fn=lambda a, b: DUOMO, transport=boom,
                   env={"GEMINI_API_KEY": "k"}, out=out)
    assert code == 1 and "LLM request failed" in capsys.readouterr().err

    dead = {"point": {}, "layers": {"a": []}, "errors": {"a": "OSError: down"}}
    assert ask.run(["1", "2"], query_fn=lambda a, b: dead, env={}, out=io.StringIO()) == 1


# ---- retry / fallback ----------------------------------------------------------------------
OK = {"candidates": [{"content": {"parts": [{"text": '{"answer_it": "x"}'}]}}]}


def scripted(*steps):
    """Fake transport: each step is a dict reply or an exception to raise; records model names."""
    steps = list(steps)
    models = []

    def transport(url, headers, payload, timeout):
        models.append(url.split("/models/")[1].split(":")[0])
        step = steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return step

    transport.models = models
    return transport


def http_err(status, retry_after=None):
    return llm.LLMError("HTTP %s" % status, status=status, retry_after=retry_after,
                        transient=status in llm.TRANSIENT_STATUSES)


def gem(transport, **kw):
    sleeps = []
    c = llm.GeminiClient("k", model="p", fallbacks=("f1", "f2"), transport=transport,
                         sleep=sleeps.append, rng=lambda: 1.0, **kw)
    return c, sleeps


def test_retry_same_model_on_503_then_success():
    t = scripted(http_err(503), OK)
    c, sleeps = gem(t)
    assert c.complete({"user": "U"}) == '{"answer_it": "x"}'
    assert t.models == ["p", "p"] and c.last_model == "p" and sleeps == [2.0]


def test_fallback_after_three_503s():
    t = scripted(http_err(503), http_err(503), http_err(503), OK)
    c, sleeps = gem(t)
    c.complete({"user": "U"})
    assert t.models == ["p", "p", "p", "f1"] and c.last_model == "f1"
    assert sleeps == [2.0, 4.0]  # no sleep between models


def test_404_falls_back_immediately():
    t = scripted(http_err(404), OK)
    c, sleeps = gem(t)
    c.complete({"user": "U"})
    assert t.models == ["p", "f1"] and c.last_model == "f1" and sleeps == []


def test_401_and_400_stop_immediately():
    for status in (400, 401, 403):
        t = scripted(http_err(status), OK)
        c, sleeps = gem(t)
        with pytest.raises(llm.LLMError) as e:
            c.complete({"user": "U"})
        assert e.value.status == status and t.models == ["p"] and sleeps == []


def test_all_models_exhausted_raises_last_error():
    t = scripted(*[http_err(503)] * 9)
    c, _ = gem(t)
    with pytest.raises(llm.LLMError) as e:
        c.complete({"user": "U"})
    assert e.value.status == 503 and len(t.models) == 9 and c.last_model is None


def test_no_fallback_and_dedup_chain():
    c = llm.GeminiClient("k", model="a", fallbacks=("a", "b", "b"))
    assert c.models == ["a", "b"]
    t = scripted(http_err(503), http_err(503), http_err(503))
    c, _ = gem(t)
    c.fallbacks = ()
    with pytest.raises(llm.LLMError):
        c.complete({"user": "U"})
    assert t.models == ["p", "p", "p"]


def test_retry_after_honoured_and_capped():
    t = scripted(http_err(429, retry_after=7), http_err(429, retry_after=500), OK)
    c, sleeps = gem(t)
    c.complete({"user": "U"})
    assert sleeps == [7.0, llm.DEFAULT_MAX_DELAY]


def test_backoff_has_jitter_and_cap():
    t = scripted(http_err(500), http_err(500), http_err(500), OK)
    sleeps = []
    c = llm.GeminiClient("k", model="p", fallbacks=("f",), transport=t, sleep=sleeps.append,
                         rng=lambda: 0.0, base_delay=2, max_delay=3)
    c.complete({"user": "U"})
    assert sleeps == [1.0, 1.5]  # 50% of min(cap, 2) and of min(cap, 4)


def test_timeout_is_transient(monkeypatch):
    import socket

    def boom(*a, **k):
        raise socket.timeout("timed out")

    monkeypatch.setattr(llm.urllib.request, "urlopen", boom)
    with pytest.raises(llm.LLMError) as e:
        llm.post_json("https://x.test/y?key=1", {}, {}, 1)
    assert e.value.transient is True and e.value.status is None
    # a raw OSError from a custom transport is retried as well
    t = scripted(TimeoutError("read timed out"), OK)
    c, sleeps = gem(t)
    c.complete({"user": "U"})
    assert t.models == ["p", "p"] and len(sleeps) == 1


def test_post_json_http_error_carries_status_and_retry_after(monkeypatch):
    import email.message
    import urllib.error
    hdrs = email.message.Message()
    hdrs["Retry-After"] = "9"

    def boom(*a, **k):
        raise urllib.error.HTTPError("https://x.test/y", 503, "busy", hdrs, io.BytesIO(b"hi"))

    monkeypatch.setattr(llm.urllib.request, "urlopen", boom)
    with pytest.raises(llm.LLMError) as e:
        llm.post_json("https://x.test/y", {}, {}, 1)
    assert (e.value.status, e.value.retry_after, e.value.transient) == (503, 9.0, True)


def test_error_scrubbing_keeps_status():
    t = scripted(llm.LLMError("bad key SECRET123", status=403))
    c = llm.GeminiClient("SECRET123", transport=t, sleep=lambda s: None)
    with pytest.raises(llm.LLMError) as e:
        c.complete({"user": "U"})
    assert "SECRET123" not in str(e.value) and e.value.status == 403


def test_ollama_retries_timeout_without_fallback():
    reply = {"message": {"content": "{}"}}
    calls, sleeps = [], []

    def transport(url, headers, payload, timeout):
        calls.append(1)
        if len(calls) < 3:
            raise llm.LLMError("timed out", transient=True)
        return reply

    c = llm.make_client("ollama", model="m", transport=transport, sleep=sleeps.append)
    assert c.complete({"user": "U"}) == "{}" and len(calls) == 3 and len(sleeps) == 2
    assert c.last_model == "m"

    def dead(url, headers, payload, timeout):
        raise llm.LLMError("down", transient=True)

    c = llm.make_client("ollama", transport=dead, sleep=lambda s: None)
    with pytest.raises(llm.LLMError):
        c.complete({"user": "U"})


def test_default_model_constants():
    assert llm.DEFAULT_GEMINI_MODEL == "gemini-3.8-flash"
    assert isinstance(llm.DEFAULT_GEMINI_FALLBACKS, tuple) and llm.DEFAULT_GEMINI_FALLBACKS


def test_ask_warns_when_keyword_rewrite_fails(capsys):
    replies = iter([llm.LLMError("HTTP 400 bad"), '{"answer_it": "R", "answer_en": "A", '
                    '"cited_articles": []}'])

    def transport(url, headers, payload, timeout):
        r = next(replies)
        if isinstance(r, Exception):
            raise r
        return {"candidates": [{"content": {"parts": [{"text": r}]}}]}

    out = io.StringIO()
    code = ask.run(["1", "2", "geological class?"], query_fn=lambda a, b: DUOMO,
                   transport=transport, env={"GEMINI_API_KEY": "k"}, out=out,
                   sleep=lambda s: None)
    err = capsys.readouterr().err
    assert code == 0
    assert "WARNING: keyword rewrite failed" in err and "searching with the original question" in err
    assert "Italian keywords: geological class?" in out.getvalue()
    assert "Model: %s" % llm.DEFAULT_GEMINI_MODEL in out.getvalue()


def test_ask_reports_fallback_model_and_no_fallback_flag(capsys):
    def make(fail_models):
        def transport(url, headers, payload, timeout):
            model = url.split("/models/")[1].split(":")[0]
            if model in fail_models:
                raise llm.LLMError("HTTP 503", status=503, transient=True)
            return {"candidates": [{"content": {"parts": [{"text": '{"keywords_it": "k"}'}]}}]}
        return transport

    primary = llm.DEFAULT_GEMINI_MODEL
    out = io.StringIO()
    code = ask.run(["1", "2", "q"], query_fn=lambda a, b: DUOMO, transport=make({primary}),
                   env={"GEMINI_API_KEY": "k"}, out=out, sleep=lambda s: None)
    assert code == 0 and "Model: %s" % llm.DEFAULT_GEMINI_FALLBACKS[0] in out.getvalue()

    out = io.StringIO()
    code = ask.run(["1", "2", "q", "--no-fallback"], query_fn=lambda a, b: DUOMO,
                   transport=make({primary}), env={"GEMINI_API_KEY": "k"}, out=out,
                   sleep=lambda s: None)
    assert code == 1 and "LLM request failed" in capsys.readouterr().err
