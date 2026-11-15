from core import llm, pipeline, prompts, retrieval, scope, services


def test_outside_milan_skips_services():
    def fetch(url, timeout):
        raise AssertionError("Exterior clicks must stay local")

    result = pipeline.query_point(45.5197, 8.9736, fetch=fetch)
    assert result["scope_note"] and not result["findings"] and not result["articles"]
    assert result["layers_total"] == 0
    assert not scope.contains(45.445, 9.276)  # Linate control east of the city limit


def test_municipal_adr_takes_priority_over_regional_nafs():
    raw = {"layers": {
        "milano_adr": [{"ambito": "ADR", "nomeambito": "Disegno urbano", "objectid": 14690}],
        "pgt_naf": [{"COD_NUC": 15}],
        "pgt_previsioni_tuc": [{"AMB_URB": 23}],
    }}
    found = {f["layer"]: f for f in retrieval.lookup(raw)}
    assert found["milano_adr"]["articles"] == ["PR-art-20", "PR-art-21"]
    assert found["milano_adr"]["map_url"].endswith("/39")
    assert "pgt_naf" not in found
    assert found["pgt_previsioni_tuc"]["candidate_articles"] == []


def test_conflicting_municipal_categories_remain_candidates():
    raw = {"layers": {"milano_naf": [{"tipo": "Edificio"}], "milano_aru": [{"ambito": "ARU"}]}}
    for finding in retrieval.lookup(raw):
        assert finding["verify"] and not finding["articles"] and finding["candidate_articles"]


def test_municipal_park_zone_and_geology_resolve_separate_rules():
    raw = {"layers": {
        "milano_park_north": [{"ambito": "Parco Nord Milano"}],
        "milano_park_south": [{"nome": "Ambito dei piani di cintura urbana (Art. 26, NTA PTC)"}],
        "milano_geology": [{"legenda": "III - Fattibilità", "classi_new": "IIIa+IIIc",
                            "rif_norma": "Artt. 45.3, 45.5 Norme di Attuazione PdR"}],
        "pgt_fattibilita_geo": [{"CLASSE": 2}],
        "pgt_at": [{"AMB_TRAS": 29}],
        "parchi_regionali": [{"NOME_PA": "Parco Agricolo Sud Milano"}],
    }}
    found = {f["layer"]: f for f in retrieval.lookup(raw)}
    assert "pgt_fattibilita_geo" not in found and "parchi_regionali" not in found
    assert found["milano_geology"]["articles"] == ["PR-art-45"]
    assert found["milano_geology"]["values"]["rif_norma"].startswith("Artt. 45.3")
    assert found["milano_park_south"]["articles"] == ["PR-art-35", "PTC-art-1", "PTC-art-26"]
    assert found["milano_park_north"]["document_url"].startswith("https://parconord.milano.it/")
    assert found["pgt_at"]["candidate_articles"] == ["PTC-art-26", "PTC-all-A"]


def test_malformed_layer_response_is_unknown_coverage():
    result = services.query_all(45.46, 9.19, fetch=lambda url, timeout: {"exceededTransferLimit": True},
                                services={"fixture": "https://example.com/MapServer/0"})
    assert "fixture" in result["errors"] and result["layers"]["fixture"] == []


def test_answer_passages_are_checked_against_sent_text():
    article = {"id": "PR-art-6", "text": "Si applica un indice unico di 0,35 mq/mq."}
    prompt = prompts.build_answer_prompt("Quale indice?", [], [article], map_errors=["pgra_H_RP"])
    assert "Layers unavailable: pgra_H_RP" in prompt["user"]
    reply = """{"answer_it":"0,35","answer_en":"0.35","cited_articles":["PR-art-6"],
      "evidence":[{"article_id":"PR-art-6","quote":"indice unico di 0,35 mq/mq."},
                  {"article_id":"PR-art-6","quote":"indice proposto di 1,00 mq/mq."}]}"""
    answer = llm.parse_answer(reply, prompt["article_ids"], prompt["evidence_texts"])
    assert answer["evidence"] == [{"article_id": "PR-art-6", "quote": "indice unico di 0,35 mq/mq."}]
    assert answer["rejected_evidence"] == 1


def test_explicit_document_article_survives_keyword_rewrite():
    selected = retrieval.retrieve({}, "ambiti", original_question="Cosa prevede il PTC art. 42?", k=1)
    assert selected["extras"] == ["PTC-art-42"]


def test_gemini_sends_evidence_schema_and_skips_thought_parts():
    def transport(url, headers, payload, timeout):
        assert payload["generationConfig"]["responseJsonSchema"]["required"] == [
            "answer_it", "answer_en", "cited_articles", "evidence",
        ]
        return {"candidates": [{"content": {"parts": [
            {"thought": True, "text": '{"unrelated":"provider reasoning"}'},
            {"text": '{"answer_it":"prova","answer_en":"test","cited_articles":[],"evidence":[]}'},
        ]}}]}

    client = llm.GeminiClient(api_key="fixture", transport=transport)
    prompt = prompts.build_answer_prompt("Quale indice?", [], [])
    answer = pipeline.complete_answer(client, prompt)
    assert not answer["parse_error"] and answer["answer_en"] == "test"
