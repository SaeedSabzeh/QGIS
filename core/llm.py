"""Gemini and Ollama over plain REST (urllib), no SDKs (Phase 2).

Both clients expose `complete(prompt_parts) -> str`, where prompt_parts is a dict with "system" and
"user" strings (see core.prompts). The HTTP transport is injectable:
`transport(url, headers, payload, timeout) -> dict`. The API key is only ever sent in a header
and never logged or included in error messages.
"""

import json
import re
import urllib.error
import urllib.request

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"  # change here; also settable per call / --model
DEFAULT_OLLAMA_MODEL = "llama3.1"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


class LLMError(Exception):
    """Network, HTTP or response-format failure from an LLM provider."""


def post_json(url, headers, payload, timeout=60):
    """Default transport: POST `payload` as JSON, return the decoded JSON reply."""
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", "replace")[:500]
        except Exception:
            pass
        raise LLMError("HTTP %s from %s: %s" % (exc.code, url.split("?")[0], body)) from None
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise LLMError("request to %s failed: %s" % (url.split("?")[0], exc)) from None


class GeminiClient:
    def __init__(self, api_key, model=DEFAULT_GEMINI_MODEL, transport=None, timeout=60,
                 temperature=0.2):
        if not api_key:
            raise LLMError("Gemini needs an API key")
        self._key = api_key
        self.model = model
        self.transport = transport or post_json
        self.timeout = timeout
        self.temperature = temperature

    @property
    def url(self):
        return "%s/models/%s:generateContent" % (GEMINI_BASE, self.model)

    def build_request(self, prompt_parts):
        headers = {"Content-Type": "application/json", "x-goog-api-key": self._key}
        payload = {
            "systemInstruction": {"parts": [{"text": prompt_parts.get("system", "")}]},
            "contents": [{"role": "user", "parts": [{"text": prompt_parts["user"]}]}],
            "generationConfig": {"responseMimeType": "application/json",
                                 "temperature": self.temperature},
        }
        return self.url, headers, payload

    def complete(self, prompt_parts):
        url, headers, payload = self.build_request(prompt_parts)
        try:
            data = self.transport(url, headers, payload, self.timeout)
        except LLMError as exc:
            raise LLMError(str(exc).replace(self._key, "***")) from None
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


class OllamaClient:
    def __init__(self, model=DEFAULT_OLLAMA_MODEL, base_url=DEFAULT_OLLAMA_URL, transport=None,
                 timeout=300):
        self.model = model
        self.base_url = (base_url or DEFAULT_OLLAMA_URL).rstrip("/")
        self.transport = transport or post_json
        self.timeout = timeout

    def build_request(self, prompt_parts):
        messages = []
        if prompt_parts.get("system"):
            messages.append({"role": "system", "content": prompt_parts["system"]})
        messages.append({"role": "user", "content": prompt_parts["user"]})
        payload = {"model": self.model, "messages": messages, "stream": False, "format": "json"}
        return self.base_url + "/api/chat", {"Content-Type": "application/json"}, payload

    def complete(self, prompt_parts):
        url, headers, payload = self.build_request(prompt_parts)
        data = self.transport(url, headers, payload, self.timeout)
        try:
            text = data["message"]["content"]
        except (KeyError, TypeError):
            raise LLMError("unexpected Ollama response") from None
        if not text or not text.strip():
            raise LLMError("Ollama returned an empty answer")
        return text


def make_client(provider, model=None, api_key=None, base_url=None, transport=None):
    provider = (provider or "gemini").lower()
    if provider == "gemini":
        return GeminiClient(api_key, model or DEFAULT_GEMINI_MODEL, transport=transport)
    if provider == "ollama":
        return OllamaClient(model or DEFAULT_OLLAMA_MODEL, base_url or DEFAULT_OLLAMA_URL,
                            transport=transport)
    raise LLMError("unknown provider: %s" % provider)


# ---------------------------------------------------------------------------------------------
# Answer parsing
# ---------------------------------------------------------------------------------------------
_FENCE = re.compile(r"^\s*```[a-zA-Z0-9]*\s*|\s*```\s*$")
_ART_NUM = re.compile(r"^\s*(?:art(?:icolo)?\.?\s*)?(\d+)\s*$", re.IGNORECASE)


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
    """Map 45, "45", "art. 45", "PR-art-45" to "PR-art-45"; leave anything else as a string."""
    if isinstance(c, int):
        return "PR-art-%d" % c
    s = str(c).strip()
    m = _ART_NUM.match(s)
    return "PR-art-%s" % m.group(1) if m else s


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
