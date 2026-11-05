"""Import shim: core library + small Qt/QGIS enum helpers.

Packaged layout (scripts/build_plugin.py): core/ and data/ sit inside the plugin package, so
`from .core import ...` works. Development layout: core/ is next to plugin/ in the repo, so
fall back to putting the repo root on sys.path.
"""

import contextlib
import sys
from pathlib import Path

try:
    from .core import llm, pipeline, prompts, retrieval, services  # noqa: F401
except ImportError:
    _root = str(Path(__file__).resolve().parents[1])
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from core import llm, pipeline, prompts, retrieval, services  # noqa: F401


def enum(cls, scope, name):
    """Return `cls.<scope>.<name>` (scoped, Qt6/QGIS 4 style), else `cls.<name>` (older QGIS)."""
    holder = getattr(cls, scope, None)
    if holder is not None and hasattr(holder, name):
        return getattr(holder, name)
    return getattr(cls, name)


def log(message, level="Info"):
    """Write a line to the QGIS message log (tag "Norme Milano"). Never pass secrets here."""
    # logging must never break the plugin
    with contextlib.suppress(ImportError, AttributeError, RuntimeError):
        from qgis.core import Qgis, QgsMessageLog
        QgsMessageLog.logMessage(str(message), "Norme Milano", enum(Qgis, "MessageLevel", level))
