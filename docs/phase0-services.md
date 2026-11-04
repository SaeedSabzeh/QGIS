# Phase 0: map service check (Milan)

Checked 5 November 2026 from the development machine (Windows, Python 3.11). Every ArcGIS REST endpoint used below returned valid JSON, with no login or token. No PDFs or data files were downloaded: the NTA and zone-card PDFs are listed by URL only.

Test points (lat, lon): Duomo 45.4642, 9.1900; Città Studi 45.4781, 9.2269; Parco Nord 45.5281, 9.2050; Navigli/Darsena 45.4520, 9.1760; Parco Agricolo Sud near Chiaravalle 45.4170, 9.2350.
Positive controls: Lambro (flood) 45.4650, 9.2560, and the Bosco di Vanzago site centroid 45.5197, 8.9736 (the EEA site centroid, from its `POINT_X`/`POINT_Y` attributes). The brief's point for Vanzago, 45.5250, 8.9930, lies about 2 km outside the site and returns nothing.

Re-run: `python scripts/probe_services.py 45.4642 9.1900`

## Summary

| Dataset | Service | CRS | Zone code / constraint field | Verdict |
|---|---|---|---|---|
| PGT zoning (Milan) | `.../arcgis1/rest/services/territorio/tav_previsioni_b/MapServer` | EPSG:32632 | NAF `COD_NUC`; TUC `AMB_URB` + `COD_DEST1`; transformation `AMB_TRAS`; sensitivity `CLASSE` | Go, category level only |
| Natura 2000 | `.../arcgis2/rest/services/ambiente/Rete_Natura_2000/MapServer` (layers 0, 1) | EPSG:32632 | `COD_SITO` (ZSC/SIC), `COD_ZPS` (ZPS) | Go |
| PGRA flood | `.../expo/rest/services/gpt/direttiva_alluvioni_2022/MapServer` (layers 4, 12-15, 17-27) | EPSG:32632 | hazard `Codscenar` (H/M/L) + `Tritorno`; risk `Ris` (R1-R4) | Go, 2022 vintage (see caveats) |

Base host for all three: `https://www.cartografia.servizirl.it` (Regione Lombardia).

## 1. Milan PGT zoning

Service: `https://www.cartografia.servizirl.it/arcgis1/rest/services/territorio/tav_previsioni_b/MapServer` (ArcGIS REST, wkid 32632).
This is the regional mosaic of the PGTs of Lombard municipalities. For Milan it carries the PGT in force: `DATA_BURL` 05/02/2020, and the zone cards are named `015146_20200205_*`.

| ID | Layer | Key fields | Milan values seen |
|---|---|---|---|
| 3 | Fattibilità geologica (group "Componente geologica PGT") | `CLASSE`, `DESCR_FATTIBILITA`, `FATTORI_PERICOLO` | Class II; Class III at Chiaravalle and Lambro |
| 12 | Nuclei di antica formazione (NAF) | `COD_NUC` | 15 |
| 13 | Ambiti di trasformazione | `AMB_TRAS`, `NOME_AMB`, `FUN_PREV1` / `DFUN_PREV1` | 26 "L'Idroscalo (PCU4)"; 29 "Le Abbazie (PCU3)" |
| 14 | Ambiti di rigenerazione urbana e territoriale | `CATEGORIA`, `NOME_AMB` | no hit at the test points |
| 18 | Servizi e impianti | `TIPO_SERV` / `DTIPO_SERV`, `STATO`, `LIV_TER` | 52 "Aree a verde", existing, municipal level (Città Studi only) |
| 19 | Aree agricole | `COD_AGR`, `SPEC_AGR` | no hit at the test points |
| 20 | Ambiti del tessuto urbano consolidato (TUC) | `AMB_URB`, `COD_DEST1` / `DCOD_DEST1`, `SPEC_DEST` | `AMB_URB` 23 (card AU_23); `COD_DEST1` 100 (RESIDENZIALE) |
| 21 | Aree di valore paesaggistico-ambientale ed ecologico | `COD_PAES`, `TIPO_AMB`, `DESCRIZION` | Chiaravalle: 20, `TIPO_AMB` 502 (traditional agrarian landscape) |
| 22 | Classi di sensibilità paesistica | `COD_SEN`, `CLASSE` (1-5), `DESCRIZION` | 2 to 5 |
| 24 | Carta consumo suolo | `CATEGORIA`, `DCATEGORIA` | 1 "Superficie urbanizzata" (Duomo, Parco Nord); 3 "Superficie agricola o naturale" (others) |

