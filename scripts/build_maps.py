"""Convert data/zone_map.yaml and data/constraint_map.yaml to JSON for the stdlib-only runtime.

Usage: python scripts/build_maps.py          (needs PyYAML; dev-time only)
The JSON files are committed next to the YAML, which stays the source of truth.
"""

import json
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
NAMES = ("zone_map", "constraint_map")


def convert(name: str) -> dict:
    import yaml

    with open(DATA / f"{name}.yaml", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def main() -> None:
    for name in NAMES:
        out = DATA / f"{name}.json"
        with open(out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(convert(name), fh, ensure_ascii=False, indent=2, sort_keys=False)
            fh.write("\n")
        print(f"wrote {out}")


if __name__ == "__main__":
    sys.exit(main())
