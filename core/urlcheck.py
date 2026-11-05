"""URL scheme guard for the urllib-based default network functions (standard library only)."""

import urllib.parse

LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def check_url(url):
    """Return `url` if it is https, or http to a local host (Ollama default); else ValueError."""
    parts = urllib.parse.urlsplit(str(url))
    if parts.scheme == "https" and parts.hostname:
        return url
    if parts.scheme == "http" and parts.hostname in LOCAL_HOSTS:
        return url
    raise ValueError("refusing URL with scheme %r: only https (or http to localhost) is allowed"
                     % parts.scheme)