Most layers also carry `SCHEDA_NEW`, a link to the zone's PDF card, for example `https://www.cartografia.servizirl.it/schede_pgt/015146/015146_20200205_AU_23.pdf` (not opened).

Results at the test points (layers that returned a feature):

| Point | NAF (12) | TUC (20) | Transformation (13) | Sensitivity (22) | Geology (3) |
|---|---|---|---|---|---|
| Duomo 45.4642, 9.1900 | 15 | 23, residential | none | 5, very high | II |
| Città Studi 45.4781, 9.2269 | none | 23 | none | 4, high | II |
| Parco Nord 45.5281, 9.2050 | none | 23 | none | 2, low | II |
| Navigli/Darsena 45.4520, 9.1760 | 15 | 23 | none | 5, very high | II |
| Parco Agricolo Sud (Chiaravalle) 45.4170, 9.2350 | none | none | 29 "Le Abbazie (PCU3)" | 4, high | III (IIIc+IIId) |
| Lambro 45.4650, 9.2560 | none | none | 26 "L'Idroscalo (PCU4)" | 3, medium | III (IIIa+IIIc) |
| Vanzago 45.5250, 8.9930 (ISTAT 015229, not Milan) | none | 74 (card dated 2013) | none | 2, low | II |

At the four central points the TUC is a single feature (`OBJECTID` 285829), so this layer does not split Milan's consolidated fabric any further there. The NAF feature (`OBJECTID` 291362) is shared by Duomo and Navigli.

Zone code and NTA links:
- The service returns codes, not NTA article numbers. Each code has to be linked to articles by hand in `zone_map.yaml`, as the plan says. I have not read the NTA text, so the article links are not yet checked.
- Level of detail: from this layer the plugin can name the category (NAF, TUC residential, transformation area PCU3 or PCU4, sensitivity class). It cannot name the finer Piano delle Regole zone.
- Vintage: Milan's features date from BURL 05/02/2020. Later variants may not be in the layer. Other municipalities are older (Vanzago's card is dated 2013), so the UI should show the date from `DATA_BURL` or the card name.
- Status: `stato_pgt` layer 1 for ISTAT 015146 gives `FASE` = "Approvazione".

Not usable for the current PGT:
- `territorio/Azzonamenti_comunali` (MISURC, PRG era). Milan rows carry old PRG codes (e.g. `SA-R`, `#SC`) and old article numbers (`ARTICOLO`, e.g. "50,27"). `territorio/storico_misurc` dates Milan's instrument to 1998.
- `gestcom/previsioni`, layer 1 "Zone omogenee per previsione". The service description is "Servizio per ESPCOM, time-dependent". It is not PGT zoning.
- `gpt/pgt_com_art13`: regional plan elements (UNESCO sites, environmental safeguard zones), not municipal zoning.
- Comune di Milano geoportal (`geoportale.comune.milano.it`): the host does not resolve in DNS from here. The Comune's open-data NIL record (CKAN `is_version_of`) names `https://geoportale.comune.milano.it/arcgisportal/rest/services/OperationalLayers/NIL_WM/MapServer/0`, which I could not test. The NIL dataset holds 88 neighbourhood polygons from "Milano 2030 - PGT Approvato", with name and ID only, so no zone code.
- `pgt.comune.milano.it` returns HTTP 403 (Azure Application Gateway) to scripted requests from here. I did not try to get around it.

NTA and PGT documents (URLs only, nothing downloaded):
- Piano delle Regole, Norme di Attuazione, file dated 5 March 2019: `https://www.pgt.comune.milano.it/pgt_file_download/b!88kfkdym6ka1FQJ8CP8l_1ken78aR3NJkcxoQgfR2kK4M-X2Jz8iSJx6ToAzeiZ_/01IBPLUZUUQUVXO3VDTBG3EJNLSCGJO4RK/01PR_Norme_Attuazione_20190305.pdf` (from a search result; not opened). Check whether it is the adopted or the approved text.
- Comune di Milano, PGT approved and in force (Milano 2030): `https://www.comune.milano.it/en/aree-tematiche/rigenerazione-urbana-e-urbanistica/pgt-approvato-e-vigente-milano-2030` (search result; not opened).
- PGT portal: `https://pgt.comune.milano.it/` (403 to scripted requests).
- Regione Lombardia PGTWEB archive: `https://www.regione.lombardia.it/ambiente-e-territorio/pianificazione-territoriale/pianificazione-comunale-e-provinciale/pgtweb-archivio-documentale-pgt`.
- "2024 variante": I could not confirm a 2024 change to the NTA text. Determination DD 1562 of 29 February 2024 (from a search snippet) partially updates the Piano delle Regole and Piano dei Servizi for one area (F2/6/30). Search results also describe a partial normative variant to the Piano delle Regole and Piano dei Servizi, opened in late 2025 (`https://www.assolombarda.it/servizi/immobili-urbanistica-e-territorio/informazioni/pgt-del-comune-di-milano-avviato-il-procedimento-di-parziale-variante-normativa`; `https://www.osborneclarke.com/it/insights/nuova-procedura-di-variante-normativa-al-pgt-del-comune-di-milano`). Its adoption status is unknown.

