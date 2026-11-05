"""Validate a built plugin zip against the plugins.qgis.org upload rules.

    python scripts/check_plugin_zip.py [dist/norme_milano-0.1.0.zip]

Exit code 1 (with a list of problems) if any rule is broken.
"""

import configparser
import re
import sys
import zipfile
from pathlib import Path

NAME = "norme_milano"
MAX_BYTES = 5 * 1024 * 1024
REQUIRED_META = ("name", "qgisMinimumVersion", "description", "about", "version", "author",
                 "email", "repository", "tracker")
REQUIRED_FILES = ("__init__.py", "metadata.txt", "icon.png", "LICENSE", "main.py",
                  "core/__init__.py", "data/articles.json", "data/documents.json",
                  "data/zone_map.json", "data/constraint_map.json")
ALLOWED_DATA = {"articles.json", "documents.json", "zone_map.json", "constraint_map.json"}
FORBIDDEN_PARTS = {"__pycache__", "tests", "eval", "scripts", "raw", ".git", "docs"}
FORBIDDEN_SUFFIXES = (".pyc", ".pyo", ".yaml", ".yml", ".exe", ".dll", ".so", ".dylib", ".pdf",
                      ".docx", ".zip", ".qgz", ".env")
SECRET_RE = re.compile(r"AIza[0-9A-Za-z_\-]{30,}|sk-[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY")


def check(zip_path):
    problems = []
    zip_path = Path(zip_path)
    if not zip_path.exists():
        return ["zip not found: %s" % zip_path]
    if zip_path.stat().st_size > MAX_BYTES:
        problems.append("zip larger than %d bytes (%d)" % (MAX_BYTES, zip_path.stat().st_size))
    with zipfile.ZipFile(zip_path) as zf:
        bad = zf.testzip()
        if bad:
            problems.append("corrupt entry: %s" % bad)
        names = [n for n in zf.namelist() if not n.endswith("/")]
        tops = {n.split("/")[0] for n in zf.namelist()}
        if tops != {NAME}:
            problems.append("must have exactly one top-level folder %r, found %s"
                            % (NAME, sorted(tops)))
        rel = {n.split("/", 1)[1]: n for n in names if "/" in n}
        for n in names:
            if "\\" in n or n.startswith("/") or ".." in n.split("/"):
                problems.append("bad path: %s" % n)
        for r in REQUIRED_FILES:
            if r not in rel:
                problems.append("missing file: %s" % r)
        for r in rel:
            parts = set(r.split("/"))
            if parts & FORBIDDEN_PARTS:
                problems.append("forbidden path: %s" % r)
            if r.lower().endswith(FORBIDDEN_SUFFIXES):
                problems.append("forbidden file type: %s" % r)
            if r.startswith("data/") and r[5:] not in ALLOWED_DATA:
                problems.append("unexpected data file: %s" % r)
            if r.startswith("core/") and not r.endswith(".py"):
                problems.append("unexpected file in core/: %s" % r)
        if "metadata.txt" in rel:
            cp = configparser.ConfigParser(interpolation=None)
            cp.read_string(zf.read(rel["metadata.txt"]).decode("utf-8"))
            meta = dict(cp["general"]) if cp.has_section("general") else {}
            low = {k.lower(): v for k, v in meta.items()}
            for key in REQUIRED_META:
                if not low.get(key.lower(), "").strip():
                    problems.append("metadata.txt: missing or empty %s" % key)
            ver = low.get("version", "")
            if ver and not re.fullmatch(r"\d+\.\d+\.\d+", ver):
                problems.append("metadata.txt: version %r is not X.Y.Z" % ver)
            if low.get("icon") and low["icon"] not in rel:
                problems.append("metadata.txt: icon %r not in zip" % low["icon"])
            if ver and zip_path.name.startswith(NAME + "-") and zip_path.name != (
                    "%s-%s.zip" % (NAME, ver)):
                problems.append("zip file name does not match version %s" % ver)
        for r, full in rel.items():
            if r.endswith(".py"):
                text = zf.read(full).decode("utf-8", "replace")
                if SECRET_RE.search(text):
                    problems.append("possible hardcoded secret in %s" % r)
                if re.search(r"^\s*(eval|exec)\(", text, re.M):
                    problems.append("eval/exec call in %s" % r)
    return problems


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else str(
        Path(__file__).resolve().parents[1] / "dist" / "norme_milano.zip")
    found = check(target)
    if found:
        print("FAILED:")
        for p in found:
            print("  - " + p)
        sys.exit(1)
    print("OK: %s" % target)
