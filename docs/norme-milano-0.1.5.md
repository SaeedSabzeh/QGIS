# Norme Milano 0.1.5

This release improves the planning rules shown for a click and the evidence available when
checking an answer. It keeps the `norme_milano` plugin ID so QGIS can install it as an update.

## Municipal maps and coverage

- **Finer zoning.** The regional TUC polygon groups several urban contexts together. The
  plugin now queries the Comune's Tav. R.02 layers 38, 39 and 40. A single municipal hit
  identifies NAF, ADR or ARU and maps it to Piano delle Regole articles 18–19, 20–21 or
  22–23 respectively. Multiple different zone hits remain candidates. The regional NAF
  layer provides context when the municipal zone has no hit. Detailed morphology and
  intervention categories still require Tav. R.03.
  [Tav. R.02 service](https://gisportal.comune.milano.it/federated/rest/services/PGT/Milano_2030_PGT_Vigente_Tavola_R02/MapServer) ·
  [Piano delle Regole and official sheets](https://pgt.comune.milano.it/pgt-previgente/pgt-milano-2030-approvato-e-successive-modificazioni/piano-delle-regole-milano-2030/piano-delle-regole-vigente)
- **Parks and geology.** R.02 layers 15 and 17 identify Parco Nord and Parco Agricolo Sud.
  The south-park polygon may name a PTC article directly. A regional PCU name alone only
  suggests a candidate. Tav. G.17 gives the geological class, subclass and article
  reference. The regional records provide fallback coverage. The dock links the Parco
  Nord PTC for checking its park-specific rules.
  [Tav. G.17](https://gisportal.comune.milano.it/federated/rest/services/PGT/Milano_2030_PGT_Vigente_Tavola_G17/MapServer/1) ·
  [Parco Agricolo Sud PTC](https://www.cittametropolitana.mi.it/aree-tematiche/ambiente-e-tutela-del-territorio/parco_agricolo_sud_milano/territorio_e_pianificazione/piano_territoriale_di_coordinamento.html) ·
  [Parco Nord PTC](https://parconord.milano.it/wp-content/uploads/2019/09/Norme-Tecniche-di-Attuazione-PTC-Parco-Nord-Milano-2020.pdf)
- **City boundary.** The plugin checks a bundled copy of the Comune's DS2841 polygon
  locally. The copy retains the exterior ring in WGS 84, rounded to seven decimal places,
  with consecutive duplicate vertices removed. This stops a regional feature in another
  municipality from being matched to the Milan corpus. The source is the Comune di Milano
  under Creative Commons Attribution. The boundary is for routing the point lookup.
  [DS2841 and licence](https://dati.comune.milano.it/dataset/e75d91fa-eca6-4ee5-b96e-08bcdbb8d6f0)

The dock links to the map layer behind each finding and the official publication behind
each article. Article details include the source document version and pages in the
bundled corpus's PDF. The underlying 172 article texts were regenerated for comparison
and matched the 0.1.4 corpus.

## Q&A and evidence

The search retains planning documents and article references explicitly named in the
question even if the keyword rewrite drops them. Italian equivalents for English planning
terms help when the original question is used. The answer prompt asks the model to cover
each part, including conditions and exceptions, and identifies layers whose coverage was
unavailable. Gemini requests a typed JSON response for both languages, article IDs and
supporting excerpts. The dock shows passages that occur in the exact text sent to the
model. It warns when citation support is missing and discards unreadable model replies.
The passage check establishes that the quotation exists. Interpretation and completeness
still require review against the official sources.

The archived point data and 38 scored questions give the replay below. There are 41 expected
article IDs across those questions. Both versions used the same cached map results and
the same question text or archived keywords. The metric counts IDs in the actual prompt.

| Input | 0.1.4 | 0.1.5 |
|---|---:|---:|
| Original question text | 34/41 | 40/41 |
| Archived Italian keywords | 37/41 | 40/41 |

The archived 6 November model run recorded 17/38 fully correct answers and 79% of
available fact points. The replay above measures retrieval coverage. The targeted
16 November live check below exercises the changed answer protocol with four public
benchmark prompts on `gemini-3.5-flash`. It does not estimate accuracy on the full set.
[Historical judge summary](../eval/results/summary_judge.md)

| Live question | Observed result |
|---|---|
| Base and maximum floor-area index (q03) | Returned 0.35, 0.70 and the conditional 1.0, with three matched passages from PR art. 6 |
| Service obligations below and above the base index (q24) | Stated the base exemption and the rule for excess floor area. Linked PS art. 11 and PR art. 33. Omitted the productive-use percentage |
| Building near a Naviglio in the park (q38) | Returned the 100 m PTC condition and the PGT hierarchy. Quoted PTC art. 42 and PR art. 35. Omitted the separately requested PR art. 50 rules |
| Natura 2000 procedure and timing (q39) | Said the supplied material lacks the requested details and gave no citation |

All four final replies parsed. The three cited replies had at least one matched excerpt
for each cited article. The plugin checks evidence and citation IDs. The remaining
omissions above show why that check cannot establish completeness.
[Recorded live replies](../eval/results/live_milano_0.1.5.json)

Two archived questions have geographic limitations exposed by the new data. The original
Parco Nord control is outside the park polygon. The Chiaravalle control intersects the
R.02 park zone referencing PTC art. 26, while its historical answer key used art. 25. The
historical replay retains its original inputs so the results can be compared.

## Verification

The live audit compared the 20 original points and four additional controls. All 22 in-city
geology controls agreed on the main class between the municipal and regional feeds. Linate
and Vanzago exercised the outside-city check. The sampled flood comparison checked
H/M/L and the numeric return-period field at Lambro. The municipal M label contains
`TR 100` while its numeric field and the regional value are 200 at that point. The dock
uses the regional PGRA fields for flood findings.
[Tav. G.15 layer 19](https://gisportal.comune.milano.it/federated/rest/services/PGT/Milano_2030_PGT_Vigente_Tavola_G15/MapServer/19)

| Control point | Latitude, longitude | Verified result |
|---|---|---|
| Duomo building | 45.46414, 9.19192 | Municipal NAF and geology II |
| Duomo square | 45.46420, 9.19000 | Regional historic-area hit, with municipal NAF absent at the point |
| North Milan, original park control | 45.52810, 9.20500 | Municipal ADR, outside the mapped park |
| Parco Nord positive control | 45.52937179, 9.21261924 | Park hit in both the municipal and regional layers |
| Niguarda | 45.52000, 9.18500 | Municipal ARU and geology II |
| Chiaravalle | 45.41700, 9.23500 | R.02 references PTC Article 26, geology IIIc+IIId |
| Lambro | 45.46500, 9.25600 | PGRA H/M/L, 10/200/500 years, regional R3 |
| Vanzago | 45.51970, 8.97360 | Outside Milan. Separate regional positive control for Natura 2000 |

Reproduce with the project dev requirements installed.

```sh
python -m pytest -q
python -m ruff check core scripts tests plugin eval
python -m bandit -r plugin core -q
python eval/verify_milan_points.py
python eval/replay_prompt.py
python scripts/build_plugin.py
```

`eval/replay_prompt.py --source PATH` runs the same replay against a checkout of
`v0.1.4`. The generated plugin ZIP uses the existing QGIS plugin ID and carries the
new runtime boundary and source registry. Research evidence and review scripts stay
in the repository.

To exercise the exact ZIP against live map layers, run the smoke script with QGIS's
bundled Python. The checked runtime was QGIS 3.44.15 LTR on Windows.

```sh
python eval/smoke_qgis.py dist/norme_milano-0.1.5.zip
```

## Independent release review

On the same 10-point rubric, Astra High scored 0.1.4 at 7.8, the first 0.1.5 candidate
at 8.6, and the final build at 8.8. The second round fixed the official publication links
in answers and checked the live response schema and stale-task behavior. The final review
confirmed 190 passing tests, clean Ruff and Bandit checks, and an archive matching its
runtime sources. The packaged QGIS run passed all seven map clicks and the external
answer-link check. The local detect-secrets scan returned zero findings.
