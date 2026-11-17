"""Point queries to the ArcGIS REST map services (PGT, Natura 2000, PGRA).

Standard library only. The network call is injectable (`fetch`) so the QGIS shell can swap in
QgsNetworkAccessManager later.
"""

import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FuturesTimeout

from . import scope, urlcheck

# Verified live layer URLs (see docs/phase0-services.md). All services are EPSG:32632;
# the query sends lon/lat (inSR=4326) and the server reprojects.
_PGT = "https://www.cartografia.servizirl.it/arcgis1/rest/services/territorio/tav_previsioni_b/MapServer"
_N2K = "https://www.cartografia.servizirl.it/arcgis2/rest/services/ambiente/Rete_Natura_2000/MapServer"
_AREE_PROTETTE = "https://www.cartografia.servizirl.it/arcgis2/rest/services/ambiente/AreeProtette/MapServer"
_PGRA = "https://www.cartografia.servizirl.it/expo/rest/services/gpt/direttiva_alluvioni_2022/MapServer"
_MILANO = "https://gisportal.comune.milano.it/federated/rest/services/PGT/Milano_2030_PGT_Vigente_Tavola_"
_R02 = f"{_MILANO}R02/MapServer"
MUNICIPAL_ZONES = ("milano_naf", "milano_adr", "milano_aru")

