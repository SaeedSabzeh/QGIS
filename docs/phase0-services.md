# Phase 0: verified data sources

Checked 5 November 2026 from a Windows machine with `curl` and `core.services.query_point(layer_url, lon, lat)`. Only things that returned valid data are listed as working. All three live services are on `https://www.cartografia.servizirl.it` (Regione Lombardia), in EPSG:32632. `query_point` sends lon/lat with `inSR=4326` and the server reprojects. The same URLs are in `SERVICES` in `scripts/probe_services.py`.

Test points (lat, lon): Duomo 45.4642, 9.1900; Citta Studi 45.4781, 9.2269; Parco Nord 45.5281, 9.2050; Darsena 45.4520, 9.1760; Chiaravalle 45.4170, 9.2350.

## 1. Milan PGT zoning

### Chosen source: `tav_previsioni_b` (Regione Lombardia, "PGT - Tavola delle Previsioni di Piano")

`https://www.cartografia.servizirl.it/arcgis1/rest/services/territorio/tav_previsioni_b/MapServer/{id}` (ArcGIS 10.91). WMS twin: `https://www.cartografia.servizirl.it/arcgis1/services/territorio/tav_previsioni_b/MapServer/WMSServer?`. The catalogue record is `r_lombar:a964bb90-d3b8-4e23-95d6-f7925c38e164` (RNDT/geodati.gov.it, metadata date 2026-10-26, licence CC BY 4.0, no access limitations). It is the regional mosaic of the Tavola delle previsioni that each Comune uploads. For Milan it holds PGT Milano 2030 (in force from BURL 05/02/2020; the `SCHEDA_NEW` links carry the date 20200205).

Why this and not something finer: the Comune di Milano's own service could not be reached (see "Not reached" below), so this is the most accurate source that is actually reachable. It is the Comune's own current PGT, delivered by the Comune to the Region, but only at **category level**.

Layers used:

| ID | Layer | Key fields |
|---|---|---|
| 12 | Nuclei di antica formazione (NAF) | `COD_NUC` (Milan = 15) |
| 13 | Ambiti di trasformazione (AT) | `AMB_TRAS`, `NOME_AMB`, `DFUN_PREV1`, `SCHEDA_NEW` |
| 14 | Ambiti di rigenerazione | no hit at the test points |
| 18 | Servizi e impianti | `DTIPO_SERV`, `DLIV_TER`, `DSTATO`, `LEGENDA` |
| 20 | Tessuto urbano consolidato (TUC) | `AMB_URB`, `DCOD_DEST1`, `DSPEC_DEST`, `SCHEDA_NEW` |
| 21 | Aree di valore paesaggistico-ambientale | `TIPO_AMB`, `DESCRIZION`, `NOTE` |
| 22 | Classi di sensibilita paesistica | `CLASSE` (1-5), `DESCRIZION`, `SCHEDA` |
| 24 | Carta del consumo di suolo | `DCATEGORIA`, `DFONTE_AGR` |

Also present, not yet used: 1-3 geological component, 5-10 ecological network, 11 modalita attuative (`COD_MOD`, `NOMEAMB`, `DMOD_INT`), 27-33 buffer zones (roads, railways, cemeteries, wells).

**Zone-code field:** there is no single one. Use the layer that hits plus its code: NAF `COD_NUC`, AT `AMB_TRAS`/`NOME_AMB`, TUC `AMB_URB` (always 23 in Milan), services `DTIPO_SERV`, landscape `TIPO_AMB`, sensitivity `CLASSE`. **There is no NTA article field** in this service. The mapping to NTA articles must come from the hand-written `zone_map.yaml`, keyed on layer and category.

Results at the test points (layers 11-14, 18-22 and 24 queried; layers not listed returned nothing):

| Point | Hits |
|---|---|
| Duomo | L12 NAF (`COD_NUC` 15); L20 TUC 23, `DCOD_DEST1` RESIDENZIALE, `DSPEC_DEST` Commerciale; L22 class 5 (molto elevata); L24 "Superficie urbanizzata" |
| Citta Studi | L18 service "AREE A VERDE", existing, municipal level; L20 TUC 23; L22 class 4; L24 agricultural/natural, "Area verde - parchi urbani" |
| Parco Nord | L20 TUC 23; L22 class 2 (bassa); L24 "Superficie urbanizzata" |
| Darsena | L12 NAF 15; L20 TUC 23; L22 class 5; L24 "Specchi e corsi d'acqua" |
| Chiaravalle | L13 AT 29 "Le Abbazie (PCU3)", `DFUN_PREV1` RESIDENZIALE; L21 `TIPO_AMB` 502 (paesaggio agrario tradizionale, "Ambiti agricoli di rilevanza paesistica"); L22 class 4; L24 "Aree naturali o seminaturali" |

