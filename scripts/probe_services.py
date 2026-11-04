"""Phase 0: query each map service at a test point and print what comes back.

Usage: python scripts/probe_services.py <lat> <lon>
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.services import query_point  # noqa: E402

# TODO: fill in the real layer URLs found during Phase 0.
SERVICES = {
    # "pgt_previsioni": "https://.../MapServer/0",
    # "natura2000": "https://.../MapServer/0",
    # "pgra": "https://.../MapServer/0",
}


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    lat, lon = float(sys.argv[1]), float(sys.argv[2])
    if not SERVICES:
        sys.exit("No services configured yet: edit SERVICES in this script.")
    for name, url in SERVICES.items():
        print(f"== {name}")
        print(json.dumps(query_point(url, lon, lat), indent=2, ensure_ascii=False)[:3000])


if __name__ == "__main__":
    main()