SERVICES = {
    "milano_naf": f"{_R02}/38",
    "milano_adr": f"{_R02}/39",
    "milano_aru": f"{_R02}/40",
    "milano_park_north": f"{_R02}/15",
    "milano_park_south": f"{_R02}/17",
    "milano_geology": f"{_MILANO}G17/MapServer/1",
    # Further Tav. R.02 layers (Milano 2030), each mapped in zone_map.yaml.
    "milano_accessibility": f"{_R02}/0",
    "milano_rigen_ambientale": f"{_R02}/2",
    "milano_piazze": f"{_R02}/3",
    "milano_nodi": f"{_R02}/4",
    "milano_nuclei_esterni": f"{_R02}/5",
    "milano_gfu": f"{_R02}/6",
    "milano_pedonale": f"{_R02}/7",
    "milano_in_itinere": f"{_R02}/10",
    "milano_pa_obbligatori": f"{_R02}/12",
    "milano_agricoltura": f"{_R02}/13",
    "milano_ticinello": f"{_R02}/16",
    "milano_plis_lambro": f"{_R02}/19",
    "milano_plis_martesana": f"{_R02}/20",
    "milano_ers": f"{_R02}/21",
    "milano_navigli_136": f"{_R02}/22",
    "milano_navigli_riapertura": f"{_R02}/24",
    "milano_mobilita_nuova": f"{_R02}/27",
    "milano_verde": f"{_R02}/36",
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
    # Regional parks (NOME_PA, NOME_ENTE, DATTUA_PA), also a fallback for Milan's R02.
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

# Whole Comune maps queried with one "identify" request each (every layer at the point).
IDENTIFY = {
    "milano_r03": f"{_MILANO}R03/MapServer",
    "milano_r05": f"{_MILANO}R05/MapServer",
    "milano_r06": f"{_MILANO}R06/MapServer",
    "milano_r07": f"{_MILANO}R07/MapServer",
    "milano_r08": f"{_MILANO}R08/MapServer",
}
CLICK_DEADLINE = 30  # seconds for all layers of one click


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
    urlcheck.check_url(url)  # https only (or http to localhost)
    with urllib.request.urlopen(url, timeout=timeout) as resp:  # nosec B310
        return json.load(resp)


def query_point(layer_url: str, x: float, y: float, wkid: int = 4326, timeout: int = 20) -> dict:
    """Return the features of `layer_url` that intersect the point (x, y).

    `layer_url` is a full `.../MapServer/{layer}` URL. Coordinates are lon/lat by default.
    """
    return fetch_json(build_query_url(layer_url, x, y, wkid), timeout=timeout)


def build_identify_url(map_url: str, x: float, y: float) -> str:
    """ArcGIS identify on every layer of `map_url` at the lon/lat point (x, y)."""
    params = {
        "geometry": f"{x},{y}",
        "geometryType": "esriGeometryPoint",
        "sr": "4326",
        "layers": "all",
        "tolerance": "0",
        "mapExtent": f"{x - 0.01},{y - 0.01},{x + 0.01},{y + 0.01}",
        "imageDisplay": "400,400,96",
        "returnGeometry": "false",
        "f": "json",
    }
    return f"{map_url.rstrip('/')}/identify?{urllib.parse.urlencode(params)}"


def _transient(exc):
    """Worth one retry: network trouble or a flagged transient HTTP status. Never cancellation,
    a client error (4xx), a bad reply or a programming error."""
    if "cancel" in type(exc).__name__.lower() or "cancel" in str(exc).lower():
        return False
    flag = getattr(exc, "transient", None)
    if flag is not None:
        return bool(flag)
    code = getattr(exc, "code", None)
    if isinstance(code, int):
        return code in (408, 429) or code >= 500
    return isinstance(exc, (OSError, TimeoutError))


def query_all(lat, lon, timeout=DEFAULT_TIMEOUT, fetch=None, services=None, max_workers=64,
              deadline=CLICK_DEADLINE, identify=None):
    """Query every registered layer at (lat, lon).

    `fetch(url, timeout) -> dict` is injectable (default: urllib). Never raises for a single
    failing layer. Returns::

        {"point": {"lat": .., "lon": ..},
         "layers": {name: [attribute dict, ...]},   # every layer, [] when no hit
         "errors": {name: "message"}}               # only layers that failed

    A layer that fails with a transient error is tried once more. Layers that have not
    answered when `deadline` seconds have passed are reported as errors, so one hung host
    cannot hold the click.
    """
    fetch = fetch or fetch_json
    if identify is None:
        identify = IDENTIFY if services is None else {}
    services = SERVICES if services is None else services
    timeout = min(timeout, max(5, deadline // 2))
    started = time.monotonic()
    retried = []

    def remaining():
        return deadline - (time.monotonic() - started)

    def get(name, url):
        # Each request is capped to the time left, so no worker outlives the click by much.
        left = remaining()
        if left <= 0.2:
            raise TimeoutError("no time left within the %g s deadline" % deadline)
        try:
            return fetch(url, min(timeout, left))
        except Exception as exc:
            if not _transient(exc) or remaining() < deadline / 2:
                raise
            retried.append(name)
            time.sleep(0.5)
            left = remaining()
            if left <= 0.2:
                raise
            return fetch(url, min(timeout, left))

    def one_identify(name, map_url):
        try:
            data = get(name, build_identify_url(map_url, lon, lat))
            if not isinstance(data, dict) or "error" in data or not isinstance(
                    data.get("results", []), list):
                raise ValueError("unexpected identify response")
            hits = []
            for r in data.get("results", []):
                if isinstance(r, dict) and isinstance(r.get("attributes"), dict):
                    hits.append(dict(r["attributes"], _layerId=r.get("layerId"),
                                     _layerName=str(r.get("layerName", "")).strip()))
            return name, hits, None
        except Exception as exc:
            return name, [], f"{type(exc).__name__}: {exc}"

    def one(item):
        name, layer_url = item
        if name in identify:
            return one_identify(name, layer_url)
        try:
            data = get(name, build_query_url(layer_url, lon, lat))
            if not isinstance(data, dict):
                raise ValueError("unexpected response")
            if "error" in data:
                err = data["error"]
                msg = err.get("message", err) if isinstance(err, dict) else err
                raise ValueError(f"service error: {msg}")
            feats = data.get("features")
            if data.get("exceededTransferLimit") or not isinstance(feats, list) or any(
                not isinstance(f, dict) or not isinstance(f.get("attributes"), dict) for f in feats
            ):
                raise ValueError("unexpected feature response")
            return name, [f["attributes"] for f in feats], None
        except Exception as exc:  # one bad layer must not break the others
            return name, [], f"{type(exc).__name__}: {exc}"

    layers, errors = {}, {}
    items = list(services.items()) + list(identify.items())
    if items:
        done = {}
        # one worker per request (they only wait on the network), so a hanging host cannot
        # keep the other hosts' layers queued until the deadline
        pool = ThreadPoolExecutor(max_workers=min(max_workers, len(items)))
        futures = {pool.submit(one, item): item[0] for item in items}
        try:
            for future in as_completed(futures, timeout=deadline):
                name, attrs, err = future.result()
                done[name] = (attrs, err)
        except FuturesTimeout:
            pass
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
        for name, _url in items:  # keep registry order
            attrs, err = done.get(name, ([], "TimeoutError: no answer within %d s" % deadline))
            layers[name] = attrs
            if err:
                errors[name] = err
    return {"point": {"lat": lat, "lon": lon}, "layers": layers, "errors": errors,
            "retried": sorted(set(retried))}


def query_milan(lat, lon, fetch=None):
    """Query at a covered point. Exterior clicks stay on the local machine."""
    try:
        inside = scope.contains(lat, lon)
    except (OSError, ValueError):
        status, note = "unavailable", scope.UNAVAILABLE
    else:
        if inside:
            return query_all(lat, lon, fetch=fetch)
        status, note = "outside", scope.OUTSIDE
    return {"point": {"lat": lat, "lon": lon}, "layers": {}, "errors": {},
            "scope_status": status, "scope_note": note}
