"""Phase 0: query each map service at a test point and print what comes back.

Usage: python scripts/probe_services.py <lat> <lon>
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.services import query_point  # noqa: E402

# Verified live layer URLs (see docs/phase0-services.md). All services are EPSG:32632;
# query_point sends lon/lat (inSR=4326) and the server reprojects.
_PGT = "https://www.cartografia.servizirl.it/arcgis1/rest/services/territorio/tav_previsioni_b/MapServer"
_N2K = "https://www.cartografia.servizirl.it/arcgis2/rest/services/ambiente/Rete_Natura_2000/MapServer"
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
