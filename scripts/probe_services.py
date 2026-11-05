"""Phase 0: query each map service at a test point and print what comes back.

Usage: python scripts/probe_services.py <lat> <lon>
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.services import SERVICES, query_point  # noqa: E402


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    lat, lon = float(sys.argv[1]), float(sys.argv[2])
    if not SERVICES:
        sys.exit("No services configured yet: edit SERVICES in this script.")
    for name, url in SERVICES.items():
        print(f"== {name}")
        try:
            feats = query_point(url, lon, lat).get("features", [])
        except Exception as exc:  # network/HTTP errors should not stop the probe
            print(f"  ERROR: {exc}")
            continue
        if not feats:
            print("  (no feature)")
        for feat in feats:
            print(json.dumps(feat.get("attributes", {}), indent=2, ensure_ascii=False)[:1500])


if __name__ == "__main__":
    main()