Caveats:
- All of Milan's consolidated urban fabric is **one polygon** (`AMB_URB` = 23, `DCOD_DEST1` always RESIDENZIALE). The finer Piano delle Regole zones (ADR, ARU, individual tessuti, per-parcel indices) are not in this service. Parco Nord is reported as TUC, which is true of the mosaic but not informative.
- `DSPEC_DEST` ("Commerciale") is a specification of the use, not a zone.
- At Duomo and Darsena, NAF hits, so v1 can cite NAF-related articles there; everything else is category-level.
- Detailed Piano delle Regole zoning with NTA references would need the Comune's own data (below).

### Download alternative (not used)
The same data is offered as shapefile packages per province at `https://www.geoportale.regione.lombardia.it/download-pacchetti` (metadata id `r_lombar:a964bb90-d3b8-4e23-95d6-f7925c38e164`). I saw BERGAMO 300 MB, BRESCIA 341 MB, COMO 127 MB, CREMONA 58 MB and LECCO 88 MB on page 1; the Milan package is on a later page of a JavaScript form and was not fetched. It is the same layers as the live service, so it would not give finer zones, and it is likely over 200 MB. Not downloaded.

### Not reached (nothing verified)
- `geoportale.comune.milano.it` (the Comune's ArcGIS, named as `.../arcgis/rest/services/PGT/PGT_Milano2030_VIGENTE_R10/MapServer/5` in dati.comune.milano.it metadata): NXDOMAIN on the local resolver and on 8.8.8.8. `sit.comune.milano.it` and `geoserver.comune.milano.it` are also NXDOMAIN. Retry from another network; if it resolves, test `.../arcgis/rest/services/PGT?f=json` first.
- `pgt.comune.milano.it` returns HTTP 403 to automated requests (Azure gateway); `www.pgt.comune.milano.it` fails certificate name validation. Not bypassed.
- dati.comune.milano.it CKAN has no zoning dataset (searched pgt, piano delle regole, azzonamento, urbanistica, tessuto, ambiti, vincoli; only NIL boundaries).
- Geoportale Lombardia and the RNDT catalogue (`https://geodati.gov.it/RNDT/csw`; a CSW POST with an OGC filter on `AnyText` works) list only the regional record above for the Tavola delle previsioni. No Comune di Milano or Citta Metropolitana record for the Piano delle Regole zoning turned up. The PGTWEB archive (`https://www.regione.lombardia.it/ambiente-e-territorio/pianificazione-territoriale/pianificazione-comunale-e-provinciale/pgtweb-archivio-documentale-pgt`) is documents only; no public geometry download found. The open-data table `https://www.dati.lombardia.it/Territorio/PGT-Piani-di-governo-del-territorio/ijqk-ahfp` lists Milan PGT procedures (ISTAT 015146) with dates, not geometries.

### Rejected: `territorio/Azzonamenti_comunali`
It has a zone code (`PRG`) and an article (`ARTICOLO`), but `storico_misurc` dates Milan's instrument to **1998** (old PRG). It would cite repealed articles. Not used.

## 2. Natura 2000

- Service: `https://www.cartografia.servizirl.it/arcgis2/rest/services/ambiente/Rete_Natura_2000/MapServer` (ArcGIS 10.91, EPSG:32632). WMS twin at `.../arcgis2/services/ambiente/Rete_Natura_2000/MapServer/WMSServer` (metadata dated 2010-12-08; the data year is not stated).
- Layers: 0 ZSC/SIC (`COD_SITO`, `NOME_SITO`; 197 features); 1 ZPS (`COD_ZPS`, `NOME_ZPS`); 2 habitat (not inspected).
- Constraint class: presence of a site, with its code and name.
- Results: Duomo, Citta Studi, Parco Nord, Darsena, Chiaravalle: no hit in layers 0-2. Bosco di Vanzago centroid 45.52016, 8.97483: L0 `IT2050006` BOSCO DI VANZAGO and L1 `IT2050006`. Other centroids: Bosco di Cusago 45.44930, 9.00837 (L0 `IT2050008`); Pineta di Cesate 45.59582, 9.08709 (L0 `IT2050001`).
- Caveat: no site covers any of the five city test points, so "none" is the normal answer in Milan. Point-in-polygon only; no distance check.

## 3. PGRA flood hazard

- Service used: `https://www.cartografia.servizirl.it/expo/rest/services/gpt/direttiva_alluvioni_2022/MapServer` (ArcGIS 10.81, EPSG:32632). It is the 2022 revision of the hazard maps, with a catalogue record ("Direttiva Alluvioni 2007/60/CE - Revisione 2022").
- Other services in the same folder: `direttiva_alluvioni` (2013 maps), `_2015`, `_2019`, `_2020`, `_2023`. I compared `_2022` and `_2023`: same 28 layers, same 34 features in layer 17, identical results at the Lambro point (`Datacons` 20220601). `_2023` carries the internal project title "prova_quadrotti" and I found no catalogue record for it, so it looks like a copy. **`_2022` is the one to use.** I did not find a newer registered revision; the Region's PGRA review is ongoing, so re-check when it closes.
- Hazard layers (polygons; `Codscenar` H/M/L, `Tritorno` return period in years): H frequent 17 RP, 18 RSCM, 19 RSP, 20 ACL; M poco frequente 21 RP, 22 RSCM, 23 RSP, 24 ACL; L raro 25 RP, 26 RSCM, 27 ACL (no RSP). RP = reticolo principale, RSCM = secondario collinare e montano, RSP = secondario di pianura, ACL = aree costiere lacuali. Risk layers: 12 R4, 13 R3, 14 R2, 15 R1; 4 APSFR.
- Key fields: `Codscenar`, `Tritorno`, `Nomeelidr` (river), `Codelidr`, `Codarea`, `Datacons`, `Ambitoter`.
- Results: the five city test points have no hit in layers 17-27. Lambro 45.4650, 9.2560: L17 H (Lambro, T10), L21 M (T200), L25 L (T500), all `Datacons` 20220601. Niguarda 45.5100, 9.1850: L25 L, Seveso, T500.
- Caveat: the standard test points are outside the hazard areas, so "no hit" must be a normal result. Each scenario and network is a separate layer, so query all of 17-27.

## 4. NTA (Norme di attuazione del Piano delle Regole)

- Official page: `https://www.comune.milano.it/aree-tematiche/rigenerazione-urbana-e-urbanistica/pgt-approvato-e-vigente-milano-2030` (403 to automated requests).
- A PDF URL found by web search, **not downloaded or checked** (host 403 / certificate mismatch): `https://www.pgt.comune.milano.it/pgt_file_download/b!88kfkdym6ka1FQJ8CP8l_1ken78aR3NJkcxoQgfR2kK4M-X2Jz8iSJx6ToAzeiZ_/01IBPLUZUUQUVXO3VDTBG3EJNLSCGJO4RK/01PR_Norme_Attuazione_20190305.pdf`. By its name it is the adoption-stage text ("emendato a seguito della delibera di adozione del 5 marzo 2019"), so it may not be the approved text in force. Fetch the approved version from the page above in a browser.
- Variants after approval: partial variant of the Piano delle Regole in force from 04/10/2023 (NdA art. 45 c.3, hydraulic hazard; PAI/PGRA update); a normative partial variant (PR + PS) was in consultation with opinions due 30/10/2026; the general revision begun in 2023 was reported as revoked (Assolombarda). I could not find a consolidated text. Contact: URB.PUGDirezione@comune.milano.it (from the Assolombarda notice).

## Go / no-go

- **Natura 2000: go. PGRA: go** (use `_2022`).
- **Milan zoning: partial go.** `tav_previsioni_b` returns the current PGT's categories (NAF, TUC, AT, services, landscape, sensitivity) at every test point, so v1 can cite NTA articles per category via `zone_map.yaml`. It cannot answer at the level of ADR/ARU/tessuto, and carries no article numbers. Per the Phase 0 rule, set the v1 scope to category-level citations and show that limit in the UI.
- Upgrade path: if `geoportale.comune.milano.it` is reachable from another network, test it first; otherwise ask the Comune (Ufficio Pianificazione Urbanistica Generale) for the Piano delle Regole shapefile.
- Still to do by hand: obtain the NTA currently in force (browser download) for `parse_nta.py`.
