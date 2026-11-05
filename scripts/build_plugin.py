"""Assemble dist/norme_milano/ (plugin + core + runtime data) and zip it.

    python scripts/build_plugin.py

Outputs dist/norme_milano-<version>.zip (version read from plugin/metadata.txt) and a
convenience copy dist/norme_milano.zip, then validates the archive with check_plugin_zip.py
and exits non-zero if any rule is broken.

Only runtime files are shipped: plugin/*.py, metadata.txt, icon, core/*.py, LICENSE, and the
four runtime data files (articles.json, documents.json, zone_map.json, constraint_map.json).
data/raw and the YAML sources stay out. Zip entries use forward slashes, with the single
top-level folder norme_milano/ as QGIS expects.
"""

import shutil
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_plugin_zip  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
NAME = "norme_milano"
RUNTIME_DATA = ("articles.json", "documents.json", "zone_map.json", "constraint_map.json")
# Whitelist of what plugin/ and core/ may contribute (no stray files get shipped).
PLUGIN_SUFFIXES = {".py", ".txt", ".png", ".svg"}
CORE_SUFFIXES = {".py"}


def read_version():
    for line in (ROOT / "plugin" / "metadata.txt").read_text(encoding="utf-8").splitlines():
        if line.startswith("version="):
            return line.split("=", 1)[1].strip()
    sys.exit("version= not found in plugin/metadata.txt")


def _copy_flat(src, dst, suffixes):
    """Copy files of the given suffixes from src (no recursion, so no __pycache__)."""
    dst.mkdir(parents=True, exist_ok=True)
    for path in sorted(src.iterdir()):
        if path.is_file() and path.suffix in suffixes:
            shutil.copy2(path, dst / path.name)


def build():
    version = read_version()
    out = DIST / NAME
    if out.exists():
        shutil.rmtree(out)
    _copy_flat(ROOT / "plugin", out, PLUGIN_SUFFIXES)
    _copy_flat(ROOT / "core", out / "core", CORE_SUFFIXES)
    (out / "data").mkdir(parents=True, exist_ok=True)
    for fname in RUNTIME_DATA:
        src = ROOT / "data" / fname
        if not src.exists():
            sys.exit("missing runtime data file: %s" % src)
        shutil.copy2(src, out / "data" / fname)
    licence = ROOT / "LICENSE"
    if not licence.exists():
        sys.exit("LICENSE is missing")
    shutil.copy2(licence, out / "LICENSE")

    versioned = DIST / ("%s-%s.zip" % (NAME, version))
    plain = DIST / (NAME + ".zip")
    for z in (versioned, plain):
        if z.exists():
            z.unlink()
    with zipfile.ZipFile(versioned, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(out.rglob("*")):
            if path.is_file():
                zf.write(path, (Path(NAME) / path.relative_to(out)).as_posix())
    shutil.copy2(versioned, plain)
    return versioned, plain


if __name__ == "__main__":
    versioned, plain = build()
    with zipfile.ZipFile(versioned) as zf:
        names = zf.namelist()
    print("built %s (%d files, %d bytes) and %s"
          % (versioned, len(names), versioned.stat().st_size, plain.name))
    for n in names:
        print("  " + n)
    problems = check_plugin_zip.check(versioned)
    if problems:
        print("\nZIP VALIDATION FAILED:")
        for p in problems:
            print("  - " + p)
        sys.exit(1)
    print("\nzip validation OK")
