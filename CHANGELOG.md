# Changelog

## 0.1.6

- Redesigned dock: one card per constraint with a colour chip and family, a "more" toggle for values, articles grouped into governing and general, and a clearer status line. A one-time early-access notice is built in but stays off until a sign-up page is set.
- Queries 18 more Tav. R.02 layers (public-transport accessibility, GFU, in itinere plans, mandatory implementation plans, PLIS, art. 136 Navigli, urban green and others) and identifies Tav. R.03 (NAF intervention types, ADR and ARU morphology, services exemption under PS art. 11), R.05 and R.06 (administrative, heritage and landscape constraints, with the law named in each record) and R.07-R.08 (airport risk, noise, radar and obstacle limits).
- Each whole-map layer rule is tied to the name the Comune publishes; a renamed layer is shown as "verify" instead of with a wrong article, and the weekly live check fails on a rename.
- Context is no longer governing: the regional TUC record when the Comune's zone layers answered, geology articles on flood findings when the municipal geology class is known, city-wide airport obstacle surfaces, and the proposed PLIS Martesana (a candidate).
- A map that does not answer gets a "not checked: unknown, not absent" card. Each click finishes within 30 s, one worker per request so a slow host cannot block the others, and only network errors, 408, 429 and 5xx are retried, once.
- Answers: numbers not found in the cited articles are listed in a warning (whole numbers, in each answer's language, ignoring article references and dates). The caption says when a fallback model answered. The sources line shows when the norms were last checked and warns after 90 days.

## 0.1.5

- Added Milan's live Tav. R.02 findings for NAF, ADR, ARU and both regional parks, and its Tav. G.17 geological classes and article references.
- Check the municipal boundary locally before querying map services. Preserve the regional fallback and mark conflicting or insufficient evidence as uncertain.
- Added official map and document links. Show article PDF page ranges and excerpts that can be located in the text sent to the model.
- Improved multipart Q&A prompts and retrieval for explicitly named planning documents. Discard a pending answer when the user clicks a new point.
- Documented the live municipal versus regional comparison and the limits of the historical answer evaluation. [Release notes](docs/norme-milano-0.1.5.md)

## 0.1.4

- No longer flagged experimental.
- Keeps 8 BM25 extra articles when no article is mapped to the clicked point.

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
