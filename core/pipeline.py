"""Whole-flow helpers shared by front ends (the QGIS plugin): no printing, no Qt.

`query_point` = query_all + lookup + retrieve (no-key mode). `ask` = keyword rewrite + retrieve
+ answer prompt + parse, reusing the raw query result of the click. Mirrors core.ask.run.
"""

from . import llm, prompts, retrieval, services

ROLE_NAMES = {"articles": "governing", "general_articles": "general",
              "candidate_articles": "candidate", "bm25": "search"}
ROLE_ORDER = ("governing", "general", "candidate", "search")


def article_rows(ids, provenance, by_id):
    """Rows for display: id, number, title, capo, text, roles (governing/general/...)."""
    rows = []
    for aid in ids:
        a = by_id.get(aid)
        if not a:
            continue
        roles = {ROLE_NAMES.get(x.get("role"), x.get("role")) for x in provenance.get(aid, [])}
        roles = [r for r in ROLE_ORDER if r in roles]
        rows.append({"id": aid, "number": a.get("number"), "title": a.get("title", ""),
                     "capo": a.get("capo", ""), "text": a.get("text", ""), "roles": roles})
    return rows


def query_point(lat, lon, fetch=None, data_dir=None):
    """Query the map services at (lat, lon) and map the hits to findings and articles."""
    raw = services.query_all(lat, lon, fetch=fetch)
    errors = raw.get("errors", {})
    total = len(raw.get("layers", {}))
    findings = retrieval.lookup(raw, data_dir)
    ret = retrieval.retrieve(raw, None, findings=findings, data_dir=data_dir)
    return {
        "point": raw["point"], "raw": raw, "findings": findings, "errors": errors,
        "layers_total": total, "all_failed": bool(total) and len(errors) == total,
        "articles": article_rows(ret["ids"], ret["provenance"], retrieval.articles_by_id(data_dir)),
    }


def ask(question, point_result, client, k=5, data_dir=None):
    """Answer `question` for a `query_point` result with an LLM client (llm.make_client).

    Raises llm.LLMError when the answer request fails. A failed keyword rewrite is not fatal
    (the question itself is searched) and is reported in "warnings".
    """
    raw, findings = point_result["raw"], point_result["findings"]
    by_id = retrieval.articles_by_id(data_dir)
    warnings, keywords = [], question
    try:
        kw = prompts.keywords_from_text(client.complete(prompts.build_keywords_prompt(question)))
        if kw:
            keywords = kw
    except llm.LLMError as exc:
        warnings.append("keyword rewrite failed (%s); searched with the original question" % exc)
    ret = retrieval.retrieve(raw, keywords, k=k, findings=findings, data_dir=data_dir)
    articles = [by_id[i] for i in ret["ids"] if i in by_id]
    prompt = prompts.build_answer_prompt(
        question, findings, articles, keywords=keywords, provenance=ret["provenance"])
    ans = llm.parse_answer(client.complete(prompt), prompt["article_ids"])
    ans["model"] = client.last_model or client.model
    ans["keywords"] = keywords
    ans["warnings"] = warnings
    ans["articles"] = article_rows(ret["ids"], ret["provenance"], by_id)
    return ans


def check_connection(client):
    """Tiny request to verify the provider works. Returns the model name; raises LLMError."""
    client.complete({"system": "", "user": 'Reply with the JSON object {"ok": true}.'})
    return client.last_model or client.model
