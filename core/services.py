"""Point queries to the ArcGIS REST map services (PGT, Natura 2000, PGRA).

Standard library only. The network call is injectable (`fetch`) so the QGIS shell can swap in
QgsNetworkAccessManager later.
"""

import json
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

# Verified live layer URLs (see docs/phase0-services.md). All services are EPSG:32632;
# the query sends lon/lat (inSR=4326) and the server reprojects.
_PGT = "https://www.cartografia.servizirl.it/arcgis1/rest/services/territorio/tav_previsioni_b/MapServer"
_N2K = "https://www.cartografia.servizirl.it/arcgis2/rest/services/ambiente/Rete_Natura_2000/MapServer"
_AREE_PROTETTE = "https://www.cartografia.servizirl.it/arcgis2/rest/services/ambiente/AreeProtette/MapServer"
_PGRA = "https://www.cartografia.servizirl.it/expo/rest/services/gpt/direttiva_alluvioni_2022/MapServer"

SERVICES = {
    # Regional mosaic of the current PGT (Milano 2030, BURL 05/02/2020): categories only.
    "pgt_naf": f"{_PGT}/12",  # nuclei di antica formazione (COD_NUC)
    "pgt_at": f"{_PGT}/13",  # ambiti di trasformazione (AMB_TRAS, NOME_AMB)
    "pgt_servizi": f"{_PGT}/18",  # servizi e impianti (DTIPO_SERV, DSTATO)
    "pgt_previsioni_tuc": f"{_PGT}/20",  # tessuto urbano consolidato (AMB_URB; all Milan = 23)
    "pgt_paesaggio": f"{_PGT}/21",  # aree di valore paesaggistico-ambientale (TIPO_AMB)
    "pgt_sensibilita": f"{_PGT}/22",  # classi di sensibilita paesistica (CLASSE 1-5)
    "pgt_rigenerazione": f"{_PGT}/14",  # ambiti di rigenerazione (no hit at the test points)
    "pgt_agricole": f"{_PGT}/19",  # aree agricole (no hit at the test points)
    "pgt_fattibilita_geo": f"{_PGT}/3",  # fattibilita geologica (CLASSE, FATTORI_PERICOLO)
    "natura2000_zsc": f"{_N2K}/0",  # ZSC/SIC (COD_SITO, NOME_SITO)
    "natura2000_zps": f"{_N2K}/1",  # ZPS (COD_ZPS, NOME_ZPS)
    # Regional parks (NOME_PA, NOME_ENTE, DATTUA_PA; wkid 32632). Known gap: Parco Nord Milano is
    # NOT in this layer (no hit even at its centre); Parco Agricolo Sud Milano is.
    "parchi_regionali": f"{_AREE_PROTETTE}/9",
    # PGRA risk classes R4-R1 (field Ris) and the APSFR areas they belong to.
    "pgra_APSFR": f"{_PGRA}/4",  # aree a potenziale rischio significativo (nameAPSFR)
    "pgra_R4": f"{_PGRA}/12",
    "pgra_R3": f"{_PGRA}/13",
    "pgra_R2": f"{_PGRA}/14",
    "pgra_R1": f"{_PGRA}/15",
    # PGRA hazard, 2022 revision: scenario H (frequent), M (poco frequente), L (raro).
    # RP = reticolo principale, RSCM = sec. collinare/montano, RSP = sec. pianura, ACL = coste lacuali.
    "pgra_H_RP": f"{_PGRA}/17",
    "pgra_H_RSCM": f"{_PGRA}/18",
    "pgra_H_RSP": f"{_PGRA}/19",
    "pgra_H_ACL": f"{_PGRA}/20",
    "pgra_M_RP": f"{_PGRA}/21",
    "pgra_M_RSCM": f"{_PGRA}/22",
    "pgra_M_RSP": f"{_PGRA}/23",
    "pgra_M_ACL": f"{_PGRA}/24",
    "pgra_L_RP": f"{_PGRA}/25",
    "pgra_L_RSCM": f"{_PGRA}/26",
    "pgra_L_ACL": f"{_PGRA}/27",
}

DEFAULT_TIMEOUT = 20


def build_query_url(layer_url: str, x: float, y: float, wkid: int = 4326) -> str:
    """Return the full `/query` URL for a point intersect on `layer_url`."""
    params = {
        "geometry": f"{x},{y}",
        "geometryType": "esriGeometryPoint",
        "inSR": str(wkid),
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "returnGeometry": "false",
        "f": "json",
    }
    return f"{layer_url.rstrip('/')}/query?{urllib.parse.urlencode(params)}"


def fetch_json(url: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Default fetch function: GET `url` and decode the JSON body."""
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.load(resp)


def query_point(layer_url: str, x: float, y: float, wkid: int = 4326, timeout: int = 20) -> dict:
    """Return the features of `layer_url` that intersect the point (x, y).

    `layer_url` is a full `.../MapServer/{layer}` URL. Coordinates are lon/lat by default.
    """
    return fetch_json(build_query_url(layer_url, x, y, wkid), timeout=timeout)


def query_all(lat, lon, timeout=DEFAULT_TIMEOUT, fetch=None, services=None, max_workers=8):
    """Query every registered layer at (lat, lon).

    `fetch(url, timeout) -> dict` is injectable (default: urllib). Never raises for a single
    failing layer. Returns::

        {"point": {"lat": .., "lon": ..},
         "layers": {name: [attribute dict, ...]},   # every layer, [] when no hit
         "errors": {name: "message"}}               # only layers that failed
    """
    fetch = fetch or fetch_json
    services = SERVICES if services is None else services

    def one(item):
        name, layer_url = item
        try:
            data = fetch(build_query_url(layer_url, lon, lat), timeout)
            if not isinstance(data, dict):
                raise ValueError("unexpected response")
            if "error" in data:
                err = data["error"]
                msg = err.get("message", err) if isinstance(err, dict) else err
                raise ValueError(f"service error: {msg}")
            feats = data.get("features") or []
            return name, [dict(f.get("attributes") or {}) for f in feats], None
        except Exception as exc:  # one bad layer must not break the others
            return name, [], f"{type(exc).__name__}: {exc}"

    layers, errors = {}, {}
    items = list(services.items())
    if items:
        with ThreadPoolExecutor(max_workers=min(max_workers, len(items))) as pool:
            results = list(pool.map(one, items))
        for name, attrs, err in results:  # keep registry order
            layers[name] = attrs
            if err:
                errors[name] = err
    return {"point": {"lat": lat, "lon": lon}, "layers": layers, "errors": errors}
