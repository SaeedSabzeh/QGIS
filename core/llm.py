"""Gemini and Ollama over plain REST (urllib), no SDKs (Phase 2).

Both clients expose `complete(prompt_parts) -> str`, where prompt_parts is a dict with "system" and
"user" strings (see core.prompts). The HTTP transport is injectable:
`transport(url, headers, payload, timeout) -> dict`. The API key is only ever sent in a header
and never logged or included in error messages.
"""

import contextlib
import json
import random
import re
import time
import urllib.error
import urllib.request

from . import urlcheck

DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"  # change here; also settable per call / --model
# Tried in order when the primary model keeps failing (overloaded / unavailable). Easy to edit.
DEFAULT_GEMINI_FALLBACKS = ("gemini-3.5-flash", "gemini-3.1-flash-lite")
DEFAULT_OLLAMA_MODEL = "llama3.1"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"

TRANSIENT_STATUSES = frozenset({429, 500, 502, 503, 504})
DEFAULT_MAX_ATTEMPTS = 3   # per model
DEFAULT_BASE_DELAY = 2.0   # seconds; doubles each retry
DEFAULT_MAX_DELAY = 20.0   # cap for backoff and for a Retry-After header


class LLMError(Exception):
    """Network, HTTP or response-format failure from an LLM provider.

    status: HTTP status code when known; retry_after: seconds from a Retry-After header;
    transient: True when retrying (or trying another model) may help.
    """

    def __init__(self, message="", status=None, retry_after=None, transient=False):
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after
        self.transient = transient


def _parse_retry_after(value):
    try:
        secs = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return secs if secs >= 0 else None


def post_json(url, headers, payload, timeout=60):
    """Default transport: POST `payload` as JSON, return the decoded JSON reply."""
    urlcheck.check_url(url)
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        # scheme validated by urlcheck.check_url above (https, or http to localhost only)
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = ""
        # an unreadable error body just stays empty
        with contextlib.suppress(OSError, ValueError):
            body = exc.read().decode("utf-8", "replace")[:500]
        retry_after = None
        # missing or odd headers just mean no Retry-After hint
        with contextlib.suppress(AttributeError, TypeError, ValueError):
            retry_after = _parse_retry_after(exc.headers.get("Retry-After"))
        raise LLMError("HTTP %s from %s: %s" % (exc.code, url.split("?")[0], body),
                       status=exc.code, retry_after=retry_after,
                       transient=exc.code in TRANSIENT_STATUSES) from None
    except (urllib.error.URLError, OSError) as exc:  # includes timeouts / connection errors
        raise LLMError("request to %s failed: %s" % (url.split("?")[0], exc),
                       transient=True) from None
    except ValueError as exc:  # unreadable JSON reply
        raise LLMError("request to %s failed: %s" % (url.split("?")[0], exc)) from None


class _Retrying:
    """Shared retry-with-backoff logic for the clients."""

    def _init_retry(self, max_attempts, base_delay, max_delay, sleep, rng):
        self.max_attempts = max(1, int(max_attempts))
        self.base_delay = base_delay
        self.max_delay = max_delay
        self._sleep = sleep or time.sleep
        self._rng = rng or random.random

    def _delay(self, attempt, exc):
        """Seconds to wait after failed attempt number `attempt` (1-based)."""
        if getattr(exc, "retry_after", None) is not None:
            return min(float(exc.retry_after), self.max_delay)
        backoff = min(self.max_delay, self.base_delay * (2 ** (attempt - 1)))
        return backoff * (0.5 + 0.5 * self._rng())  # jitter: 50-100% of the backoff

    def _send(self, url, headers, payload, scrub=None):
        """Call the transport, retrying transient errors. Raises LLMError when attempts are
        used up or the error is not transient."""
        last = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return self.transport(url, headers, payload, self.timeout)
            except LLMError as exc:
                err = exc
            except OSError as exc:  # raw timeout / connection error from a custom transport
                err = LLMError("request failed: %s" % exc, transient=True)
            if scrub:
                err = LLMError(str(err).replace(scrub, "***"), status=err.status,
                               retry_after=err.retry_after, transient=err.transient)
            last = err
            if not err.transient or attempt >= self.max_attempts:
                break
            self._sleep(self._delay(attempt, err))
        raise last from None


