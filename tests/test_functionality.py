import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import pipeline, retrieval, services  # noqa: E402


def test_transient_layer_error_is_retried_once():
    calls = []

    def flaky(url, timeout):
        calls.append(url)
        if len(calls) == 1:
            raise OSError("connection reset")
        return {"features": [{"attributes": {"A": 1}}]}

    res = services.query_all(45.46, 9.19, fetch=flaky, services={"x": "https://example.test/0"})
    assert len(calls) == 2 and res["layers"]["x"] == [{"A": 1}] and not res["errors"]


def test_bad_service_reply_is_not_retried():
    calls = []

    def broken(url, timeout):
        calls.append(url)
        return {"error": {"message": "invalid layer"}}

    res = services.query_all(45.46, 9.19, fetch=broken, services={"x": "https://example.test/0"})
    assert len(calls) == 1 and "service error" in res["errors"]["x"]


def test_click_deadline_reports_slow_layers_as_errors():
    def slow(url, timeout):
        if url.startswith("https://slow"):
            time.sleep(2)
        return {"features": []}

    started = time.monotonic()
    res = services.query_all(45.46, 9.19, fetch=slow, deadline=0.5,
                             services={"fast": "https://fast.test/0", "slow": "https://slow.test/0"})
    assert time.monotonic() - started < 1.5
    assert "fast" not in res["errors"] and "no answer within" in res["errors"]["slow"]


def test_numbers_missing_from_the_articles_are_reported():
    answer = {"answer_it": "Indice 0,35 mq/mq e massimo 0,70; quota 25 %.",
              "answer_en": "Index 0.35 sq.m/sq.m"}
    articles = [{"text": "indice di edificabilità territoriale pari a 0,35 mq/mq"}]
    assert pipeline.unsupported_numbers(answer, articles) == ["0,70", "25"]


def test_previous_plan_records_are_flagged():
    findings = [{"layer": "pgt_at", "values": {"SCHEDA_NEW": "x/015146_20171115_AT_22.pdf"},
                 "note": "n", "verify": False}]
    retrieval._flag_previous_plan(findings)
    assert findings[0]["verify"] and "15/11/2017" in findings[0]["note"]
    current = [{"layer": "pgt_at", "values": {"SCHEDA_NEW": "x/015146_20210301_AT_2.pdf"},
                "note": "", "verify": False}]
    retrieval._flag_previous_plan(current)
    assert not current[0]["verify"]


def test_municipal_geology_demotes_flood_geology_articles():
    findings = [{"layer": "pgra_L_RP", "articles": ["PR-art-44", "PR-art-48"],
                 "general_articles": [], "note": ""}]
    retrieval._demote_flood_geology(findings)
    assert findings[0]["articles"] == ["PR-art-48"]
    assert findings[0]["general_articles"] == ["PR-art-44"]
    assert "Tav. G.17" in findings[0]["note"]


def test_new_municipal_layers_are_registered_and_mapped():
    zone_map, _ = retrieval.load_maps()
    for name in ("milano_accessibility", "milano_gfu", "milano_in_itinere", "milano_plis_lambro",
                 "milano_navigli_136", "milano_verde"):
        assert name in services.SERVICES
        assert retrieval.LAYER_RULES[name] == ("zone", name)
        assert zone_map["layers"][name]["articles"]


def test_cancellation_is_not_retried():
    class Canceled(Exception):
        pass

    calls = []

    def cancel(url, timeout):
        calls.append(url)
        raise Canceled("Canceled")

    services.query_all(45.46, 9.19, fetch=cancel, services={"x": "https://example.test/0"})
    assert len(calls) == 1


def test_identify_findings_use_the_map_rules_and_skip_labels():
    zone_map, _ = retrieval.load_maps()
    rules = zone_map["identify"]
    naf = retrieval._identify_finding("milano_r03", rules["milano_r03"], {
        "_layerId": 3, "_layerName": "Interventi di manutenzione ordinaria, straordinaria",
        "Disciplina": "Interventi di manutenzione ordinaria straordinaria e restauro", "OBJECTID": 7})
    assert naf["articles"] == ["PR-art-19"] and "OBJECTID" not in naf["values"]
    radar = retrieval._identify_finding("milano_r07", rules["milano_r07"],
                                        {"_layerId": 8, "_layerName": "Fasce di rispetto"})
    assert radar["articles"] == ["PR-art-37", "PR-art-40"]
    assert retrieval._identify_finding("milano_r08", rules["milano_r08"],
                                       {"_layerId": 4, "_layerName": " Label"}) is None


def test_regional_tuc_is_context_when_municipal_zones_answered_empty():
    findings = [{"layer": "pgt_previsioni_tuc", "articles": ["PR-art-6"], "general_articles": [],
                 "note": ""}]
    retrieval._demote_regional_tuc(findings, [])
    assert findings[0]["articles"] == [] and findings[0]["general_articles"] == ["PR-art-6"]


def test_cg_geology_articles_are_not_governing_on_flood_findings():
    findings = [{"layer": "pgra_H_RP", "articles": ["CG-art-45", "CG-art-46", "PR-art-48"],
                 "general_articles": [], "note": ""}]
    retrieval._demote_flood_geology(findings)
    assert findings[0]["articles"] == ["PR-art-48"]


