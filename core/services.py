"""Point queries to the ArcGIS REST map services (PGT, Natura 2000, PGRA)."""

import json
import urllib.parse
import urllib.request


def query_point(layer_url: str, x: float, y: float, wkid: int = 4326, timeout: int = 20) -> dict:
    """Return the features of `layer_url` that intersect the point (x, y).

    `layer_url` is a full `.../MapServer/{layer}` URL. Coordinates are lon/lat by default.
    """
    params = {
        "geometry": f"{x},{y}",
        "geometryType": "esriGeometryPoint",
        "inSR": str(wkid),
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "returnGeometry": "false",
        "f": "json",
    }
    url = f"{layer_url.rstrip('/')}/query?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.load(resp)