class GeminiClient(_Retrying):
    def __init__(self, api_key, model=DEFAULT_GEMINI_MODEL, transport=None, timeout=60,
                 temperature=0.2, fallbacks=DEFAULT_GEMINI_FALLBACKS,
                 max_attempts=DEFAULT_MAX_ATTEMPTS, base_delay=DEFAULT_BASE_DELAY,
                 max_delay=DEFAULT_MAX_DELAY, sleep=None, rng=None):
        if not api_key:
            raise LLMError("Gemini needs an API key")
        self._key = api_key
        self.model = model
        self.fallbacks = tuple(fallbacks or ())
        self.transport = transport or post_json
        self.timeout = timeout
        self.temperature = temperature
        self.last_model = None  # model that actually produced the last answer
        self._init_retry(max_attempts, base_delay, max_delay, sleep, rng)

    @property
    def models(self):
        """Primary model followed by the fallbacks, without duplicates."""
        chain = []
        for m in (self.model,) + self.fallbacks:
            if m and m not in chain:
                chain.append(m)
        return chain

    def _url(self, model):
        return "%s/models/%s:generateContent" % (GEMINI_BASE, model)

    @property
    def url(self):
        return self._url(self.model)

    def build_request(self, prompt_parts, model=None):
        headers = {"Content-Type": "application/json", "x-goog-api-key": self._key}
        payload = {
            "systemInstruction": {"parts": [{"text": prompt_parts.get("system", "")}]},
            "contents": [{"role": "user", "parts": [{"text": prompt_parts["user"]}]}],
            "generationConfig": {"responseMimeType": "application/json",
                                 "temperature": self.temperature},
        }
        return self._url(model or self.model), headers, payload

    def complete(self, prompt_parts):
        data = None
        last = None
        for model in self.models:
            url, headers, payload = self.build_request(prompt_parts, model)
            try:
                data = self._send(url, headers, payload, scrub=self._key)
            except LLMError as exc:
                last = exc
                if exc.transient or exc.status == 404:
                    continue  # overloaded or unavailable: try the next model
                raise
            self.last_model = model
            break
        else:
            raise last
        try:
            cands = data.get("candidates") or []
            if not cands:
                block = (data.get("promptFeedback") or {}).get("blockReason")
                raise LLMError("Gemini returned no candidates" + (" (blocked: %s)" % block if block else ""))
            parts = (cands[0].get("content") or {}).get("parts") or []
            text = "".join(p.get("text", "") for p in parts)
        except AttributeError:
            raise LLMError("unexpected Gemini response") from None
        if not text.strip():
            raise LLMError("Gemini returned an empty answer")
        return text


class OllamaClient(_Retrying):
    def __init__(self, model=DEFAULT_OLLAMA_MODEL, base_url=DEFAULT_OLLAMA_URL, transport=None,
                 timeout=300, max_attempts=DEFAULT_MAX_ATTEMPTS, base_delay=DEFAULT_BASE_DELAY,
                 max_delay=DEFAULT_MAX_DELAY, sleep=None, rng=None):
        self.model = model
        self.base_url = (base_url or DEFAULT_OLLAMA_URL).rstrip("/")
        self.transport = transport or post_json
        self.timeout = timeout
        self.last_model = None
        self._init_retry(max_attempts, base_delay, max_delay, sleep, rng)

    def build_request(self, prompt_parts):
        messages = []
        if prompt_parts.get("system"):
            messages.append({"role": "system", "content": prompt_parts["system"]})
        messages.append({"role": "user", "content": prompt_parts["user"]})
        payload = {"model": self.model, "messages": messages, "stream": False, "format": "json"}
        return self.base_url + "/api/chat", {"Content-Type": "application/json"}, payload

    def complete(self, prompt_parts):
        url, headers, payload = self.build_request(prompt_parts)
        data = self._send(url, headers, payload)  # retries only; no model fallback
        self.last_model = self.model
        try:
            text = data["message"]["content"]
        except (KeyError, TypeError):
            raise LLMError("unexpected Ollama response") from None
        if not text or not text.strip():
            raise LLMError("Ollama returned an empty answer")
        return text


def make_client(provider, model=None, api_key=None, base_url=None, transport=None,
                fallbacks=DEFAULT_GEMINI_FALLBACKS, sleep=None):
    """`fallbacks=()` disables the Gemini model chain. `sleep` is injectable for tests."""
    provider = (provider or "gemini").lower()
    if provider == "gemini":
        return GeminiClient(api_key, model or DEFAULT_GEMINI_MODEL, transport=transport,
                            fallbacks=fallbacks, sleep=sleep)
    if provider == "ollama":
        return OllamaClient(model or DEFAULT_OLLAMA_MODEL, base_url or DEFAULT_OLLAMA_URL,
                            transport=transport, sleep=sleep)
    raise LLMError("unknown provider: %s" % provider)


# ---------------------------------------------------------------------------------------------
# Answer parsing
# ---------------------------------------------------------------------------------------------
_FENCE = re.compile(r"^\s*```[a-zA-Z0-9]*\s*|\s*```\s*$")
_ART_NUM = re.compile(r"^\s*(?:art(?:icolo)?\.?\s*)?(\d+)\s*$", re.IGNORECASE)
# "PS art. 11", "PS-art-11", "PS art 11", "DPA1 sez. 21", "DPA1-sec-21", "PTC all. A", "PTC-all-A"
_DOC_ART = re.compile(
    r"^\s*([A-Za-z][A-Za-z0-9]*)[\s\-_]*(art(?:icolo)?|sec|sez(?:ione)?|all(?:egato)?)"
    r"[\s.\-_]*([0-9]+|[A-Za-z])\s*$", re.IGNORECASE)
_KIND = {"art": "art", "articolo": "art", "sec": "sec", "sez": "sec", "sezione": "sec",
         "all": "all", "allegato": "all"}


def _extract_json(text):
    text = _FENCE.sub("", text.strip())
    text = _FENCE.sub("", text)
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object")
    obj, _ = json.JSONDecoder().raw_decode(text[start:])
    if not isinstance(obj, dict):
        raise ValueError("not an object")
    return obj


def normalize_citation(c):
    """Map a citation to a record id. A bare number is a Piano delle Regole article: 45, "45",
    "art. 45" -> "PR-art-45". With a document code: "PS art. 11", "ps-art-11" -> "PS-art-11",
    "DPA1 sez. 21" -> "DPA1-sec-21", "PTC all. A" -> "PTC-all-A". Anything else is returned
    as a string."""
    if isinstance(c, int):
        return "PR-art-%d" % c
    s = str(c).strip()
    m = _ART_NUM.match(s)
    if m:
        return "PR-art-%s" % m.group(1)
    m = _DOC_ART.match(s)
    if m:
        kind = _KIND[m.group(2).lower()]
        num = m.group(3)
        return "%s-%s-%s" % (m.group(1).upper(), kind, num.upper() if kind == "all" else num)
    return s


def parse_answer(text, allowed_ids):
    """Parse the model reply. Returns a dict:

    answer_it, answer_en, cited_articles (only ids in `allowed_ids`), rejected_citations
    (cited but not supplied), parse_error (bool; True when the reply was not valid JSON, in
    which case the raw text is returned as both answers and no citations are accepted).
    """
    allowed = set(allowed_ids)
    try:
        obj = _extract_json(text)
    except ValueError:
        return {"answer_it": text.strip(), "answer_en": text.strip(), "cited_articles": [],
                "rejected_citations": [], "parse_error": True}
    cited, rejected = [], []
    raw = obj.get("cited_articles") or []
    if not isinstance(raw, list):
        raw = [raw]
    for c in raw:
        cid = normalize_citation(c)
        bucket = cited if cid in allowed else rejected
        if cid not in bucket:
            bucket.append(cid)
    return {
        "answer_it": str(obj.get("answer_it") or obj.get("answer") or ""),
        "answer_en": str(obj.get("answer_en") or ""),
        "cited_articles": cited,
        "rejected_citations": rejected,
        "parse_error": False,
    }
