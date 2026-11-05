# Testing the plugin in QGIS

The unit tests use a fake `qgis` package, so everything below has to be checked by hand in a real QGIS (3.28+ LTR with Qt5, and QGIS 4 with Qt6).

## Install

1. `python scripts/build_plugin.py` builds `dist/norme_milano-<version>.zip` (and a copy `dist/norme_milano.zip`) (plugin code, `core/`, and `data/articles.json`, `zone_map.json`, `constraint_map.json`).
2. QGIS: Plugins > Manage and Install Plugins > Install from ZIP > pick the zip > Install Plugin. Tick "Norme Milano" in the Installed tab (it is experimental: enable "Show also experimental plugins" in Settings if it does not appear).
3. A "Norme Milano" button appears in the plugins toolbar and a "Norme Milano" menu under Plugins. On first start the settings dialog opens once.

## Master password and key

1. Settings > Options > Authentication > set a master password (QGIS asks for it when the key is saved or read).
2. Plugins > Norme Milano > Settings. Choose Gemini, paste the key (create one at https://aistudio.google.com/apikey), press "Test connection", then OK.
3. The key is stored only in the encrypted auth database (Settings > Options > Authentication > Configurations shows "Norme Milano - Gemini API key"). Check that `QGIS3.ini` / `QGIS.ini` contains `norme_milano/authcfg=<id>` but not the key.
4. If no master password is set, saving the key must fail with a clear message and nothing is stored.
5. Ollama: choose Ollama, base URL `http://localhost:11434`, your model; "Test connection" should answer OK.

## Manual checklist

Use a project in any CRS (try EPSG:3857 and EPSG:32632) with an OSM basemap. Click the toolbar button, then click the map.

| Point (lat, lon) | Expected findings (docs/phase0-services.md) |
|---|---|
| Duomo 45.4642, 9.1900 | NAF 15, TUC AMB_URB 23 residential, sensitivity class 5, geology class II. No transformation area |
| Lambro 45.4650, 9.2560 | Transformation area 26 "L'Idroscalo (PCU4)", sensitivity 3, geology class III (IIIa+IIIc), PGRA flood hazard/risk layers |
| Chiaravalle 45.4170, 9.2350 | Transformation area 29 "Le Abbazie (PCU3)", landscape-value area (TIPO_AMB 502), sensitivity 4, geology class III (IIIc+IIId) |

For each click verify:

- [ ] A red cross marker appears at the click and the UI never freezes; the status line shows "Querying..." then the point.
- [ ] "Vincoli / Constraints found" lists the findings above with key values, `[VERIFY]` where a link is unconfirmed, and external-rule notes.
- [ ] "Articoli / Articles" lists the mapped articles with roles (governing / general / candidate); expanding one shows the full text.
- [ ] The footer (disclaimer EN/IT and the point-not-parcel limitation) is always visible.
- [ ] Clicking Vanzago-like points outside Milan or the sea gives "No planning constraint or zone found" without errors.
- [ ] With provider "none" the question box and Ask button are disabled with a hint; with Gemini + key, or Ollama, they are enabled.
- [ ] Ask "Quali distanze devo rispettare dai confini?" and "Can I add a floor?": the answer appears in Italian and English with the model name, cited articles, and (if the model cites an unsupplied article) a warning. The articles list marks cited ones.
- [ ] Wrong key: the status shows the HTTP error, findings stay on screen, no key text appears anywhere.
- [ ] Block one host (e.g. firewall the Natura 2000 host): other layers still show, the status lists the failed layers.
- [ ] Clicking quickly several times: only the last query is shown.
- [ ] Plugins > Manage > untick/reinstall the plugin: toolbar button, menu entries, dock and marker disappear; no errors in the Python console / Log Messages.

## Proxy behaviour

1. Settings > Options > Network > Use proxy for web access, with a proxy that logs requests (or one that refuses connections).
2. With a working proxy, the ArcGIS queries and the LLM request must go through it (see the proxy log). With a refusing proxy, the status line shows "All map services failed (network or proxy?)" and Ask reports a transient network error after its retries.
3. Optional: View > Panels > Log Messages > Network Logger shows each request (the `x-goog-api-key` header is visible only to the local user who enables it; turn it off afterwards).

## Qt6 / QGIS 4

Repeat the checklist on QGIS 4. Watch the Python console for `AttributeError` on enums (all enums are accessed scoped, e.g. `Qt.DockWidgetArea.RightDockWidgetArea`) and for `QAction` import problems (it is imported from `QtGui` first, then `QtWidgets`).
