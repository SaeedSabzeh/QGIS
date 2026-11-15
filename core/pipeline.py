"""Whole-flow helpers shared by front ends (the QGIS plugin): no printing, no Qt.

`query_point` = query_all + lookup + retrieve (no-key mode). `ask` = keyword rewrite + retrieve
+ answer prompt + parse, reusing the raw query result of the click. Mirrors core.ask.run.
"""

from . import llm, prompts, retrieval, services

ROLE_NAMES = {"articles": "governing", "general_articles": "general",
              "explanatory_articles": "explanatory", "candidate_articles": "candidate",
              "bm25": "search"}
ROLE_ORDER = ("governing", "general", "explanatory", "candidate", "search")


def article_rows(ids, provenance, by_id, data_dir=None):
    """Rows for display: id, document, label ("art. 11"), cite ("Piano dei Servizi \u2013 art. 11"),
    number, title, capo, text, normative, roles (governing/general/...)."""
    rows = []
    sources = retrieval.load_documents(data_dir)
    for aid in ids:
        a = by_id.get(aid)
        if not a:
            continue
        roles = {ROLE_NAMES.get(x.get("role"), x.get("role")) for x in provenance.get(aid, [])}
        roles = [r for r in ROLE_ORDER if r in roles]
        doc = sources.get(a.get("doc"), {})
        rows.append({"id": aid, "doc": a.get("doc"), "doc_name": a.get("doc_name"),
                     "label": a.get("label"), "cite": retrieval.cite_label(a),
                     "number": a.get("number"), "title": a.get("title", ""),
                     "capo": a.get("capo", ""), "text": a.get("text", ""),
                     "normative": a.get("normative", True), "roles": roles,
                     "source_url": doc.get("source_url"), "version_date": a.get("version_date"),
                     "pages": a.get("pages")})
    return rows


def query_point(lat, lon, fetch=None, data_dir=None):
    """Query the map services at (lat, lon) and map the hits to findings and articles."""
    raw = services.query_milan(lat, lon, fetch=fetch)
    errors = raw.get("errors", {})
    total = len(raw.get("layers", {}))
    findings = retrieval.lookup(raw, data_dir)
    ret = retrieval.retrieve(raw, None, findings=findings, data_dir=data_dir)
    return {
        "point": raw["point"], "raw": raw, "findings": findings, "errors": errors,
        "layers_total": total, "all_failed": bool(total) and len(errors) == total,
        "scope_note": raw.get("scope_note", ""),
        "articles": article_rows(ret["ids"], ret["provenance"], retrieval.articles_by_id(data_dir), data_dir),
        "sources": retrieval.sources_used(ret["ids"], data_dir),
    }


def complete_answer(client, prompt, on_progress=None):
    answer = llm.parse_answer(client.complete(prompt, on_progress=on_progress),
                              prompt["article_ids"], prompt["evidence_texts"])
    if answer["parse_error"]:
        answer["answer_it"] = "Il modello non ha restituito una risposta verificabile. Riprovare."
        answer["answer_en"] = "The model reply could not be verified. Try the question again."
    cited = set(answer["cited_articles"])
    supported = {item["article_id"] for item in answer.get("evidence", [])}
    answer["source_check"] = (
        "complete" if cited and cited <= supported and not answer["rejected_citations"]
        and not answer.get("rejected_evidence")
        else "review"
    )
    return answer


def ask(question, point_result, client, k=None, data_dir=None, on_progress=None):
    """Answer `question` for a `query_point` result with an LLM client (llm.make_client).

    Raises llm.LLMError when the answer request fails. A failed keyword rewrite is not fatal
    (the question itself is searched) and is reported in "warnings".

    `on_progress(message)` (optional) is called with short status lines such as "Trying
    gemini-3.8-flash..." or "gemini-3.8-flash busy, trying gemini-3.5-flash...". It runs in the
    calling thread: front ends that use a worker thread must hand the message to the GUI thread.
    """
    say = on_progress or (lambda message: None)
    if point_result.get("scope_note") or point_result.get("all_failed"):
        raise llm.LLMError(point_result.get("scope_note") or "The map lookup failed. Try again.")
    raw, findings = point_result["raw"], point_result["findings"]
    by_id = retrieval.articles_by_id(data_dir)
    warnings, keywords = [], question
    say("Preparing the search...")
    try:
        kw = prompts.keywords_from_text(client.complete(
            prompts.build_keywords_prompt(question), on_progress=on_progress,
            budget=llm.KEYWORDS_BUDGET))
        if kw:
            keywords = kw
    except llm.LLMError as exc:
        warnings.append("keyword rewrite failed (%s); searched with the original question" % exc)
    ret = retrieval.retrieve(raw, keywords, k=k, findings=findings, data_dir=data_dir,
                             original_question=question)
    articles = [by_id[i] for i in ret["ids"] if i in by_id]
    prompt = prompts.build_answer_prompt(
        question, findings, articles, keywords=keywords, provenance=ret["provenance"],
        map_errors=raw.get("errors", {}))
    say("Asking the model...")
    ans = complete_answer(client, prompt, on_progress)
    ans["model"] = client.last_model or client.model
    ans["keywords"] = keywords
    ans["warnings"] = warnings
    ans["articles"] = article_rows(ret["ids"], ret["provenance"], by_id, data_dir)
    ans["sources"] = retrieval.sources_used(prompt["article_ids"], data_dir)
    return ans


def check_connection(client):
    """Tiny request to verify the provider works. Returns the model name; raises LLMError."""
    client.complete({"system": "", "user": 'Reply with the JSON object {"ok": true}.'})
    return client.last_model or client.model
