"""Compare the municipal and regional source layers at the release controls."""

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from run_eval import load_points  # noqa: E402

from core import scope, services  # noqa: E402

CONTROLS = (
    ("north-east", 45.52937179, 9.21261924),
    ("north-west", 45.521842, 9.18490991),
    ("duomo-building", 45.46414, 9.19192),
    ("vanzago", 45.5197, 8.9736),
)
COMPARED_LAYERS = (
    *services.MUNICIPAL_ZONES, "milano_park_north", "milano_park_south",
    "milano_geology", "pgt_fattibilita_geo", "pgt_naf", "parchi_regionali",
    "pgra_H_RP", "pgra_M_RP", "pgra_L_RP", "pgra_R3", "natura2000_zsc", "natura2000_zps",
)


def run():
    points = [(p["id"], p["lat"], p["lon"]) for p in load_points()] + list(CONTROLS)
    layers = {name: services.SERVICES[name] for name in COMPARED_LAYERS}
    layers["milano_flood"] = layers["milano_geology"].replace("G17/MapServer/1", "G15/MapServer/19")

    def probe(point):
        key, lat, lon = point
        result = services.query_all(lat, lon, services=layers)
        if result["errors"]:
            failed = {name: layers[name] for name in result["errors"]}
            retry = services.query_all(lat, lon, services=failed)
            result["layers"].update(retry["layers"])
            result["errors"] = retry["errors"]
        if result["errors"]:
            raise RuntimeError(f"{key}: {result['errors']}")
        return key, (scope.contains(lat, lon), result["layers"])

    with ThreadPoolExecutor(max_workers=3) as pool:
        found = dict(pool.map(probe, points))

    geology_agreement = 0
    for key, (inside, hits) in found.items():
        city = {a["legenda"].split(" - ")[0] for a in hits["milano_geology"]}
        region = {str(a["CLASSE"]) for a in hits["pgt_fattibilita_geo"]}
        if inside:
            assert city and {int(code) for code in region} == {{"I": 1, "II": 2, "III": 3, "IV": 4}[code] for code in city}, key
            geology_agreement += 1
        category = "/".join(layer.removeprefix("milano_") for layer in services.MUNICIPAL_ZONES if hits[layer])
        parks = "/".join(park for park in ("north", "south") if hits["milano_park_" + park])
        print(f"{key:<15} {'Milan' if inside else 'outside':<7} {category or '-':<8} "
              f"{'/'.join(sorted(city)) or '-':<4} {parks or '-'}")

    assert found["p03"][1]["milano_adr"] and not found["p03"][1]["milano_park_north"]
    assert found["p19"][1]["milano_aru"]
    assert not found["p01"][1]["milano_naf"] and found["duomo-building"][1]["milano_naf"]
    for key in ("north-east", "north-west"):
        inside, hits = found[key]
        assert inside and hits["milano_park_north"]
        assert any(row["NOME_PA"] == "Parco Nord Milano" for row in hits["parchi_regionali"])
    assert "Art. 26" in found["p05"][1]["milano_park_south"][0]["nome"]
    lambro = found["p06"][1]
    city_flood = {(a["scenario"][0], a["tritorno"]) for a in lambro["milano_flood"]}
    regional_flood = {(a["Codscenar"], a["Tritorno"]) for s in "HML" for a in lambro[f"pgra_{s}_RP"]}
    assert city_flood == regional_flood == {("H", 10), ("M", 200), ("L", 500)}
    assert not found["p10"][0] and not found["vanzago"][0]
    assert found["vanzago"][1]["natura2000_zsc"] and found["vanzago"][1]["natura2000_zps"]
    print(f"All {geology_agreement} in-city geology controls agree at the main-class level.")


if __name__ == "__main__":
    run()
