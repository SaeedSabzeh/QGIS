"""Prompt builders. The answer prompt asks for JSON with answer_it, answer_en, cited_articles.

A prompt is a dict {"system": str, "user": str, ...}; llm clients read those two keys.
"""

import json

DISCLAIMER_EN = (
    "Guidance only, not legal advice. Check the official texts and ask a qualified professional "
    "before acting. Source: Milan PGT 2030, Piano delle Regole - Norme di attuazione."
)
DISCLAIMER_IT = (
    "Solo orientamento, non e un parere legale. Verificare i testi ufficiali e rivolgersi a un "
    "professionista abilitato."
)
LIMITATION_EN = (
    "v1 limitation: the result refers to the clicked POINT, not to the whole parcel. A parcel "
    "crossing two zones may be misreported."
)

SYSTEM_RULES = """\
You help people understand which planning rules of the Comune di Milano apply at a map point.
Follow these rules strictly:
1. Answer ONLY from the ARTICLES and FINDINGS supplied below. Do not use outside knowledge about
   Italian planning law.
2. Cite ONLY article ids that appear in the supplied ARTICLES (format "PR-art-N"). Never invent ids.
3. If the supplied material does not contain the answer, say so plainly (in answer_it and answer_en)
   and leave cited_articles empty or limited to what is relevant. Do not guess.
4. This is guidance, not legal advice. Say that the user should check the official text.
5. A finding marked VERIFY or "uncertain link" has an article mapping a human has not confirmed:
   mention that the link is uncertain. Articles listed as "candidate" are only possible matches.
6. Findings marked EXTERNAL RULE come from laws or plans outside the Milan NTA (Piano delle
   Regole). Say that they are outside the NTA and are not among the supplied articles; do not
   cite them as articles.
7. The result concerns the clicked point only, not the whole parcel.
Reply with a single JSON object and nothing else:
{"answer_it": "<answer in Italian>", "answer_en": "<same answer in English>",
 "cited_articles": ["PR-art-N", ...]}"""

KEYWORDS_SYSTEM = """\
You turn a question about urban planning rules into Italian search keywords for a keyword
search (BM25) over the Norme di attuazione of the Piano delle Regole of Milan. Use the Italian
terms the regulation would use (e.g. "distanze", "destinazioni d'uso", "fattibilita geologica",
"nuclei di antica formazione", "parcheggi privati"). 3 to 10 keywords, no explanation.
Reply with JSON only: {"keywords_it": "<space separated keywords>"}"""


def truncate_text(text, limit):
    """Cut `text` to about `limit` characters at a paragraph/sentence boundary."""
    if limit is None or len(text) <= limit:
        return text
    cut = text[:limit]
    for sep in ("\n", ". ", "; "):
        pos = cut.rfind(sep)
        if pos >= limit * 0.6:
            cut = cut[: pos + 1]
            break
    return cut.rstrip() + "\n[... testo troncato / text truncated ...]"


def format_finding(f):
    """One finding as plain text for the prompt."""
    vals = ", ".join("%s=%s" % (k, v) for k, v in f.get("values", {}).items()
                     if k != "SCHEDA_NEW")
    lines = ["- %s%s" % (f.get("label") or f.get("category"), " (%s)" % vals if vals else "")]
    for key, title in (("articles", "governing articles"),
                       ("general_articles", "related general articles"),
                       ("candidate_articles", "candidate articles (uncertain)")):
        if f.get(key):
            lines.append("    %s: %s" % (title, ", ".join("PR-art-%s" % n for n in f[key])))
    if f.get("why"):
        lines.append("    why: %s" % " ".join(f["why"].split()))
    if f.get("note"):
        lines.append("    note: %s" % " ".join(f["note"].split()))
    if f.get("verify"):
        lines.append("    VERIFY: this link is uncertain, not confirmed by a human.")
    ext = f.get("external_rule")
    if ext:
        lines.append("    EXTERNAL RULE (outside the NTA%s): %s" % (
            ", unverified" if ext.get("verify") else "", ext.get("text", "")))
    return "\n".join(lines)


def format_article(a, max_chars):
    head = "[%s] Art. %s - %s" % (a["id"], a.get("number", ""), a.get("title", ""))
    if a.get("capo"):
        head += "  (%s)" % a["capo"]
    return head + "\n" + truncate_text(a.get("text", ""), max_chars)


def build_answer_prompt(question, findings, articles, max_chars_per_article=3500,
                        max_total_chars=30000):
    """Build the answer prompt.

    `articles` is an ordered list of article dicts (mapped first). Articles that do not fit in
    `max_total_chars` are left out; the ids actually included are returned as `article_ids` and
    are the only ones the model may cite.
    """
    blocks, ids, total = [], [], 0
    for a in articles:
        block = format_article(a, max_chars_per_article)
        if blocks and total + len(block) > max_total_chars:
            continue
        blocks.append(block)
        ids.append(a["id"])
        total += len(block)
    fnd = "\n".join(format_finding(f) for f in findings) or "(no constraint or zone found at the point)"
    user = (
        "FINDINGS at the clicked point:\n%s\n\nARTICLES (the only citable ids: %s):\n\n%s\n\n"
        "QUESTION: %s\n\nReturn the JSON object now."
        % (fnd, ", ".join(ids) or "none", "\n\n".join(blocks) or "(none)", question.strip())
    )
    return {"system": SYSTEM_RULES, "user": user, "article_ids": ids}


def build_keywords_prompt(question):
    """Prompt asking the model to rewrite `question` as Italian search keywords."""
    return {"system": KEYWORDS_SYSTEM, "user": "Question: " + question.strip()}


def keywords_from_text(text):
    """Extract the keyword string from a model reply (JSON, or plain text as a fallback)."""
    try:
        data = json.loads(text)
        if isinstance(data, dict) and data.get("keywords_it"):
            kw = data["keywords_it"]
            return " ".join(kw) if isinstance(kw, list) else str(kw)
    except (ValueError, TypeError):
        pass
    return text.strip().strip("`").replace("json", "", 1).strip() if text else ""
