# QGIS Regulations Plugin — Implementation Plan

Date: 5 November 2026
Based on: "پروژه افزونه هوشمند ضوابط QGIS.docx"

## Changes to the original plan

1. **Look up articles by zone code, not by search.** When you click a point, the map service returns a zone code from the PGT. Write a small table by hand that maps each zone code to its NTA articles, and another that maps each constraint layer (Natura 2000, flood risk) to the rule that applies. Text search then only adds extra articles. The table makes the citations reliable and is what makes the project stand out from the existing plugins.
2. **No-key mode can't answer free-text questions in English.** The NTA is in Italian, so keyword search on an English question finds almost nothing. Without a key, the plugin only shows the constraints and the full text of the mapped articles. Free-text questions need the LLM, which can rewrite the question in Italian before searching.
3. **"Parcel" is really a point in v1.** You query the point you click, and a parcel that crosses two zones would be misreported. Say this in the UI. Proper parcel geometry from the national cadastre can come in v2.
4. **2–3 weeks is optimistic.** Getting the current NTA, building the zone table and running the evaluation are slow work. Plan for 4–5 weeks part-time.
5. **The licensing risk is smaller than the original plan makes it sound.** The plugin queries the region's services live; it doesn't redistribute their data. Under Italian copyright law (art. 5, L. 633/1941), official acts of public bodies aren't covered by copyright, so shipping the NTA text is probably fine. This isn't legal advice, and the email to the region costs nothing, so still send it.
6. **The free Gemini tier has a privacy catch.** Google can use free-tier prompts to improve its products. Add one line about this in settings. Store the key in QGIS's encrypted auth manager (QgsAuthManager), not in plain settings.
7. **Support both QGIS 3 LTR and QGIS 4 (Qt6).** Import only from `qgis.PyQt` and declare Qt6 support in `metadata.txt`. Check which version is the current LTR before installing.

## Phases

### Phase 0: check the data before writing plugin code (2–3 days)
- [ ] Install the current QGIS LTR.
- [ ] Find the NTA currently in force: the 2019 text plus the 2024 amendment. Check both Milan's own PGT portal and PGTWEB.
- [ ] Take 3–5 test points in Milan and query each service with `/MapServer/{layer}/query` (point geometry, `spatialRel=esriSpatialRelIntersects`, `outFields=*`, `f=json`). Services: the PGT zoning map (Tavola delle previsioni), Natura 2000 and PGRA flood risk.
- [ ] For each service, write down the layer IDs, field names, coordinate system (probably EPSG:32632) and which field holds the zone code.
- **Go/no-go:** if no service returns a zone code that can be linked to NTA articles, change the v1 scope before building anything.

### Phase 1: rules text and lookup tables (3–4 days)
- [ ] Offline script (PyMuPDF) that splits the NTA at each `Art. N` and saves `articles.json` with id, title, text, source and version date.
- [ ] `zone_map.yaml`: zone code → articles.
- [ ] `constraint_map.yaml`: layer → applicable rule and a short note.
- v1 covers only the Milan NTA plus Natura 2000 and flood risk. Regional law 12/2005 and the model building code (RET) wait for v1.1.

### Phase 2: core library, no QGIS dependency (4–5 days)
- [ ] `services.py`: point queries to the map services.
- [ ] `retrieval.py`: zone-table lookup, plus BM25 search (implement it in about 50 lines rather than adding a dependency).
- [ ] `llm.py`: Gemini and Ollama called over plain REST, with no SDKs. Installing pip packages into QGIS on Windows is painful, so keep dependencies at zero.
- [ ] Prompt: answer in Italian and English, as JSON with `answer` and `cited_articles`. Reject or flag any cited article that wasn't among the retrieved articles.
- [ ] Command-line entry point: `python -m core.ask <lat> <lon> "question"`.
- [ ] pytest tests.

### Phase 3: plugin shell (3–4 days)
- [ ] Map tool that captures clicks and converts the point to the services' coordinate system.
- [ ] Network calls through `QgsTask` and `QgsNetworkAccessManager`, so the UI doesn't freeze and QGIS proxy settings are respected.
- [ ] Dock panel with three parts: constraints found, articles (expandable full text), question box (enabled only with a key).
- [ ] Settings and first-run dialog: link to create a Gemini key, Gemini/Ollama choice, "Test connection" button, privacy note.
- [ ] Permanent disclaimer: answers are guidance, not legal advice.

### Phase 4: evaluation (2–3 days)
- [ ] 40 questions written from the NTA, each tagged with its correct article(s).
- [ ] Metrics:
  - Retrieval recall@5: is the correct article in the top 5?
  - Citation accuracy
  - Answer correctness: judged by hand, or by an LLM with a rubric
  - Constraint correctness: 20 points checked against the official map viewer
- [ ] Run in both no-key and Gemini modes. The results table goes in the README.

### Phase 5: release (2 days)
- [ ] README, GIF or 1-minute video.
- [ ] GitHub Actions workflow for lint, tests and building the plugin zip (qgis-plugin-ci).
- [ ] GPL-2.0+ licence (required by the official QGIS plugin repository).
- [ ] Upload to plugins.qgis.org as experimental.
- [ ] Email the region about data licensing: sit_rl@regione.lombardia.it, sitpianificazione@regione.lombardia.it

## Repo layout

```
qgis-norme-milano/
  plugin/        metadata.txt, __init__.py, main.py, map_tool.py, dock.py, settings.py
  core/          services.py, retrieval.py, llm.py, prompts.py
  data/          articles.json, zone_map.yaml, constraint_map.yaml
  scripts/       parse_nta.py, probe_services.py
  eval/          questions.yaml, run_eval.py
  tests/
```

## Order of work

Phase 0 decides whether the rest holds up, so start with `probe_services.py` on the Milan test points, then `parse_nta.py`.

## Timeline

About 17–23 working days in total, which is roughly 4–5 weeks part-time.
