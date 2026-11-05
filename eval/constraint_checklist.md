# Constraint checklist (to be checked by a human)

NOT VERIFIED. Each row is what the plugin reports for a point (live query of the regional ArcGIS services on 2026-11-05). To check a point, open a viewer, go to the coordinates, switch on the PGT / Natura 2000 / PGRA layers and compare. Tick a box only after comparing.

Viewers (generic entry pages; type the coordinates in their search box):
- Geoportale Lombardia: https://www.geoportale.regione.lombardia.it/
- Geoportale del Comune di Milano: https://geoportale.comune.milano.it/
- Each row also has an OpenStreetMap link to see where the point is.

## p01. Duomo

- Coordinates: lat 45.46420, lon 9.19000 (WGS84); lon,lat for the viewer search: `45.46420, 9.19000`
- Links: [map](https://www.openstreetmap.org/?mlat=45.46420&mlon=9.19000#map=17/45.46420/9.19000) · [Geoportale Lombardia](https://www.geoportale.regione.lombardia.it/) · [Geoportale Milano](https://geoportale.comune.milano.it/)
- Plugin findings:
  - Nuclei di antica formazione (NAF) (pgt_naf) [COD_NUC=15] -> PR-art-18, PR-art-19
  - Ambiti del tessuto urbano consolidato (TUC) (pgt_previsioni_tuc) [AMB_URB=23, COD_DEST1=100, DCOD_DEST1=RESIDENZIALE, SPEC_DEST=1] -> PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5 (VERIFY)
  - Classi di sensibilità paesistica (CLASSE 1-5) (pgt_sensibilita) [CLASSE=5, DESCRIZION=SENSIBILITA' MOLTO ELEVATA] -> PR-art-34 (VERIFY)
  - Fattibilità geologica (Componente geologica PGT) (pgt_fattibilita_geo) [CLASSE=2, DESCR_FATTIBILITA=Fattibilità con modeste limitazioni, FATTORI_PERICOLO=II - Fattibilità con modeste limitazioni - II] -> PR-art-44
- Articles shown: PR-art-18, PR-art-19, PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5, PR-art-34, PR-art-44, PR-art-7, PR-art-9, PR-art-10, PR-art-12, PR-art-17, PR-art-4, PR-art-42, PR-art-43, PR-art-47, PR-art-48, CG-art-47, CGS-sec-1, CGS-sec-2, CG-art-44, DPA1-sec-21, DPA1-sec-22, PR-art-20, PR-art-21, PR-art-22, PR-art-23
- [ ] zoning / urban fabric matches the viewer
- [ ] geological feasibility class matches
- [ ] Natura 2000 matches (hit or no hit)
- [ ] flood hazard / risk (PGRA) matches
- Notes: 

## p02. Citta Studi

- Coordinates: lat 45.47810, lon 9.22690 (WGS84); lon,lat for the viewer search: `45.47810, 9.22690`
- Links: [map](https://www.openstreetmap.org/?mlat=45.47810&mlon=9.22690#map=17/45.47810/9.22690) · [Geoportale Lombardia](https://www.geoportale.regione.lombardia.it/) · [Geoportale Milano](https://geoportale.comune.milano.it/)
- Plugin findings:
  - Servizi e impianti (pgt_servizi) [TIPO_SERV=52, DTIPO_SERV=AREE A VERDE, STATO=1, DSTATO=ESISTENTE, LIV_TER=30] -> PS-art-7, PS-art-8 (VERIFY)
  - Ambiti del tessuto urbano consolidato (TUC) (pgt_previsioni_tuc) [AMB_URB=23, COD_DEST1=100, DCOD_DEST1=RESIDENZIALE, SPEC_DEST=1] -> PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5 (VERIFY)
  - Classi di sensibilità paesistica (CLASSE 1-5) (pgt_sensibilita) [CLASSE=4, DESCRIZION=SENSIBILITA' ELEVATA] -> PR-art-34 (VERIFY)
  - Fattibilità geologica (Componente geologica PGT) (pgt_fattibilita_geo) [CLASSE=2, DESCR_FATTIBILITA=Fattibilità con modeste limitazioni, FATTORI_PERICOLO=II - Fattibilità con modeste limitazioni - II] -> PR-art-44
- Articles shown: PS-art-7, PS-art-8, PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5, PR-art-34, PR-art-44, PS-art-4, PS-art-5, PS-art-6, PS-art-12, PR-art-1, PR-art-7, PR-art-53, PR-art-9, PR-art-10, PR-art-12, PR-art-17, PR-art-4, PR-art-42, PR-art-43, PR-art-47, PR-art-48, CG-art-47, CGS-sec-1, CGS-sec-2, CG-art-44, DPA1-sec-21, DPA1-sec-22, PS-art-9, PR-art-18, PR-art-19, PR-art-20, PR-art-21, PR-art-22, PR-art-23
- [ ] zoning / urban fabric matches the viewer
- [ ] geological feasibility class matches
- [ ] Natura 2000 matches (hit or no hit)
- [ ] flood hazard / risk (PGRA) matches
- Notes: 

## p03. Parco Nord

- Coordinates: lat 45.52810, lon 9.20500 (WGS84); lon,lat for the viewer search: `45.52810, 9.20500`
- Links: [map](https://www.openstreetmap.org/?mlat=45.52810&mlon=9.20500#map=17/45.52810/9.20500) · [Geoportale Lombardia](https://www.geoportale.regione.lombardia.it/) · [Geoportale Milano](https://geoportale.comune.milano.it/)
- Plugin findings:
  - Ambiti del tessuto urbano consolidato (TUC) (pgt_previsioni_tuc) [AMB_URB=23, COD_DEST1=100, DCOD_DEST1=RESIDENZIALE, SPEC_DEST=1] -> PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5 (VERIFY)
  - Classi di sensibilità paesistica (CLASSE 1-5) (pgt_sensibilita) [CLASSE=2, DESCRIZION=SENSIBILITA' BASSA] -> PR-art-34 (VERIFY)
  - Fattibilità geologica (Componente geologica PGT) (pgt_fattibilita_geo) [CLASSE=2, DESCR_FATTIBILITA=Fattibilità con modeste limitazioni, FATTORI_PERICOLO=II - Fattibilità con modeste limitazioni - II] -> PR-art-44
- Articles shown: PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5, PR-art-34, PR-art-44, PR-art-7, PR-art-9, PR-art-10, PR-art-12, PR-art-17, PR-art-4, PR-art-42, PR-art-43, PR-art-47, PR-art-48, CG-art-47, CGS-sec-1, CGS-sec-2, CG-art-44, DPA1-sec-21, DPA1-sec-22, PR-art-18, PR-art-19, PR-art-20, PR-art-21, PR-art-22, PR-art-23
- [ ] zoning / urban fabric matches the viewer
- [ ] geological feasibility class matches
- [ ] Natura 2000 matches (hit or no hit)
- [ ] flood hazard / risk (PGRA) matches
- Notes: 

## p04. Darsena (Navigli)

- Coordinates: lat 45.45200, lon 9.17600 (WGS84); lon,lat for the viewer search: `45.45200, 9.17600`
- Links: [map](https://www.openstreetmap.org/?mlat=45.45200&mlon=9.17600#map=17/45.45200/9.17600) · [Geoportale Lombardia](https://www.geoportale.regione.lombardia.it/) · [Geoportale Milano](https://geoportale.comune.milano.it/)
- Plugin findings:
  - Nuclei di antica formazione (NAF) (pgt_naf) [COD_NUC=15] -> PR-art-18, PR-art-19
  - Ambiti del tessuto urbano consolidato (TUC) (pgt_previsioni_tuc) [AMB_URB=23, COD_DEST1=100, DCOD_DEST1=RESIDENZIALE, SPEC_DEST=1] -> PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5 (VERIFY)
  - Classi di sensibilità paesistica (CLASSE 1-5) (pgt_sensibilita) [CLASSE=5, DESCRIZION=SENSIBILITA' MOLTO ELEVATA] -> PR-art-34 (VERIFY)
  - Fattibilità geologica (Componente geologica PGT) (pgt_fattibilita_geo) [CLASSE=2, DESCR_FATTIBILITA=Fattibilità con modeste limitazioni, FATTORI_PERICOLO=II - Fattibilità con modeste limitazioni - II] -> PR-art-44
- Articles shown: PR-art-18, PR-art-19, PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5, PR-art-34, PR-art-44, PR-art-7, PR-art-9, PR-art-10, PR-art-12, PR-art-17, PR-art-4, PR-art-42, PR-art-43, PR-art-47, PR-art-48, CG-art-47, CGS-sec-1, CGS-sec-2, CG-art-44, DPA1-sec-21, DPA1-sec-22, PR-art-20, PR-art-21, PR-art-22, PR-art-23
- [ ] zoning / urban fabric matches the viewer
- [ ] geological feasibility class matches
- [ ] Natura 2000 matches (hit or no hit)
- [ ] flood hazard / risk (PGRA) matches
- Notes: 

## p05. Chiaravalle (Parco Agricolo Sud)

- Coordinates: lat 45.41700, lon 9.23500 (WGS84); lon,lat for the viewer search: `45.41700, 9.23500`
- Links: [map](https://www.openstreetmap.org/?mlat=45.41700&mlon=9.23500#map=17/45.41700/9.23500) · [Geoportale Lombardia](https://www.geoportale.regione.lombardia.it/) · [Geoportale Milano](https://geoportale.comune.milano.it/)
- Plugin findings:
  - Ambiti di trasformazione (pgt_at) [AMB_TRAS=29, NOME_AMB=Le Abbazie (PCU3), DFUN_PREV1=RESIDENZIALE] -> PTC-art-26, PTC-all-A (VERIFY)
  - Aree di valore paesaggistico-ambientale ed ecologico (pgt_paesaggio) [COD_PAES=20, TIPO_AMB=502, DESCRIZION=AMBITI, ELEMENTI E SISTEMI DEL PAESAGGIO AGRARIO TRADIZIONALE] -> PR-art-34 (VERIFY)
  - Classi di sensibilità paesistica (CLASSE 1-5) (pgt_sensibilita) [CLASSE=4, DESCRIZION=SENSIBILITA' ELEVATA] -> PR-art-34 (VERIFY)
  - Fattibilità geologica (Componente geologica PGT) (pgt_fattibilita_geo) [CLASSE=3, DESCR_FATTIBILITA=Fattibilità con consistenti limitazioni, FATTORI_PERICOLO=III - Fattibilità con consistenti limitazioni - IIIc+IIId] -> PR-art-45
- Articles shown: PTC-art-26, PTC-all-A, PR-art-34, PR-art-45, PR-art-1, PR-art-3, PR-art-35, PR-art-52, PR-art-53, DP-art-1, DP-art-2, PR-art-2, PR-art-24, PR-art-36, PR-art-4, PR-art-13, PR-art-42, PR-art-43, PR-art-47, PR-art-48, CG-art-47, CGS-sec-1, CGS-sec-2, CG-art-45, DPA1-sec-21, DPA1-sec-22, PTC-art-16, PTC-art-34
- [ ] zoning / urban fabric matches the viewer
- [ ] geological feasibility class matches
- [ ] Natura 2000 matches (hit or no hit)
- [ ] flood hazard / risk (PGRA) matches
- Notes: 

## p06. Lambro (flood positive control)

- Coordinates: lat 45.46500, lon 9.25600 (WGS84); lon,lat for the viewer search: `45.46500, 9.25600`
- Links: [map](https://www.openstreetmap.org/?mlat=45.46500&mlon=9.25600#map=17/45.46500/9.25600) · [Geoportale Lombardia](https://www.geoportale.regione.lombardia.it/) · [Geoportale Milano](https://geoportale.comune.milano.it/)
- Plugin findings:
  - Ambiti di trasformazione (pgt_at) [AMB_TRAS=26, NOME_AMB=L'Idroscalo (PCU4), DFUN_PREV1=RESIDENZIALE] -> PTC-art-26, PTC-all-A (VERIFY)
  - Classi di sensibilità paesistica (CLASSE 1-5) (pgt_sensibilita) [CLASSE=3, DESCRIZION=SENSIBILITA' MEDIA] -> PR-art-34 (VERIFY)
  - Fattibilità geologica (Componente geologica PGT) (pgt_fattibilita_geo) [CLASSE=3, DESCR_FATTIBILITA=Fattibilità con consistenti limitazioni, FATTORI_PERICOLO=III - Fattibilità con consistenti limitazioni - IIIa+IIIc] -> PR-art-45
  - Area a potenziale rischio significativo di alluvione (APSFR) (pgra_APSFR) [nameAPSFR=Città di Milano - Reticolo Nord Milano, relZoneId=ITN008, specHazTyp=A11 - Fluvial] -> -
  - Rischio alluvioni (PGRA) (pgra_R3) [Ris=R3, Danno=D2, CatUE=Beni paesaggistici e culturali, Nomeelidr=Lambro] -> PR-art-43, PR-art-45, PR-art-46, PR-art-48 (VERIFY)
  - Pericolosita alluvioni (PGRA) (pgra_H_RP) [Codscenar=H, Tritorno=10, Nomeelidr=Lambro, Ambitoter=RP, nta_scenario=P3] -> PR-art-45, PR-art-46, CG-art-45, CG-art-46 (VERIFY)
  - Pericolosita alluvioni (PGRA) (pgra_M_RP) [Codscenar=M, Tritorno=200, Nomeelidr=Lambro, Ambitoter=RP, nta_scenario=P2] -> PR-art-44, PR-art-45, PR-art-46, CG-art-44, CG-art-45, CG-art-46 (VERIFY)
  - Pericolosita alluvioni (PGRA) (pgra_L_RP) [Codscenar=L, Tritorno=500, Nomeelidr=Lambro, Ambitoter=RP, nta_scenario=P1] -> PR-art-44, CG-art-44 (VERIFY)
- Articles shown: PTC-art-26, PTC-all-A, PR-art-34, PR-art-45, PR-art-43, PR-art-46, PR-art-48, CG-art-45, CG-art-46, PR-art-44, CG-art-44, PR-art-1, PR-art-3, PR-art-35, PR-art-52, PR-art-53, DP-art-1, DP-art-2, PR-art-4, PR-art-13, PR-art-42, PR-art-47, CG-art-47, CGS-sec-1, CGS-sec-2, CG-art-43, DPA1-sec-21, DPA1-sec-22
- [ ] zoning / urban fabric matches the viewer
- [ ] geological feasibility class matches
- [ ] Natura 2000 matches (hit or no hit)
- [ ] flood hazard / risk (PGRA) matches
- Notes: 

## p07. Stazione Centrale

- Coordinates: lat 45.48620, lon 9.20460 (WGS84); lon,lat for the viewer search: `45.48620, 9.20460`
- Links: [map](https://www.openstreetmap.org/?mlat=45.48620&mlon=9.20460#map=17/45.48620/9.20460) · [Geoportale Lombardia](https://www.geoportale.regione.lombardia.it/) · [Geoportale Milano](https://geoportale.comune.milano.it/)
- Plugin findings:
  - Servizi e impianti (pgt_servizi) [TIPO_SERV=34, DTIPO_SERV=ATTREZZATURE DI DEPOSITO E SERVIZIO TRASPORTI PUBBLICI, STATO=1, DSTATO=ESISTENTE, LIV_TER=31] -> PS-art-7, PS-art-8 (VERIFY)
  - Ambiti del tessuto urbano consolidato (TUC) (pgt_previsioni_tuc) [AMB_URB=23, COD_DEST1=100, DCOD_DEST1=RESIDENZIALE, SPEC_DEST=1] -> PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5 (VERIFY)
  - Classi di sensibilità paesistica (CLASSE 1-5) (pgt_sensibilita) [CLASSE=4, DESCRIZION=SENSIBILITA' ELEVATA] -> PR-art-34 (VERIFY)
  - Ambiti di rigenerazione urbana e territoriale (pgt_rigenerazione) [CATEGORIA=2, NOME_AMB=Ambito di rigenerazione] -> PR-art-14, PR-art-15, DP-art-3 (VERIFY)
  - Fattibilità geologica (Componente geologica PGT) (pgt_fattibilita_geo) [CLASSE=3, DESCR_FATTIBILITA=Fattibilità con consistenti limitazioni, FATTORI_PERICOLO=III - Fattibilità con consistenti limitazioni - IIIa] -> PR-art-45
  - Rischio alluvioni (PGRA) (pgra_R4) [Ris=R4, Danno=D4, CatUE=Attività economiche e sociali, Nomeelidr=Seveso] -> PR-art-43, PR-art-45, PR-art-46, PR-art-48 (VERIFY)
  - Pericolosita alluvioni (PGRA) (pgra_H_RP) [Codscenar=H, Tritorno=10, Nomeelidr=Seveso, Ambitoter=RP, nta_scenario=P3] -> PR-art-45, PR-art-46, CG-art-45, CG-art-46 (VERIFY)
  - Pericolosita alluvioni (PGRA) (pgra_M_RP) [Codscenar=M, Tritorno=100, Nomeelidr=Seveso, Ambitoter=RP, nta_scenario=P2] -> PR-art-44, PR-art-45, PR-art-46, CG-art-44, CG-art-45, CG-art-46 (VERIFY)
  - Pericolosita alluvioni (PGRA) (pgra_L_RP) [Codscenar=L, Tritorno=500, Nomeelidr=Seveso, Ambitoter=RP, nta_scenario=P1] -> PR-art-44, CG-art-44 (VERIFY)
- Articles shown: PS-art-7, PS-art-8, PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5, PR-art-34, PR-art-14, PR-art-15, DP-art-3, PR-art-45, PR-art-43, PR-art-46, PR-art-48, CG-art-45, CG-art-46, PR-art-44, CG-art-44, PS-art-4, PS-art-5, PS-art-6, PS-art-12, PR-art-1, PR-art-7, PR-art-53, PR-art-9, PR-art-10, PR-art-12, PR-art-17, PR-art-4, PR-art-16, PR-art-22, PR-art-23, DP-art-4, PR-art-42, PR-art-47, CG-art-47, CGS-sec-1, CGS-sec-2, CG-art-43, DPA1-sec-21, DPA1-sec-22, PS-art-9, PR-art-18, PR-art-19, PR-art-20, PR-art-21
- [ ] zoning / urban fabric matches the viewer
- [ ] geological feasibility class matches
- [ ] Natura 2000 matches (hit or no hit)
- [ ] flood hazard / risk (PGRA) matches
- Notes: 

## p08. San Siro stadium

- Coordinates: lat 45.47810, lon 9.12400 (WGS84); lon,lat for the viewer search: `45.47810, 9.12400`
- Links: [map](https://www.openstreetmap.org/?mlat=45.47810&mlon=9.12400#map=17/45.47810/9.12400) · [Geoportale Lombardia](https://www.geoportale.regione.lombardia.it/) · [Geoportale Milano](https://geoportale.comune.milano.it/)
- Plugin findings:
  - Servizi e impianti (pgt_servizi) [TIPO_SERV=33, DTIPO_SERV=GRANDI IMPIANTI PER L'AGONISMO E LO SPETTACOLO, STATO=1, DSTATO=ESISTENTE, LIV_TER=31] -> PS-art-7, PS-art-8 (VERIFY)
  - Ambiti del tessuto urbano consolidato (TUC) (pgt_previsioni_tuc) [AMB_URB=23, COD_DEST1=100, DCOD_DEST1=RESIDENZIALE, SPEC_DEST=1] -> PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5 (VERIFY)
  - Classi di sensibilità paesistica (CLASSE 1-5) (pgt_sensibilita) [CLASSE=2, DESCRIZION=SENSIBILITA' BASSA] -> PR-art-34 (VERIFY)
  - Ambiti di rigenerazione urbana e territoriale (pgt_rigenerazione) [CATEGORIA=2, NOME_AMB=Ambito di rigenerazione] -> PR-art-14, PR-art-15, DP-art-3 (VERIFY)
  - Fattibilità geologica (Componente geologica PGT) (pgt_fattibilita_geo) [CLASSE=2, DESCR_FATTIBILITA=Fattibilità con modeste limitazioni, FATTORI_PERICOLO=II - Fattibilità con modeste limitazioni - II] -> PR-art-44
- Articles shown: PS-art-7, PS-art-8, PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5, PR-art-34, PR-art-14, PR-art-15, DP-art-3, PR-art-44, PS-art-4, PS-art-5, PS-art-6, PS-art-12, PR-art-1, PR-art-7, PR-art-53, PR-art-9, PR-art-10, PR-art-12, PR-art-17, PR-art-4, PR-art-16, PR-art-22, PR-art-23, DP-art-4, PR-art-42, PR-art-43, PR-art-47, PR-art-48, CG-art-47, CGS-sec-1, CGS-sec-2, CG-art-44, DPA1-sec-21, DPA1-sec-22, PS-art-9, PR-art-18, PR-art-19, PR-art-20, PR-art-21
- [ ] zoning / urban fabric matches the viewer
- [ ] geological feasibility class matches
- [ ] Natura 2000 matches (hit or no hit)
- [ ] flood hazard / risk (PGRA) matches
- Notes: 

## p09. Isola / Porta Garibaldi

- Coordinates: lat 45.48500, lon 9.18800 (WGS84); lon,lat for the viewer search: `45.48500, 9.18800`
- Links: [map](https://www.openstreetmap.org/?mlat=45.48500&mlon=9.18800#map=17/45.48500/9.18800) · [Geoportale Lombardia](https://www.geoportale.regione.lombardia.it/) · [Geoportale Milano](https://geoportale.comune.milano.it/)
- Plugin findings:
  - Ambiti del tessuto urbano consolidato (TUC) (pgt_previsioni_tuc) [AMB_URB=23, COD_DEST1=100, DCOD_DEST1=RESIDENZIALE, SPEC_DEST=1] -> PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5 (VERIFY)
  - Classi di sensibilità paesistica (CLASSE 1-5) (pgt_sensibilita) [CLASSE=4, DESCRIZION=SENSIBILITA' ELEVATA] -> PR-art-34 (VERIFY)
  - Ambiti di rigenerazione urbana e territoriale (pgt_rigenerazione) [CATEGORIA=2, NOME_AMB=Ambito di rigenerazione] -> PR-art-14, PR-art-15, DP-art-3 (VERIFY)
  - Fattibilità geologica (Componente geologica PGT) (pgt_fattibilita_geo) [CLASSE=2, DESCR_FATTIBILITA=Fattibilità con modeste limitazioni, FATTORI_PERICOLO=II - Fattibilità con modeste limitazioni - II] -> PR-art-44
- Articles shown: PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5, PR-art-34, PR-art-14, PR-art-15, DP-art-3, PR-art-44, PR-art-7, PR-art-9, PR-art-10, PR-art-12, PR-art-17, PR-art-4, PR-art-16, PR-art-22, PR-art-23, DP-art-4, PR-art-42, PR-art-43, PR-art-47, PR-art-48, CG-art-47, CGS-sec-1, CGS-sec-2, CG-art-44, DPA1-sec-21, DPA1-sec-22, PR-art-18, PR-art-19, PR-art-20, PR-art-21
- [ ] zoning / urban fabric matches the viewer
- [ ] geological feasibility class matches
- [ ] Natura 2000 matches (hit or no hit)
- [ ] flood hazard / risk (PGRA) matches
- Notes: 

## p10. Linate airport

- Coordinates: lat 45.44500, lon 9.27600 (WGS84); lon,lat for the viewer search: `45.44500, 9.27600`
- Links: [map](https://www.openstreetmap.org/?mlat=45.44500&mlon=9.27600#map=17/45.44500/9.27600) · [Geoportale Lombardia](https://www.geoportale.regione.lombardia.it/) · [Geoportale Milano](https://geoportale.comune.milano.it/)
- Plugin findings:
  - Servizi e impianti (pgt_servizi) [TIPO_SERV=32, DTIPO_SERV=AREE DI INTERSCAMBIO PASSEGGERI, STATO=1, DSTATO=ESISTENTE, LIV_TER=31] -> PS-art-7, PS-art-8 (VERIFY)
  - Ambiti del tessuto urbano consolidato (TUC) (pgt_previsioni_tuc) [AMB_URB=7, COD_DEST1=0, SPEC_DEST=0] -> PR-art-6, PR-art-8, PR-art-13, PS-art-11 (VERIFY)
  - Classi di sensibilità paesistica (CLASSE 1-5) (pgt_sensibilita) [CLASSE=2, DESCRIZION=SENSIBILITA' BASSA] -> PR-art-34 (VERIFY)
  - Fattibilità geologica (Componente geologica PGT) (pgt_fattibilita_geo) [CLASSE=3, DESCR_FATTIBILITA=Fattibilità con consistenti limitazioni, FATTORI_PERICOLO=Aree vulnerabili dal punto di vista idraulico -  aree con tirante inferiore a 90cm  inserite in fascia C delimitata  da un limite di progetto tra la fascia B e C PAI del fiume Lambro (3.1B/C)] -> PR-art-45
  - Area a potenziale rischio significativo di alluvione (APSFR) (pgra_APSFR) [nameAPSFR=Città di Milano - Reticolo Nord Milano, relZoneId=ITN008, specHazTyp=A11 - Fluvial] -> -
  - Rischio alluvioni (PGRA) (pgra_R2) [Ris=R2, Danno=D4, CatUE=Attività economiche e sociali, Nomeelidr=Lambro] -> PR-art-43, PR-art-45, PR-art-46, PR-art-48 (VERIFY)
  - Pericolosita alluvioni (PGRA) (pgra_L_RP) [Codscenar=L, Tritorno=500, Nomeelidr=Lambro, Ambitoter=RP, nta_scenario=P1] -> PR-art-44, CG-art-44 (VERIFY)
- Articles shown: PS-art-7, PS-art-8, PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-34, PR-art-45, PR-art-43, PR-art-46, PR-art-48, PR-art-44, CG-art-44, PS-art-4, PS-art-5, PS-art-6, PS-art-12, PR-art-1, PR-art-7, PR-art-53, PR-art-5, PR-art-9, PR-art-10, PR-art-12, PR-art-17, PR-art-4, PR-art-42, PR-art-47, CG-art-47, CGS-sec-1, CGS-sec-2, CG-art-45, CG-art-43, CG-art-46, DPA1-sec-21, DPA1-sec-22, PS-art-9, PR-art-18, PR-art-19, PR-art-20, PR-art-21, PR-art-22, PR-art-23
- [ ] zoning / urban fabric matches the viewer
- [ ] geological feasibility class matches
- [ ] Natura 2000 matches (hit or no hit)
- [ ] flood hazard / risk (PGRA) matches
- Notes: 

## p11. Bicocca

- Coordinates: lat 45.51800, lon 9.21100 (WGS84); lon,lat for the viewer search: `45.51800, 9.21100`
- Links: [map](https://www.openstreetmap.org/?mlat=45.51800&mlon=9.21100#map=17/45.51800/9.21100) · [Geoportale Lombardia](https://www.geoportale.regione.lombardia.it/) · [Geoportale Milano](https://geoportale.comune.milano.it/)
- Plugin findings:
  - Servizi e impianti (pgt_servizi) [TIPO_SERV=52, DTIPO_SERV=AREE A VERDE, STATO=1, DSTATO=ESISTENTE, LIV_TER=30] -> PS-art-7, PS-art-8 (VERIFY)
  - Ambiti del tessuto urbano consolidato (TUC) (pgt_previsioni_tuc) [AMB_URB=23, COD_DEST1=100, DCOD_DEST1=RESIDENZIALE, SPEC_DEST=1] -> PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5 (VERIFY)
  - Classi di sensibilità paesistica (CLASSE 1-5) (pgt_sensibilita) [CLASSE=2, DESCRIZION=SENSIBILITA' BASSA] -> PR-art-34 (VERIFY)
  - Fattibilità geologica (Componente geologica PGT) (pgt_fattibilita_geo) [CLASSE=2, DESCR_FATTIBILITA=Fattibilità con modeste limitazioni, FATTORI_PERICOLO=II - Fattibilità con modeste limitazioni - II] -> PR-art-44
- Articles shown: PS-art-7, PS-art-8, PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5, PR-art-34, PR-art-44, PS-art-4, PS-art-5, PS-art-6, PS-art-12, PR-art-1, PR-art-7, PR-art-53, PR-art-9, PR-art-10, PR-art-12, PR-art-17, PR-art-4, PR-art-42, PR-art-43, PR-art-47, PR-art-48, CG-art-47, CGS-sec-1, CGS-sec-2, CG-art-44, DPA1-sec-21, DPA1-sec-22, PS-art-9, PR-art-18, PR-art-19, PR-art-20, PR-art-21, PR-art-22, PR-art-23
- [ ] zoning / urban fabric matches the viewer
- [ ] geological feasibility class matches
- [ ] Natura 2000 matches (hit or no hit)
- [ ] flood hazard / risk (PGRA) matches
- Notes: 

## p12. Quarto Oggiaro

- Coordinates: lat 45.50600, lon 9.13900 (WGS84); lon,lat for the viewer search: `45.50600, 9.13900`
- Links: [map](https://www.openstreetmap.org/?mlat=45.50600&mlon=9.13900#map=17/45.50600/9.13900) · [Geoportale Lombardia](https://www.geoportale.regione.lombardia.it/) · [Geoportale Milano](https://geoportale.comune.milano.it/)
- Plugin findings:
  - Ambiti del tessuto urbano consolidato (TUC) (pgt_previsioni_tuc) [AMB_URB=23, COD_DEST1=100, DCOD_DEST1=RESIDENZIALE, SPEC_DEST=1] -> PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5 (VERIFY)
  - Classi di sensibilità paesistica (CLASSE 1-5) (pgt_sensibilita) [CLASSE=2, DESCRIZION=SENSIBILITA' BASSA] -> PR-art-34 (VERIFY)
  - Fattibilità geologica (Componente geologica PGT) (pgt_fattibilita_geo) [CLASSE=2, DESCR_FATTIBILITA=Fattibilità con modeste limitazioni, FATTORI_PERICOLO=II - Fattibilità con modeste limitazioni - II] -> PR-art-44
- Articles shown: PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5, PR-art-34, PR-art-44, PR-art-7, PR-art-9, PR-art-10, PR-art-12, PR-art-17, PR-art-4, PR-art-42, PR-art-43, PR-art-47, PR-art-48, CG-art-47, CGS-sec-1, CGS-sec-2, CG-art-44, DPA1-sec-21, DPA1-sec-22, PR-art-18, PR-art-19, PR-art-20, PR-art-21, PR-art-22, PR-art-23
- [ ] zoning / urban fabric matches the viewer
- [ ] geological feasibility class matches
- [ ] Natura 2000 matches (hit or no hit)
- [ ] flood hazard / risk (PGRA) matches
- Notes: 

## p13. Giambellino / Lorenteggio

- Coordinates: lat 45.44300, lon 9.14200 (WGS84); lon,lat for the viewer search: `45.44300, 9.14200`
- Links: [map](https://www.openstreetmap.org/?mlat=45.44300&mlon=9.14200#map=17/45.44300/9.14200) · [Geoportale Lombardia](https://www.geoportale.regione.lombardia.it/) · [Geoportale Milano](https://geoportale.comune.milano.it/)
- Plugin findings:
  - Servizi e impianti (pgt_servizi) [TIPO_SERV=52, DTIPO_SERV=AREE A VERDE, STATO=1, DSTATO=ESISTENTE, LIV_TER=30] -> PS-art-7, PS-art-8 (VERIFY)
  - Ambiti del tessuto urbano consolidato (TUC) (pgt_previsioni_tuc) [AMB_URB=23, COD_DEST1=100, DCOD_DEST1=RESIDENZIALE, SPEC_DEST=1] -> PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5 (VERIFY)
  - Classi di sensibilità paesistica (CLASSE 1-5) (pgt_sensibilita) [CLASSE=4, DESCRIZION=SENSIBILITA' ELEVATA] -> PR-art-34 (VERIFY)
  - Fattibilità geologica (Componente geologica PGT) (pgt_fattibilita_geo) [CLASSE=3, DESCR_FATTIBILITA=Fattibilità con consistenti limitazioni, FATTORI_PERICOLO=III - Fattibilità con consistenti limitazioni - IIIc] -> PR-art-45
- Articles shown: PS-art-7, PS-art-8, PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5, PR-art-34, PR-art-45, PS-art-4, PS-art-5, PS-art-6, PS-art-12, PR-art-1, PR-art-7, PR-art-53, PR-art-9, PR-art-10, PR-art-12, PR-art-17, PR-art-4, PR-art-42, PR-art-43, PR-art-47, PR-art-48, CG-art-47, CGS-sec-1, CGS-sec-2, CG-art-45, DPA1-sec-21, DPA1-sec-22, PS-art-9, PR-art-18, PR-art-19, PR-art-20, PR-art-21, PR-art-22, PR-art-23
- [ ] zoning / urban fabric matches the viewer
- [ ] geological feasibility class matches
- [ ] Natura 2000 matches (hit or no hit)
- [ ] flood hazard / risk (PGRA) matches
- Notes: 

## p14. Rogoredo

- Coordinates: lat 45.43250, lon 9.23900 (WGS84); lon,lat for the viewer search: `45.43250, 9.23900`
- Links: [map](https://www.openstreetmap.org/?mlat=45.43250&mlon=9.23900#map=17/45.43250/9.23900) · [Geoportale Lombardia](https://www.geoportale.regione.lombardia.it/) · [Geoportale Milano](https://geoportale.comune.milano.it/)
- Plugin findings:
  - Servizi e impianti (pgt_servizi) [TIPO_SERV=49, DTIPO_SERV=PARCHEGGI E AUTORIMESSE, STATO=2, DSTATO=IN PROGETTO, LIV_TER=31] -> PS-art-7, PS-art-8 (VERIFY)
  - Ambiti del tessuto urbano consolidato (TUC) (pgt_previsioni_tuc) [AMB_URB=23, COD_DEST1=100, DCOD_DEST1=RESIDENZIALE, SPEC_DEST=1] -> PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5 (VERIFY)
  - Classi di sensibilità paesistica (CLASSE 1-5) (pgt_sensibilita) [CLASSE=2, DESCRIZION=SENSIBILITA' BASSA] -> PR-art-34 (VERIFY)
  - Ambiti di rigenerazione urbana e territoriale (pgt_rigenerazione) [CATEGORIA=2, NOME_AMB=Ambito di rigenerazione] -> PR-art-14, PR-art-15, DP-art-3 (VERIFY)
  - Fattibilità geologica (Componente geologica PGT) (pgt_fattibilita_geo) [CLASSE=3, DESCR_FATTIBILITA=Fattibilità con consistenti limitazioni, FATTORI_PERICOLO=III - Fattibilità con consistenti limitazioni - IIIc] -> PR-art-45
- Articles shown: PS-art-7, PS-art-8, PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5, PR-art-34, PR-art-14, PR-art-15, DP-art-3, PR-art-45, PS-art-4, PS-art-5, PS-art-6, PS-art-12, PR-art-1, PR-art-7, PR-art-53, PR-art-9, PR-art-10, PR-art-12, PR-art-17, PR-art-4, PR-art-16, PR-art-22, PR-art-23, DP-art-4, PR-art-42, PR-art-43, PR-art-47, PR-art-48, CG-art-47, CGS-sec-1, CGS-sec-2, CG-art-45, DPA1-sec-21, DPA1-sec-22, PS-art-9, PR-art-18, PR-art-19, PR-art-20, PR-art-21
- [ ] zoning / urban fabric matches the viewer
- [ ] geological feasibility class matches
- [ ] Natura 2000 matches (hit or no hit)
- [ ] flood hazard / risk (PGRA) matches
- Notes: 

## p15. Gratosoglio

- Coordinates: lat 45.41000, lon 9.17800 (WGS84); lon,lat for the viewer search: `45.41000, 9.17800`
- Links: [map](https://www.openstreetmap.org/?mlat=45.41000&mlon=9.17800#map=17/45.41000/9.17800) · [Geoportale Lombardia](https://www.geoportale.regione.lombardia.it/) · [Geoportale Milano](https://geoportale.comune.milano.it/)
- Plugin findings:
  - Ambiti del tessuto urbano consolidato (TUC) (pgt_previsioni_tuc) [AMB_URB=23, COD_DEST1=100, DCOD_DEST1=RESIDENZIALE, SPEC_DEST=1] -> PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5 (VERIFY)
  - Classi di sensibilità paesistica (CLASSE 1-5) (pgt_sensibilita) [CLASSE=2, DESCRIZION=SENSIBILITA' BASSA] -> PR-art-34 (VERIFY)
  - Fattibilità geologica (Componente geologica PGT) (pgt_fattibilita_geo) [CLASSE=3, DESCR_FATTIBILITA=Fattibilità con consistenti limitazioni, FATTORI_PERICOLO=III - Fattibilità con consistenti limitazioni - IIIc] -> PR-art-45
- Articles shown: PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5, PR-art-34, PR-art-45, PR-art-7, PR-art-9, PR-art-10, PR-art-12, PR-art-17, PR-art-4, PR-art-42, PR-art-43, PR-art-47, PR-art-48, CG-art-47, CGS-sec-1, CGS-sec-2, CG-art-45, DPA1-sec-21, DPA1-sec-22, PR-art-18, PR-art-19, PR-art-20, PR-art-21, PR-art-22, PR-art-23
- [ ] zoning / urban fabric matches the viewer
- [ ] geological feasibility class matches
- [ ] Natura 2000 matches (hit or no hit)
- [ ] flood hazard / risk (PGRA) matches
- Notes: 

## p16. Baggio (west edge)

- Coordinates: lat 45.46500, lon 9.09200 (WGS84); lon,lat for the viewer search: `45.46500, 9.09200`
- Links: [map](https://www.openstreetmap.org/?mlat=45.46500&mlon=9.09200#map=17/45.46500/9.09200) · [Geoportale Lombardia](https://www.geoportale.regione.lombardia.it/) · [Geoportale Milano](https://geoportale.comune.milano.it/)
- Plugin findings:
  - Ambiti del tessuto urbano consolidato (TUC) (pgt_previsioni_tuc) [AMB_URB=23, COD_DEST1=100, DCOD_DEST1=RESIDENZIALE, SPEC_DEST=1] -> PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5 (VERIFY)
  - Classi di sensibilità paesistica (CLASSE 1-5) (pgt_sensibilita) [CLASSE=2, DESCRIZION=SENSIBILITA' BASSA] -> PR-art-34 (VERIFY)
  - Fattibilità geologica (Componente geologica PGT) (pgt_fattibilita_geo) [CLASSE=3, DESCR_FATTIBILITA=Fattibilità con consistenti limitazioni, FATTORI_PERICOLO=III - Fattibilità con consistenti limitazioni - IIIc] -> PR-art-45
- Articles shown: PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5, PR-art-34, PR-art-45, PR-art-7, PR-art-9, PR-art-10, PR-art-12, PR-art-17, PR-art-4, PR-art-42, PR-art-43, PR-art-47, PR-art-48, CG-art-47, CGS-sec-1, CGS-sec-2, CG-art-45, DPA1-sec-21, DPA1-sec-22, PR-art-18, PR-art-19, PR-art-20, PR-art-21, PR-art-22, PR-art-23
- [ ] zoning / urban fabric matches the viewer
- [ ] geological feasibility class matches
- [ ] Natura 2000 matches (hit or no hit)
- [ ] flood hazard / risk (PGRA) matches
- Notes: 

## p17. Barona / Naviglio Pavese

- Coordinates: lat 45.43300, lon 9.16000 (WGS84); lon,lat for the viewer search: `45.43300, 9.16000`
- Links: [map](https://www.openstreetmap.org/?mlat=45.43300&mlon=9.16000#map=17/45.43300/9.16000) · [Geoportale Lombardia](https://www.geoportale.regione.lombardia.it/) · [Geoportale Milano](https://geoportale.comune.milano.it/)
- Plugin findings:
  - Servizi e impianti (pgt_servizi) [TIPO_SERV=39, DTIPO_SERV=ATTREZZATURE OSPEDALIERE, SANITARIE E ASSISTENZIALI, STATO=1, DSTATO=ESISTENTE, LIV_TER=31] -> PS-art-7, PS-art-8 (VERIFY)
  - Ambiti del tessuto urbano consolidato (TUC) (pgt_previsioni_tuc) [AMB_URB=23, COD_DEST1=100, DCOD_DEST1=RESIDENZIALE, SPEC_DEST=1] -> PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5 (VERIFY)
  - Classi di sensibilità paesistica (CLASSE 1-5) (pgt_sensibilita) [CLASSE=2, DESCRIZION=SENSIBILITA' BASSA] -> PR-art-34 (VERIFY)
  - Ambiti di rigenerazione urbana e territoriale (pgt_rigenerazione) [CATEGORIA=2, NOME_AMB=Ambito di rigenerazione] -> PR-art-14, PR-art-15, DP-art-3 (VERIFY)
  - Fattibilità geologica (Componente geologica PGT) (pgt_fattibilita_geo) [CLASSE=2, DESCR_FATTIBILITA=Fattibilità con modeste limitazioni, FATTORI_PERICOLO=II - Fattibilità con modeste limitazioni - II] -> PR-art-44
- Articles shown: PS-art-7, PS-art-8, PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5, PR-art-34, PR-art-14, PR-art-15, DP-art-3, PR-art-44, PS-art-4, PS-art-5, PS-art-6, PS-art-12, PR-art-1, PR-art-7, PR-art-53, PR-art-9, PR-art-10, PR-art-12, PR-art-17, PR-art-4, PR-art-16, PR-art-22, PR-art-23, DP-art-4, PR-art-42, PR-art-43, PR-art-47, PR-art-48, CG-art-47, CGS-sec-1, CGS-sec-2, CG-art-44, DPA1-sec-21, DPA1-sec-22, PS-art-9, PR-art-18, PR-art-19, PR-art-20, PR-art-21
- [ ] zoning / urban fabric matches the viewer
- [ ] geological feasibility class matches
- [ ] Natura 2000 matches (hit or no hit)
- [ ] flood hazard / risk (PGRA) matches
- Notes: 

## p18. Bovisa

- Coordinates: lat 45.50700, lon 9.15800 (WGS84); lon,lat for the viewer search: `45.50700, 9.15800`
- Links: [map](https://www.openstreetmap.org/?mlat=45.50700&mlon=9.15800#map=17/45.50700/9.15800) · [Geoportale Lombardia](https://www.geoportale.regione.lombardia.it/) · [Geoportale Milano](https://geoportale.comune.milano.it/)
- Plugin findings:
  - Ambiti del tessuto urbano consolidato (TUC) (pgt_previsioni_tuc) [AMB_URB=23, COD_DEST1=100, DCOD_DEST1=RESIDENZIALE, SPEC_DEST=1] -> PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5 (VERIFY)
  - Classi di sensibilità paesistica (CLASSE 1-5) (pgt_sensibilita) [CLASSE=2, DESCRIZION=SENSIBILITA' BASSA] -> PR-art-34 (VERIFY)
  - Fattibilità geologica (Componente geologica PGT) (pgt_fattibilita_geo) [CLASSE=2, DESCR_FATTIBILITA=Fattibilità con modeste limitazioni, FATTORI_PERICOLO=II - Fattibilità con modeste limitazioni - II] -> PR-art-44
- Articles shown: PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5, PR-art-34, PR-art-44, PR-art-7, PR-art-9, PR-art-10, PR-art-12, PR-art-17, PR-art-4, PR-art-42, PR-art-43, PR-art-47, PR-art-48, CG-art-47, CGS-sec-1, CGS-sec-2, CG-art-44, DPA1-sec-21, DPA1-sec-22, PR-art-18, PR-art-19, PR-art-20, PR-art-21, PR-art-22, PR-art-23
- [ ] zoning / urban fabric matches the viewer
- [ ] geological feasibility class matches
- [ ] Natura 2000 matches (hit or no hit)
- [ ] flood hazard / risk (PGRA) matches
- Notes: 

## p19. Niguarda

- Coordinates: lat 45.52000, lon 9.18500 (WGS84); lon,lat for the viewer search: `45.52000, 9.18500`
- Links: [map](https://www.openstreetmap.org/?mlat=45.52000&mlon=9.18500#map=17/45.52000/9.18500) · [Geoportale Lombardia](https://www.geoportale.regione.lombardia.it/) · [Geoportale Milano](https://geoportale.comune.milano.it/)
- Plugin findings:
  - Servizi e impianti (pgt_servizi) [TIPO_SERV=50, DTIPO_SERV=SCUOLA DELL'OBBLIGO E DELL'INFANZIA, STATO=1, DSTATO=ESISTENTE, LIV_TER=30] -> PS-art-7, PS-art-8 (VERIFY)
  - Ambiti del tessuto urbano consolidato (TUC) (pgt_previsioni_tuc) [AMB_URB=23, COD_DEST1=100, DCOD_DEST1=RESIDENZIALE, SPEC_DEST=1] -> PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5 (VERIFY)
  - Classi di sensibilità paesistica (CLASSE 1-5) (pgt_sensibilita) [CLASSE=2, DESCRIZION=SENSIBILITA' BASSA] -> PR-art-34 (VERIFY)
  - Ambiti di rigenerazione urbana e territoriale (pgt_rigenerazione) [CATEGORIA=2, NOME_AMB=Ambito di rigenerazione] -> PR-art-14, PR-art-15, DP-art-3 (VERIFY)
  - Fattibilità geologica (Componente geologica PGT) (pgt_fattibilita_geo) [CLASSE=2, DESCR_FATTIBILITA=Fattibilità con modeste limitazioni, FATTORI_PERICOLO=II - Fattibilità con modeste limitazioni - II] -> PR-art-44
  - Area a potenziale rischio significativo di alluvione (APSFR) (pgra_APSFR) [nameAPSFR=Città di Milano - Reticolo Nord Milano, relZoneId=ITN008, specHazTyp=A11 - Fluvial] -> -
  - Rischio alluvioni (PGRA) (pgra_R4) [Ris=R4, Danno=D4, CatUE=Attività economiche e sociali, Nomeelidr=Seveso] -> PR-art-43, PR-art-45, PR-art-46, PR-art-48 (VERIFY)
  - Pericolosita alluvioni (PGRA) (pgra_M_RP) [Codscenar=M, Tritorno=100, Nomeelidr=Seveso, Ambitoter=RP, nta_scenario=P2] -> PR-art-44, PR-art-45, PR-art-46, CG-art-44, CG-art-45, CG-art-46 (VERIFY)
  - Pericolosita alluvioni (PGRA) (pgra_L_RP) [Codscenar=L, Tritorno=500, Nomeelidr=Seveso, Ambitoter=RP, nta_scenario=P1] -> PR-art-44, CG-art-44 (VERIFY)
- Articles shown: PS-art-7, PS-art-8, PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5, PR-art-34, PR-art-14, PR-art-15, DP-art-3, PR-art-44, PR-art-43, PR-art-45, PR-art-46, PR-art-48, CG-art-44, CG-art-45, CG-art-46, PS-art-4, PS-art-5, PS-art-6, PS-art-12, PR-art-1, PR-art-7, PR-art-53, PR-art-9, PR-art-10, PR-art-12, PR-art-17, PR-art-4, PR-art-16, PR-art-22, PR-art-23, DP-art-4, PR-art-42, PR-art-47, CG-art-47, CGS-sec-1, CGS-sec-2, CG-art-43, DPA1-sec-21, DPA1-sec-22, PS-art-9, PR-art-18, PR-art-19, PR-art-20, PR-art-21
- [ ] zoning / urban fabric matches the viewer
- [ ] geological feasibility class matches
- [ ] Natura 2000 matches (hit or no hit)
- [ ] flood hazard / risk (PGRA) matches
- Notes: 

## p20. Lambrate

- Coordinates: lat 45.48400, lon 9.23300 (WGS84); lon,lat for the viewer search: `45.48400, 9.23300`
- Links: [map](https://www.openstreetmap.org/?mlat=45.48400&mlon=9.23300#map=17/45.48400/9.23300) · [Geoportale Lombardia](https://www.geoportale.regione.lombardia.it/) · [Geoportale Milano](https://geoportale.comune.milano.it/)
- Plugin findings:
  - Ambiti del tessuto urbano consolidato (TUC) (pgt_previsioni_tuc) [AMB_URB=23, COD_DEST1=100, DCOD_DEST1=RESIDENZIALE, SPEC_DEST=1] -> PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5 (VERIFY)
  - Classi di sensibilità paesistica (CLASSE 1-5) (pgt_sensibilita) [CLASSE=4, DESCRIZION=SENSIBILITA' ELEVATA] -> PR-art-34 (VERIFY)
  - Fattibilità geologica (Componente geologica PGT) (pgt_fattibilita_geo) [CLASSE=2, DESCR_FATTIBILITA=Fattibilità con modeste limitazioni, FATTORI_PERICOLO=II - Fattibilità con modeste limitazioni - II] -> PR-art-44
- Articles shown: PR-art-6, PR-art-8, PR-art-13, PS-art-11, PR-art-5, PR-art-34, PR-art-44, PR-art-7, PR-art-9, PR-art-10, PR-art-12, PR-art-17, PR-art-4, PR-art-42, PR-art-43, PR-art-47, PR-art-48, CG-art-47, CGS-sec-1, CGS-sec-2, CG-art-44, DPA1-sec-21, DPA1-sec-22, PR-art-18, PR-art-19, PR-art-20, PR-art-21, PR-art-22, PR-art-23
- [ ] zoning / urban fabric matches the viewer
- [ ] geological feasibility class matches
- [ ] Natura 2000 matches (hit or no hit)
- [ ] flood hazard / risk (PGRA) matches
- Notes: 

