# Changelog

## 0.1.3

- Faster answers when Gemini is overloaded. A model that times out or answers 503 gets at most one quick retry (1-2 s), then the plugin moves to the next model. Requests time out after 20 s (45 s for the last model), and one question waits about 65 s at most (10 s more for the optional keyword step). A `Retry-After` longer than 5 s now means "use the next model" instead of waiting. The timeout is enforced in the QGIS network path too (transfer timeout plus a watchdog that aborts the blocking call).
- The dock status line shows progress while waiting ("Trying gemini-3.8-flash...", "gemini-3.8-flash busy, trying gemini-3.5-flash..."). `python -m core.ask` prints the same lines to stderr.
- Answers render as formatted text (bold, italic, lists, headings, code) instead of raw markdown. The converter escapes all HTML first, so model output can never inject markup. The prompt now says light markdown is fine.

## 0.1.2

- Contact email in metadata.txt changed to an address that can receive the plugins.qgis.org confirmation mail.
- Removed the deprecated `supportsQt6` flag: plugins.qgis.org now reads QGIS 4 support from `qgisMaximumVersion=4.99`.

## 0.1.1

- Easier Gemini key setup: no master password needed. The key is stored encrypted in the QGIS password store when it is available and a master password is already set; otherwise it falls back silently to the plugin settings in your QGIS profile (plain text, with a note under the field). GEMINI_API_KEY from the environment is used when nothing is stored. "Remove stored key" clears every store.
- Security scan cleanups: URL scheme checks before network calls (https, or http to localhost only) and narrower exception handling.

## 0.1.0 (first experimental release)

- Click a point in Milan: PGT zoning category and constraints are read live from Regione Lombardia's public ArcGIS map services (28 layers: PGT mosaic, landscape sensitivity, geological feasibility, PGRA flood hazard and risk, Natura 2000, regional parks).
- 7 PGT/PTC documents mapped to the constraints: Piano delle Regole, Piano dei Servizi, Documento di Piano, PTC Parco Agricolo Sud Milano with Allegato A, geological and seismic norms, landscape contents. Each article is shown as governing, general or candidate, with its full text.
- Optional Q&A in Italian or English with Gemini (your own API key, kept in the QGIS authentication database) or a local Ollama model. The model answers only from the retrieved articles; citations outside them are removed and flagged.
- Works without any LLM provider (provider "None"): only the map-service queries use the network.
- Guidance only, not legal advice. The plugin queries the clicked point, not a whole parcel.
