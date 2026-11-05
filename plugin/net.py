"""Network adapters on top of QgsNetworkAccessManager (respects the QGIS proxy settings).

`make_fetch()` -> fetch(url, timeout) for core.services.query_all.
`make_transport()` -> transport(url, headers, payload, timeout) for core.llm clients.
Both use blocking calls and are meant to run inside a QgsTask (a worker thread), never on the
UI thread. HTTP failures become core's LLMError with status / retry_after / transient set, so
the retry and model-fallback logic keeps working. Secrets are only sent in headers and never
appear in messages (URLs are logged without their query string).
"""

import json

from qgis.core import QgsNetworkAccessManager
from qgis.PyQt.QtCore import QByteArray, QUrl
from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest

from ._compat import enum, llm

MAX_BODY_IN_ERROR = 300


class Canceled(Exception):
    """Raised by the adapters when the running QgsTask was canceled."""


def _safe_url(url):
    return str(url).split("?")[0]


def parse_retry_after(value):
    try:
        secs = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return secs if secs >= 0 else None


def interpret(url, status, body, net_error=None, retry_after=None):
    """Turn an HTTP outcome into decoded JSON or raise llm.LLMError.

    status: HTTP status or None/0 when none was received; body: bytes; net_error: Qt error
    string when the request failed at the network level.
    """
    where = _safe_url(url)
    if not status:
        raise llm.LLMError("request to %s failed: %s" % (where, net_error or "no response"),
                           transient=True)
    if status >= 400:
        snippet = body[:MAX_BODY_IN_ERROR].decode("utf-8", "replace") if body else ""
        raise llm.LLMError("HTTP %s from %s: %s" % (status, where, snippet), status=status,
                           retry_after=parse_retry_after(retry_after),
                           transient=status in llm.TRANSIENT_STATUSES)
    if not 200 <= status < 300:
        raise llm.LLMError("HTTP %s from %s" % (status, where), status=status)
    try:
        return json.loads(body.decode("utf-8"))
    except ValueError:
        raise llm.LLMError("unreadable JSON reply from %s" % where) from None


def _read_reply(reply):
    attr = enum(QNetworkRequest, "Attribute", "HttpStatusCodeAttribute")
    status = reply.attribute(attr)
    status = int(status) if status is not None else 0
    body = bytes(reply.content())
    retry = None
    try:
        raw = reply.rawHeader(QByteArray(b"Retry-After"))
        retry = bytes(raw).decode("ascii", "ignore") or None
    except Exception:
        pass
    no_error = enum(QNetworkReply, "NetworkError", "NoError")
    net_error = None if reply.error() == no_error else reply.errorString()
    return status, body, net_error, retry


def _request(url, headers, timeout):
    req = QNetworkRequest(QUrl(url))
    for name, value in (headers or {}).items():
        req.setRawHeader(QByteArray(name.encode("ascii")), QByteArray(str(value).encode("utf-8")))
    if timeout and hasattr(req, "setTransferTimeout"):
        req.setTransferTimeout(int(timeout * 1000))
    return req


def _check(is_canceled):
    if is_canceled and is_canceled():
        raise Canceled("canceled")


def make_fetch(is_canceled=None):
    def fetch(url, timeout=20):
        _check(is_canceled)
        reply = QgsNetworkAccessManager.instance().blockingGet(_request(url, {}, timeout))
        status, body, net_error, retry = _read_reply(reply)
        _check(is_canceled)
        return interpret(url, status, body, net_error, retry)
    return fetch


def make_transport(is_canceled=None):
    def transport(url, headers, payload, timeout):
        _check(is_canceled)
        data = QByteArray(json.dumps(payload).encode("utf-8"))
        reply = QgsNetworkAccessManager.instance().blockingPost(
            _request(url, headers, timeout), data)
        status, body, net_error, retry = _read_reply(reply)
        _check(is_canceled)
        return interpret(url, status, body, net_error, retry)
    return transport