def test_numbers_with_units_are_checked_against_cited_passages():
    answer = {"answer_it": "Distanza di 100 m e altezza 25 m.", "answer_en": ""}
    assert pipeline.unsupported_numbers(answer, [], cited_texts=["fascia di 100 m"]) == ["25"]


def test_number_check_compares_whole_numbers_and_ignores_references():
    answer = {"answer_it": "Indice 0,35 mq/mq (art. 35.3, Agg. del 04.12.2025); altezza 100 m.",
              "answer_en": ""}
    assert pipeline.unsupported_numbers(answer, [], cited_texts=["indice 10,35 e 1000 m"]) == [
        "0,35", "100"]
    assert pipeline.unsupported_numbers({"answer_it": "1.234,5 mq"}, [],
                                        cited_texts=["superficie 1234,5 mq"]) == []


def test_client_errors_are_not_retried_but_server_errors_are():
    class HTTPError(Exception):
        def __init__(self, code):
            super().__init__(code)
            self.code = code

    assert not services._transient(HTTPError(404)) and services._transient(HTTPError(503))
    assert not services._transient(KeyError("x")) and services._transient(OSError("reset"))


def test_identify_override_replaces_the_default_and_guards_the_layer_name():
    zone_map, _ = retrieval.load_maps()
    rules = zone_map["identify"]["milano_r03"]
    services_ = retrieval._identify_finding("milano_r03", rules, {
        "_layerId": 15, "_layerName": "DOTAZIONI TERRITORIALI",
        "TIPO": "Limite esenzione dotazioni territoriali (art. 11.3 Piano dei Servizi)"})
    assert services_["articles"] == ["PS-art-11"] and not services_["candidate_articles"]
    moved = retrieval._identify_finding("milano_r03", rules, {"_layerId": 15, "_layerName": "Fronti"})
    assert moved["verify"] and "PS-art-11" in moved["candidate_articles"] and not moved["articles"]
    assert "could not be confirmed" in moved["note"]


def test_vincolo_legal_reference_and_unanswered_map_are_shown():
    zone_map, _ = retrieval.load_maps()
    well = retrieval._identify_finding("milano_r05", zone_map["identify"]["milano_r05"], {
        "_layerId": 9, "_layerName": "Pozzi", "LEGENDA": "Dlgs. 3-04-2006 n. 152 e DGR 7/12693"})
    assert "152" in well["external_rule"]["text"]
    cards = retrieval._identify_failures({"milano_r06": "TimeoutError"}, zone_map)
    assert cards[0]["verify"] and "unknown, not absent" in cards[0]["note"]


def test_regional_tuc_is_context_when_a_municipal_zone_governs():
    findings = [{"layer": "pgt_previsioni_tuc", "articles": ["PR-art-21"], "general_articles": [],
                 "note": ""}]
    retrieval._demote_regional_tuc(findings, ["milano_adr"])
    assert findings[0]["articles"] == [] and "ADR" in findings[0]["note"]


def test_number_check_reads_each_answer_in_its_own_language():
    cited = ["altezza massima 10 m, superficie 1350 mq, indice 0,35"]
    en = {"answer_it": "", "answer_en": "Index 1.350, height 25 meters, index 0.350"}
    assert pipeline.unsupported_numbers(en, [], cited_texts=cited) == ["1.350", "25"]
    it = {"answer_it": "Superficie 1.350 mq e indice 0,350", "answer_en": ""}
    assert pipeline.unsupported_numbers(it, [], cited_texts=cited) == []


def test_identify_findings_link_their_map():
    findings = retrieval.lookup({"layers": {"milano_r05": [{"_layerId": 9, "_layerName": "Pozzi"}]},
                                 "errors": {"milano_r06": "TimeoutError"}})
    assert findings and all(f["map_url"] for f in findings)


def test_legend_labels_are_not_reported_as_laws():
    assert retrieval._legal_reference({"LEGENDA": "TUC - Tessuto urbano consolidato"}) == ""
    assert retrieval._legal_reference({"DATA_DECR": "28-03-1984"}) == ""
    assert retrieval._legal_reference({"RifLeg": "Art. 142 c. 1 lett. f), DLgs n. 42/2004",
                                       "DATA_DECR": "28-03-1984"}) == (
        "Art. 142 c. 1 lett. f), DLgs n. 42/2004; decreto del 28-03-1984")


def test_a_hanging_host_does_not_starve_the_other_hosts():
    def fetch(url, timeout):
        if "hung.test" in url:
            time.sleep(timeout)
        return {"features": [{"attributes": {"A": 1}}]}

    layers = {"hung%d" % i: "https://hung.test/%d" % i for i in range(30)}
    layers.update({"region%d" % i: "https://region.test/%d" % i for i in range(20)})
    started = time.monotonic()
    res = services.query_all(45.46, 9.19, fetch=fetch, services=layers, deadline=2, timeout=2)
    assert time.monotonic() - started < 3.5
    assert all(res["layers"]["region%d" % i] == [{"A": 1}] for i in range(20))
