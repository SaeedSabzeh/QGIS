"""Command-line entry point.

    python -m core.ask <lat> <lon> ["question"] [--provider gemini|ollama] [--model M]
                                  [--no-fallback]

Without a question, or without a Gemini key (env GEMINI_API_KEY), it prints the findings and the
mapped articles (no-key mode). With a question it rewrites it to Italian keywords, retrieves,
asks the model and prints the answer in Italian and English with the cited articles.
Gemini transient errors are retried, then the next model in llm.DEFAULT_GEMINI_FALLBACKS is
tried (--model sets the primary model; --no-fallback disables the chain).
"""

import argparse
import contextlib
import os
import sys

from . import llm, prompts, retrieval, services

TEXT_PREVIEW = 400


def _print_findings(findings, errors, out):
    p = lambda s="": print(s, file=out)  # noqa: E731
    if errors:
        p("Layers that failed (%d): %s" % (len(errors), ", ".join(sorted(errors))))
    if not findings:
        p("No planning constraint or zone found at this point.")
        return
    p("Findings (%d):" % len(findings))
    for f in findings:
        p(prompts.format_finding(f))
    p()


def _print_articles(ids, provenance, by_id, out, full_text=False):
    p = lambda s="": print(s, file=out)  # noqa: E731
    if not ids:
        p("No mapped articles.")
        return
    p("Articles (%d):" % len(ids))
    for aid in ids:
        a = by_id.get(aid)
        if not a:
            continue
        roles = sorted({x["role"] for x in provenance.get(aid, [])})
        p("  [%s] %s - %s  <%s>" % (aid, retrieval.cite_label(a), a.get("title"),
                                       ", ".join(roles)))
        if full_text:
            p("      " + a.get("text", "").replace("\n", "\n      "))
    p()


def _footer(out, ids=(), data_dir=None):
    used = retrieval.sources_used(ids, data_dir) if ids else ""
    if used:
        print("Documents used: %s." % used, file=out)
    print(prompts.DISCLAIMER_EN, file=out)
    print(prompts.DISCLAIMER_IT, file=out)
    print(prompts.LIMITATION_EN, file=out)


def run(argv=None, query_fn=None, transport=None, env=None, out=None, data_dir=None,
        sleep=None, err=None):
    """Run the CLI; returns the process exit code. Injectable for tests."""
    out = out or sys.stdout
    err = err or sys.stderr
    progress = lambda m: print(m, file=err)  # noqa: E731
    env = os.environ if env is None else env
    ap = argparse.ArgumentParser(prog="python -m core.ask", description=__doc__.split("\n\n")[0])
    ap.add_argument("lat", type=float)
    ap.add_argument("lon", type=float)
    ap.add_argument("question", nargs="?", default=None)
    ap.add_argument("--provider", choices=["gemini", "ollama"], default="gemini")
    ap.add_argument("--model", default=None, help="primary model")
    ap.add_argument("--no-fallback", action="store_true",
                    help="do not fall back to other Gemini models on failure")
    ap.add_argument("--base-url", default=None, help="Ollama base URL")
    ap.add_argument("-k", type=int, default=None,
                    help="max BM25 extra articles (default: 5 with mapped articles, 8 without)")
    ap.add_argument("--full-text", action="store_true", help="print full article texts")
    args = ap.parse_args(argv)
    p = lambda s="": print(s, file=out)  # noqa: E731

    p("Point: lat %s, lon %s" % (args.lat, args.lon))
    try:
        result = (query_fn or services.query_all)(args.lat, args.lon)
    except Exception as exc:  # query_all should not raise, but never show a traceback
        print("Could not query the map services: %s" % exc, file=sys.stderr)
        return 1
    errors = result.get("errors", {})
    if result.get("layers") and len(errors) == len(result["layers"]):
        print("All map services failed (network?). First error: %s" % next(iter(errors.values())),
              file=sys.stderr)
        return 1

    by_id = retrieval.articles_by_id(data_dir)
    findings = retrieval.lookup(result, data_dir)
    _print_findings(findings, errors, out)

    key = env.get("GEMINI_API_KEY", "").strip()
    use_llm = bool(args.question) and (args.provider == "ollama" or bool(key))

    if not use_llm:
        ret = retrieval.retrieve(result, None, findings=findings, data_dir=data_dir)
        _print_articles(ret["ids"], ret["provenance"], by_id, out, args.full_text)
        if args.question:
            p("Free-text questions need an LLM: set GEMINI_API_KEY or use --provider ollama.")
            p("(No-key mode shows only the constraints and the mapped articles.)")
        _footer(out, ret["ids"], data_dir)
        return 0

    used_ids = []
    try:
        client = llm.make_client(
            args.provider, args.model, key, args.base_url, transport,
            fallbacks=() if args.no_fallback else llm.DEFAULT_GEMINI_FALLBACKS, sleep=sleep)
        keywords = args.question
        try:
            kw = prompts.keywords_from_text(
                client.complete(prompts.build_keywords_prompt(args.question),
                                on_progress=progress, budget=llm.KEYWORDS_BUDGET))
            if kw:
                keywords = kw
        except llm.LLMError as exc:
            print("WARNING: keyword rewrite failed (%s); searching with the original question"
                  % exc, file=sys.stderr)
        p("Italian keywords: %s" % keywords)
        ret = retrieval.retrieve(result, keywords, k=args.k, findings=findings,
                                 data_dir=data_dir)
        used_ids = ret["ids"]
        articles = [by_id[i] for i in ret["ids"] if i in by_id]
        _print_articles(ret["ids"], ret["provenance"], by_id, out, args.full_text)
        prompt = prompts.build_answer_prompt(
            args.question, findings, articles, keywords=keywords, provenance=ret["provenance"])
        ans = llm.parse_answer(client.complete(prompt, on_progress=progress),
                               prompt["article_ids"])
        p("Model: %s" % (client.last_model or client.model))
    except llm.LLMError as exc:
        print("LLM request failed: %s" % exc, file=sys.stderr)
        p("The findings and articles above are still valid.")
        _footer(out, used_ids, data_dir)
        return 1

    p("Risposta (IT): %s" % ans["answer_it"])
    p()
    p("Answer (EN): %s" % ans["answer_en"])
    p()
    p("Cited articles: %s" % (", ".join(ans["cited_articles"]) or "none"))
    if ans["rejected_citations"]:
        p("WARNING: the model cited articles that were not supplied and were removed: %s"
          % ", ".join(ans["rejected_citations"]))
    if ans["parse_error"]:
        p("WARNING: the model reply was not valid JSON; shown as raw text, citations dropped.")
    p()
    _footer(out, prompt["article_ids"], data_dir)
    return 0


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        # streams without reconfigure() (or already closed) keep their encoding
        with contextlib.suppress(AttributeError, OSError, ValueError):
            stream.reconfigure(encoding="utf-8", errors="replace")
    return run(argv)


if __name__ == "__main__":
    sys.exit(main())