## 2. Natura 2000 (Regione Lombardia)

Service: `https://www.cartografia.servizirl.it/arcgis2/rest/services/ambiente/Rete_Natura_2000/MapServer` (ArcGIS REST, wkid 32632).

| ID | Layer | Fields |
|---|---|---|
| 0 | ZSC e SIC (Habitats Directive) | `COD_SITO`, `NOME_SITO` |
| 1 | ZPS (Birds Directive) | `COD_ZPS`, `NOME_ZPS` |
| 2 | Habitat Natura 2000 | `COD_HABITA`, `DES_HABITA` |

Constraint field: a polygon hit is the constraint, and the site code is `COD_SITO` or `COD_ZPS`. The rule that applies (valutazione di incidenza) is not in the service; it goes in `constraint_map.yaml`.

Results:

| Point | Layer 0 (ZSC/SIC) | Layer 1 (ZPS) |
|---|---|---|
| Duomo, Città Studi, Parco Nord, Navigli, Chiaravalle, Lambro | none | none |
| Brief's Vanzago point 45.5250, 8.9930 | none (outside the site) | none |
| Bosco di Vanzago centroid 45.5197, 8.9736 | IT2050006 BOSCO DI VANZAGO | IT2050006 Bosco di Vanzago |
| Fontanile Nuovo centroid 45.4626, 9.0073 | IT2050007 FONTANILE NUOVO | IT2050401 Riserva Regionale Fontanile Nuovo |

Layer 2 returns habitat codes at both centroids (3150 and 3260).

Caveats: the service states no data year, and its INSPIRE metadata record could not be read (certificate expired). As expected, no Natura 2000 site covers the test points in central Milan.

Fallback (EEA, Europe-wide): `https://bio.discomap.eea.europa.eu/arcgis/rest/services/ProtectedSites/Natura2000Sites/MapServer` (ArcGIS REST, wkid 102100, dataset version 2024). Layer 0 is Habitats Directive sites, layer 1 Birds Directive (SPA), and layer 2 both. Fields: `SITECODE`, `SITENAME`, `SITETYPE`. Inferred from the regional layers: `SITETYPE` A = SPA only, B = SCI/SAC only, C = both (Bosco di Vanzago is C and appears in both regional layers; Riserva Regionale Fontanile Nuovo is A and appears only in the ZPS layer).

## 3. PGRA flood hazard

Service: `https://www.cartografia.servizirl.it/expo/rest/services/gpt/direttiva_alluvioni_2022/MapServer` (ArcGIS REST, wkid 32632). This is Regione Lombardia's copy of the Po basin PGRA hazard and risk maps, 2022 revision. The Autorità di bacino del Po's own service was not found.

| ID | Layer | Key fields |
|---|---|---|
| 4 | Aree a potenziale rischio significativo (APSFR) | `nameAPSFR`, `relZoneId`, `specHazTyp` |
| 12 to 15 | Rischio R4, R3, R2, R1 | `Ris`, `CatUE`, `Danno`, `NumAbit` (fields as in layer 13) |
| 17 to 20 | Pericolosità H (frequente): RP, RSCM, RSP, ACL | `Codscenar`, `Tritorno`, `Codelidr`, `Nomeelidr`, `NumAbit` (fields as in layer 17) |
| 21 to 24 | Pericolosità M (poco frequente): RP, RSCM, RSP, ACL | same |
| 25 to 27 | Pericolosità L (raro): RP, RSCM, ACL (no RSP layer) | same |

RP = reticolo principale; RSCM = reticolo secondario collinare e montano; RSP = reticolo secondario di pianura; ACL = aree costiere lacuali.

