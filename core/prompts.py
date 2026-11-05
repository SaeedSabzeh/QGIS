"""Prompt builders. The answer prompt asks for JSON with answer_it, answer_en, cited_articles.

A prompt is a dict {"system": str, "user": str, ...}; llm clients read those two keys.
"""

import json
import math
from collections import Counter

from . import retrieval

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
LIMITATION_IT = (
    "Limite v1: il risultato si riferisce al PUNTO cliccato, non all'intero lotto. Un lotto "
    "a cavallo di due zone puo essere riportato in modo errato."
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
8. An article header marked "(estratto)" is an excerpt: passages left out are shown as "[...]".
   If the answer may depend on omitted text, say so honestly instead of guessing.
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


DEFAULT_MAX_TOTAL_CHARS = 120000   # default budget for the ARTICLES section
HARD_CAP_CHARS = 250000            # never exceeded, whatever max_total_chars says
MIN_ARTICLE_CHARS = 600            # a non-governing article is not worth a smaller excerpt
OMIT_MARK = "[...]"
EXCERPT_TAG = "(estratto)"

# Priority classes: lower is included first.
P_GOVERNING, P_EXTRA, P_GENERAL, P_CANDIDATE = 0, 1, 2, 3
_ROLE_PRIORITY = {"articles": P_GOVERNING, "bm25": P_EXTRA,
                  "general_articles": P_GENERAL, "candidate_articles": P_CANDIDATE}


def article_header(a, excerpt=False):
    head = "[%s] Art. %s - %s" % (a["id"], a.get("number", ""), a.get("title", ""))
    if a.get("capo"):
        head += "  (%s)" % a["capo"]
    if excerpt:
        head += "  " + EXCERPT_TAG
    return head


def format_article(a, max_chars=None):
    """Header + text; plain head truncation when `max_chars` is given (legacy helper)."""
    text = a.get("text", "")
    cut = max_chars is not None and len(text) > max_chars
    return article_header(a, excerpt=cut) + "\n" + truncate_text(text, max_chars)


def _paragraph_scores(paras, query_tokens):
    """BM25-style score of each paragraph against the query tokens (idf from the paragraphs)."""
    tfs = [Counter(retrieval.tokenize(p)) for p in paras]
    lens = [sum(c.values()) for c in tfs]
    avg = (sum(lens) / len(lens)) if lens else 1.0
    n = len(paras)
    df = Counter()
    for c in tfs:
        df.update(c.keys())
    scores = []
    for c, ln in zip(tfs, lens):
        s = 0.0
        for t in query_tokens:
            f = c.get(t)
            if f:
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                norm = 1 - 0.75 + 0.75 * ln / (avg or 1.0)
                s += idf * f * 2.5 / (f + 1.5 * norm)
        scores.append(s)
    return scores


def trim_text(text, allowance, query_tokens=()):
    """Shrink `text` to about `allowance` chars, keeping what matters for the question.

    Paragraphs are lines. The first paragraph is always kept, then the paragraphs with the best
    overlap with `query_tokens` (then, with room left, the following ones in document order),
    restored to their original order; every gap is marked with an "[...]" line.
    Returns (text, was_trimmed).
    """
    if len(text) <= allowance:
        return text, False
    paras = [x for x in text.split("\n") if x.strip()]
    if not paras:
        return text, False
    room = max(allowance - len(OMIT_MARK) - 1, 0)
    if len(paras[0]) > room:
        return truncate_text(paras[0], room), True
    keep = {0}
    used = len(paras[0]) + 1
    scores = _paragraph_scores(paras, set(query_tokens)) if query_tokens else [0.0] * len(paras)
    for i in sorted(range(1, len(paras)), key=lambda i: (-scores[i], i)):
        cost = len(paras[i]) + 1 + len(OMIT_MARK) + 1  # worst case: a gap marker before it
        if used + cost + len(OMIT_MARK) + 1 <= room:
            keep.add(i)
            used += cost
    out, prev = [], -1
    for i in sorted(keep):
        if i != prev + 1:
            out.append(OMIT_MARK)
        out.append(paras[i])
        prev = i
    if prev != len(paras) - 1:
        out.append(OMIT_MARK)
    return "\n".join(out), True


def _priority(aid, provenance):
    roles = [x.get("role") for x in (provenance or {}).get(aid, [])]
    pris = [_ROLE_PRIORITY[r] for r in roles if r in _ROLE_PRIORITY]
    return min(pris) if pris else P_GENERAL


def _water_fill(lengths, total):
    """Per-item caps with sum <= total, trimming the longest items first."""
    caps = list(lengths)
    if sum(caps) <= total:
        return caps
    left, n = total, len(caps)
    for pos, i in enumerate(sorted(range(n), key=lambda i: caps[i])):
        caps[i] = min(caps[i], left // (n - pos))
        left -= caps[i]
    return caps


def build_answer_prompt(question, findings, articles, keywords="", provenance=None,
                        max_total_chars=DEFAULT_MAX_TOTAL_CHARS, hard_cap_chars=HARD_CAP_CHARS,
                        max_chars_per_article=None):
    """Build the answer prompt with a role-aware character budget.

    Priority: governing articles (role "articles" in `provenance`, as from retrieve()) are
    included in FULL; then BM25 extras (role "bm25"), then general_articles, then
    candidate_articles, each in full while it fits and otherwise trimmed query-aware (trim_text,
    using `question` + `keywords`) to what is left. Trimmed articles carry "(estratto)" in the
    header. If the governing articles alone exceed the budget, the longest are trimmed. The budget
    is min(max_total_chars, hard_cap_chars). Without `provenance` every article counts as
    general and the given order is the priority. `max_chars_per_article` optionally caps the
    non-governing ones. `article_ids` lists the included (citable) ids in priority order.
    """
    budget = min(max_total_chars, hard_cap_chars)
    qtokens = set(retrieval.tokenize("%s %s" % (question or "", keywords or ""), loose=True))
    ranked = sorted(range(len(articles)),
                    key=lambda i: (_priority(articles[i]["id"], provenance), i))
    gov = [i for i in ranked if _priority(articles[i]["id"], provenance) == P_GOVERNING]

    def full_len(i):
        return len(article_header(articles[i])) + 1 + len(articles[i].get("text", ""))

    def render(i, allowance):
        a = articles[i]
        if allowance >= full_len(i):
            return article_header(a) + "\n" + a.get("text", "")
        overhead = len(article_header(a, True)) + 1
        body, cut = trim_text(a.get("text", ""), max(allowance - overhead, 0), qtokens)
        return article_header(a, cut) + "\n" + body

    chosen, used = {}, 0
    if gov:
        for i, cap in zip(gov, _water_fill([full_len(i) + 2 for i in gov], budget)):
            chosen[i] = render(i, cap - 2)
            used += len(chosen[i]) + 2
    for i in ranked:
        if i in chosen:
            continue
        cap = budget - used - 2
        if max_chars_per_article is not None:
            cap = min(cap, max_chars_per_article)
        if cap < MIN_ARTICLE_CHARS and full_len(i) > cap:
            continue
        chosen[i] = render(i, cap)
        used += len(chosen[i]) + 2
    order = [i for i in ranked if i in chosen]
    ids = [articles[i]["id"] for i in order]
    blocks = [chosen[i] for i in order]
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
