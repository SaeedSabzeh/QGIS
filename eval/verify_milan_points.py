"""Compare the municipal and regional source layers at the release controls."""

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from run_eval import load_points  # noqa: E402

from core import retrieval, scope, services  # noqa: E402

CONTROLS = (
    ("north-east", 45.52937179, 9.21261924),
    ("north-west", 45.521842, 9.18490991),
    ("duomo-building", 45.46414, 9.19192),
    ("vanzago", 45.5197, 8.9736),
    ("porta-nuova", 45.4836, 9.1900),
    ("bovisa", 45.5040, 9.1560),
    ("parco-lambro", 45.4960, 9.2480),
    ("darsena", 45.4520, 9.1760),
    ("linate", 45.4600, 9.2600),
)
COMPARED_LAYERS = (
    *services.MUNICIPAL_ZONES, "milano_park_north", "milano_park_south",
    "milano_geology", "pgt_fattibilita_geo", "pgt_naf", "parchi_regionali",
    "pgra_H_RP", "pgra_M_RP", "pgra_L_RP", "pgra_R3", "natura2000_zsc", "natura2000_zps",
    "milano_accessibility", "milano_in_itinere", "milano_gfu", "milano_plis_lambro",
    "milano_navigli_136",
)
IDENTIFIED = ("milano_r03", "milano_r06", "milano_r07")


def check_layer_names():
    """Every identify layer with its own rule still has the expected name on the service."""
    zone_map, _ = retrieval.load_maps()
    for name, entry in zone_map["identify"].items():
        published = {str(row["id"]): row["name"].strip()
                     for row in services.fetch_json(services.IDENTIFY[name] + "/layers?f=json")["layers"]}
        for layer_id, rule in (entry.get("layers") or {}).items():
            expected = rule.get("name")
            assert expected, f"{name} layer {layer_id} has no expected name"
            assert published.get(layer_id, "").casefold().startswith(expected.casefold()), (
                name, layer_id, published.get(layer_id), expected)
    print("Identify layer names match the service.")


def run():
    check_layer_names()
    points = [(p["id"], p["lat"], p["lon"]) for p in load_points()] + list(CONTROLS)
    layers = {name: services.SERVICES[name] for name in COMPARED_LAYERS}
    layers["milano_flood"] = layers["milano_geology"].replace("G17/MapServer/1", "G15/MapServer/19")

    def probe(point):
        key, lat, lon = point
        identify = {name: services.IDENTIFY[name] for name in IDENTIFIED}
        result = services.query_all(lat, lon, services=layers, identify=identify)
        if result["errors"]:
            failed = {name: layers[name] for name in result["errors"] if name in layers}
            again = {name: identify[name] for name in result["errors"] if name in identify}
            retry = services.query_all(lat, lon, services=failed, identify=again)
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
    assert found["porta-nuova"][1]["milano_accessibility"] and found["porta-nuova"][1]["milano_in_itinere"]
    assert found["bovisa"][1]["milano_gfu"]
    assert found["parco-lambro"][1]["milano_plis_lambro"]
    assert found["darsena"][1]["milano_navigli_136"]
    names = lambda key, m: {h["_layerName"] for h in found[key][1].get(m, [])}  # noqa: E731
    assert "Ex Monumentali" in names("duomo-building", "milano_r06")
    assert any(n.startswith("Interventi di manutenzione") for n in names("duomo-building", "milano_r03"))
    assert "Ambito aeroportuale" in names("linate", "milano_r07")
    print(f"All {geology_agreement} in-city geology controls agree at the main-class level.")


if __name__ == "__main__":
    run()
