"""Quiet invitation to the Pro early-access group.

After the user's third successful lookup in Milan, a one-line strip appears at the bottom of
the panel until the user opens the link or closes it; then it never returns (per QGIS profile).
A permanent link also sits at the bottom of the Settings dialog.

The plugin collects and sends nothing for this: the link only opens the sign-up page in the
browser, with no user data in the address. Everything stays off until SIGNUP_URL points to a
published page.
"""

from urllib.parse import urlencode

from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtGui import QDesktopServices

SIGNUP_URL = ""  # the website's early-access page, e.g. "https://.../pro"; empty = off
SHOW_AFTER = 3   # successful lookups before the strip appears


def enabled():
    return bool(SIGNUP_URL)


def signup_url(lang):
    """The sign-up address with only non-personal hints (source and language)."""
    if not SIGNUP_URL:
        return ""
    sep = "&" if "?" in SIGNUP_URL else "?"
    return SIGNUP_URL + sep + urlencode({"src": "plugin", "lang": lang})


def next_state(count, resolved):
    """(new_count, show_strip) after one more successful lookup. Counting stops once the
    invitation is resolved (opened or closed) or while the feature is off."""
    if resolved or not enabled():
        return count, False
    count = int(count or 0) + 1
    return count, count >= SHOW_AFTER


def open_signup(lang):
    """Open the sign-up page in the browser. True when the browser accepted the request."""
    url = signup_url(lang)
    return bool(url) and bool(QDesktopServices.openUrl(QUrl(url)))
