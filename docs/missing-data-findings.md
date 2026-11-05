# Missing data findings

Date of search: 2026-11-05. Files in `data/raw/` are git-ignored. Nothing was committed or pushed. No files outside `data/raw/` and this report were written.

## A. Parco Agricolo Sud Milano, PTC NTA amendments

Source page: https://www.cittametropolitana.mi.it/aree-tematiche/ambiente-e-tutela-del-territorio/parco_agricolo_sud_milano/territorio_e_pianificazione/piano_territoriale_di_coordinamento.html

| File | What it is | Version / date | Pages | Text extractable |
|---|---|---|---|---|
| `data/raw/PASM_PTC_DGR_8_4516_20070403.pdf` | Variant: modifica della Tavola 26 (Comune di Colturano), per sentenza TAR 6388/2004. DGR 8/4516 of 03/04/2007, BURL 3° suppl. straord. n. 16 of 19/04/2007 | DGR 8/4516, 03/04/2007 | 8 | Yes (6,304 chars) |
| `data/raw/PASM_PTC_DGR_8_10833_20091216.pdf` | Partial variant: tutela della "Zona a monumento naturale del fontanile Rile" (Comune di Settala). DGR 8/10833 of 16/12/2009, BURL 3° suppl. straord. n. 2 of 14/01/2010 | DGR 8/10833, 16/12/2009 | 5 | Yes (10,904 chars) |
| `data/raw/PASM_PTC_DGR_7_818_20000803.pdf` (already present, not re-downloaded) | Original PTC NTA, DGR 7/818 of 03/08/2000 | 03/08/2000 | n/a | n/a (not checked in this run) |

Notes:
- The page lists only these two amendments and the original DGR 7/818. It does not publish a consolidated NTA text, so no consolidated version was found.
- Downloads: Chrome opened the PDFs from the site; I saved them through Chrome's PDF viewer download button, then moved them into `data/raw/`. A direct curl fetch of the same URLs was denied by the permission classifier and was not retried.

## B. PGT Milano 2030 schede / indirizzi for Ambiti di Trasformazione (ATU, ATP, PCU)

Reached in Chrome (pgt.comune.milano.it loaded without a 403 in the browser):
- https://pgt.comune.milano.it/dpmilano-2030-visione-costruzione-strategie-spazi (DP General Report page, 2019 text)
- https://pgt.comune.milano.it/pgt-milano2030-vigente (states the PGT was approved by DCC n. 34 of 14/10/2019, effective 05/02/2020, with later corrections)
- Documento di Piano vigente: attachments 01DP Relazione generale (08/03/2023, modified by DCC 100 of 19/12/2022), 02DP Norme di attuazione (05/02/2020), 03DP Tav. D01 (08/03/2023), 04DP Tav. D02 (05/02/2020), 05DP Tav. D03 (05/02/2020), 06DP Allegato 1 (05/02/2020)
- Piano delle Regole vigente: updated to DCC 93 of 04/12/2025 and DCC 63 of 09/07/2026. Its attachments are the PdR documents, not ambit schede.
- Atlante (Milano dei quartieri): https://pgt.comune.milano.it/dpmilano-2030-visione-costruzione-strategie-spazi/spazi/milano-dei-quartieri/atlante. Index of 26 district-level tables (PDF). Not downloaded: they are maps by district, not per-ambito schede.

Already present in `data/raw/`:
- `DP_Relazione_generale_20230308.pdf` (160 pages). It mentions "Abbazie" (p. 104, 125, 127, 131) and "Idroscalo" (p. 60, 100, 101, 103). These are city-wide and district strategy maps and text, not per-ambito schede.
- `DP_Norme_Attuazione_202002051_bis_vig.pdf` (10 pages). No "scheda" or "Abbazie" or "Idroscalo" text.
- `DP_DAll01_Contenuti_Paesaggistici_REC_202002051_bis_vig.pdf` (70 pages). Mentions Abbazie (p. 8) and Idroscalo (p. 42, 45, 63).

Not found:
- Per-ambito schede or indirizzi for PCU3 "Le Abbazie" or PCU4 "L'Idroscalo". None of the reached DP attachments or the Atlante index contain "PCU3" or "PCU4". No schede PDF or HTML page was located. Not saved as `.txt` because no such page was reached.
- Not checked: the full DP Relazione text for ATU/ATP/PCU indirizzi (the file is large and was only keyword-searched).

## C. Live map layer for Parco Agricolo Sud (and other parks / PLIS)

Service root: https://www.cartografia.servizirl.it/arcgis2/rest/services/ambiente (folder `ambiente`, arcgis2). All queries returned valid JSON. Projection: wkid 32632 (the query used inSR=4326).

Candidate layers and point results (lat, lon as requested):

Point results (`features` returned, name field):

| Layer | Name field | Chiaravalle 45.4170, 9.2350 | Duomo 45.4642, 9.1900 | Parco Nord 45.5281, 9.2050 | Lambro/Idroscalo 45.4650, 9.2560 |
|---|---|---|---|---|---|
| `AreeProtette/MapServer/9` ("Parchi regionali") | NOME_PA | Parco Agricolo Sud Milano | none | none | Parco Agricolo Sud Milano |
| `Parchi_Regionali_Nazionali/MapServer/1` ("Parchi regionali") | NOME_PA | Parco Agricolo Sud Milano | none | none | Parco Agricolo Sud Milano |
| `parchi/MapServer/2` ("Parchi") | NOME_PA | Parco Agricolo Sud Milano | none | none | Parco Agricolo Sud Milano |
| `AreeProtette/MapServer/11` ("Parchi locali di interesse sovracomunale", PLIS) | NOME_PLIS | none | none | none | none |
| `PLIS/MapServer/0` (PLIS) | NOME_PLIS | none | none | none | none |
| `AreeProtette/MapServer/8` ("Parchi naturali") | NOME_PAN | none | none | none | none |
| `Parchi_Naturali/MapServer/0` | NOME_PAN | none | none | none | none |
| `AreeProtette/MapServer/10` and `Parchi_Regionali_Nazionali/MapServer/2` ("Parchi nazionali") | NOME_PA | none | none | none | none |

Layer details (all wkid 32632):
- `AreeProtette/MapServer/9`: OBJECTID, DTIPO_IDE, NOME_PA, NOME_ENTE, SEDE_ENTE, DATTUA_PA, OBJECTID_1. Attribute for Parco Agricolo Sud Milano: DTIPO_IDE "Legge Regionale", NOME_ENTE "Provincia di Milano", DATTUA_PA "Parco con P.T.C. approvato".
- `parchi/MapServer/2`: also returns COD_PA 21, LIV_AP "Regionale".

Findings:
- Yes: the regional park layers return Parco Agricolo Sud Milano at Chiaravalle and at Lambro/Idroscalo, and nothing at Duomo, as expected.
- Parco Nord: no candidate layer returned a feature at 45.5281, 9.2050. Either Parco Nord is not in these layers or the point is outside it. Not confirmed; needs checking against another source.
- PLIS: none of the four points is inside a PLIS in these layers. The PLIS layers returned valid JSON but no features.
- Not checked: other arcgis folders (`territorio`, `sistemiverdi`, `arcgis1`) for a separate park layer.

## Could not find / open items

- A and B: see the sections above. B has no per-ambito schede in the reached sources.
- C: Parco Nord is not confirmed in the layers tested.