Constraint fields: the hazard class is `Codscenar` (H/M/L) with return period `Tritorno`; the risk class is `Ris` (R1-R4, layers 12-15); the watercourse is `Nomeelidr`; `Datacons` is a date field (20220601 at the Lambro features).

Results:

| Point | Hits |
|---|---|
| Duomo, Città Studi, Parco Nord, Navigli, Chiaravalle | none in layers 4, 12-15, 17-27 |
| Lambro 45.4650, 9.2560 | L4 APSFR "Città di Milano - Reticolo Nord Milano" (relZoneId ITN008); L13 R3 (Danno D2); L17 H, RP, Tritorno 10, NumAbit 5983; L21 M, RP, Tritorno 200, NumAbit 48603; L25 L, RP, Tritorno 500, NumAbit 89469 |
| Niguarda 45.5100, 9.1850; Seveso-Bresso 45.5300, 9.1700; Idroscalo 45.4650, 9.2850 | none |

Caveats:
- The 2022 layers may not be the latest. The same server has `gpt/Varianti_PAI_PGRA_in_corso` (it also has a "PGRA Vigente" group, layers 38-50), with a 2025 revision of the hazard maps ("Revisione mappe 2025 DSG 4/2026") and a variant ("Variante PAI-PGRA Mera DSG 27/2026"), both marked as in progress. Confirm which set is in force before the plugin cites it.
- Other versions in the same folder, not used: `direttiva_alluvioni` (2013), `_2015`, `_2019`, `_2020` and `_2023`. `_2023` has the same 28-layer layout as `_2022` and no service description; its values were not compared.
- "No hit" is the normal result across central Milan. A Niguarda hit reported in an earlier draft was not reproduced.
- Each hazard scenario and water network is a separate layer, so the plugin has to query all of 4, 12-15 and 17-27.

Extra constraints on the same server: `vincolometro/studi_geologici_comunali_vincol` layer 13 "Mosaico della fattibilità" (`CLASSE_FATTIBILITA`, `ISTAT_COMUNE` 015146) gives CLASSE 2 at the four central points and CLASSE 3 at Chiaravalle and Lambro, matching layer 3 of `tav_previsioni_b`. Its layer 17 holds local seismic hazard (`SIGLE_SCENARIO`, for example Z4a at Duomo and Z2b at Città Studi).

## 4. Earlier drafts

This note replaces two earlier drafts, which have been deleted. One said no-go for PGT because it never searched `/arcgis1/rest/services/territorio`, where `tav_previsioni_b` lives. It also reported a PGRA hit at Niguarda (45.5100, 9.1850) that could not be reproduced. The Comune geoportal URL it named (`.../PGT/PGT_Milano2030_VIGENTE_R10/MapServer`) is still untested, because the host does not resolve.

## 5. Probe script

`scripts/probe_services.py` now has 27 layer URLs in `SERVICES`: 9 PGT (layers 3, 12, 13, 14, 18, 19, 20, 21, 22), 2 Natura 2000 (layers 0, 1) and 16 PGRA (layers 4, 12-15, 17-27). The per-layer keys (`pgt_*`, `natura2000_*`, `pgra_*`) were already in the committed script (commit 1f9b0d4); this session added the missing layers, which are not committed. The keys are per layer, not the three names in the brief.

Run for the Duomo point: 27 layers queried, 4 returned a feature (`pgt_naf`, `pgt_previsioni_tuc`, `pgt_sensibilita`, `pgt_fattibilita_geo`), 23 returned none, and there were 0 errors. `python -m pytest -q`: 1 passed. Nothing committed.

## Not checked

- Rate limits: no throttling or errors across several hundred queries this session. The regional layers report `maxRecordCount` 1000; the EEA layer reports 1,000,000. No token is needed.
- The Comune di Milano's own services (host does not resolve here), the INSPIRE records (expired certificate), the Autorità di bacino del Po's services, and the NTA text itself (not downloaded).
- QGIS LTR installation (a Phase 0 checklist item) was not part of this task. ruff is not installed here, so lint was not run.

## Go/no-go

**Go/no-go (PGT service): GO, at category level.** The regional `tav_previsioni_b` service returns zone codes (NAF `COD_NUC`, TUC `AMB_URB` with `COD_DEST1`, transformation areas `AMB_TRAS`) that can be linked to NTA articles through `zone_map.yaml`; the article links still need checking against the NTA text. It does not return the finer Piano delle Regole zones, so v1 should name the category, not the exact zone.
