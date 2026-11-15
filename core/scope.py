"""Municipal coverage for the Milan-only plan corpus."""

import json
from functools import lru_cache
from pathlib import Path

BOUNDARY = Path(__file__).resolve().parents[1] / "data" / "milano-confine.json"
OUTSIDE = "This point is outside the Comune di Milano. Choose a point within Milan."
UNAVAILABLE = "The Milan boundary could not be loaded. Reinstall the plugin ZIP."


@lru_cache(maxsize=1)
def _boundary(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    try:
        geometry = data["geometry"]
        ring, = geometry["coordinates"]
        if geometry["type"] != "Polygon" or len(ring) < 4 or ring[0] != ring[-1]:
            raise ValueError("Invalid Milan boundary")
        if not all(type(x) in (int, float) and -180 <= x <= 180
                   and type(y) in (int, float) and -90 <= y <= 90 for x, y in ring):
            raise ValueError("Invalid Milan boundary coordinates")
        xs, ys = zip(*ring)
        bounds = min(xs), min(ys), max(xs), max(ys)
    except (KeyError, TypeError) as error:
        raise ValueError("Invalid Milan boundary") from error
    return ring, bounds


def contains(lat, lon):
    """Test the closed DS2841 exterior ring in the source's WGS 84 coordinates."""
    ring, (left, bottom, right, top) = _boundary(BOUNDARY)
    if not (left <= lon <= right and bottom <= lat <= top):
        return False
    inside = False
    previous = ring[-1]
    for current in ring:
        x1, y1 = previous
        x2, y2 = current
        previous = current
        if not min(y1, y2) <= lat <= max(y1, y2):
            continue
        if min(x1, x2) <= lon <= max(x1, x2):
            cross = (x2 - x1) * (lat - y1) - (y2 - y1) * (lon - x1)
            if abs(cross) <= 1e-16:
                return True
        if (y1 > lat) != (y2 > lat) and lon < x1 + (lat - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside
