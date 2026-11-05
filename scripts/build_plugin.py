"""Assemble dist/norme_milano/ (plugin + core + runtime data) and zip it to dist/norme_milano.zip.

    python scripts/build_plugin.py

Only the runtime data files are shipped (articles.json, zone_map.json, constraint_map.json);
data/raw and the YAML sources stay out. Zip entries use forward slashes, with the top-level
folder norme_milano/ as QGIS expects.
"""

import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
NAME = "norme_milano"
RUNTIME_DATA = ("articles.json", "zone_map.json", "constraint_map.json")
SKIP_DIRS = {"__pycache__"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


def _copy_tree(src, dst):
    for path in sorted(src.rglob("*")):
        rel = path.relative_to(src)
        if path.is_dir() or SKIP_DIRS & set(rel.parts) or path.suffix in SKIP_SUFFIXES:
            continue
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def build():
    out = DIST / NAME
    if out.exists():
        shutil.rmtree(out)
    _copy_tree(ROOT / "plugin", out)
    _copy_tree(ROOT / "core", out / "core")
    (out / "data").mkdir(parents=True, exist_ok=True)
    for fname in RUNTIME_DATA:
        src = ROOT / "data" / fname
        if not src.exists():
            sys.exit("missing runtime data file: %s" % src)
        shutil.copy2(src, out / "data" / fname)
    licence = ROOT / "LICENSE"
    if licence.exists():
        shutil.copy2(licence, out / "LICENSE")

    zip_path = DIST / (NAME + ".zip")
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(out.rglob("*")):
            if path.is_file():
                zf.write(path, (Path(NAME) / path.relative_to(out)).as_posix())
    return out, zip_path


if __name__ == "__main__":
    folder, archive = build()
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
    print("built %s (%d files, %d bytes)" % (archive, len(names), archive.stat().st_size))
    for n in names:
        print("  " + n)
