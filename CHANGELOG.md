# Changelog

## 0.1.0 (first experimental release)

- Click a point in Milan: PGT zoning category and constraints are read live from Regione Lombardia's public ArcGIS map services (28 layers: PGT mosaic, landscape sensitivity, geological feasibility, PGRA flood hazard and risk, Natura 2000, regional parks).
- 7 PGT/PTC documents mapped to the constraints: Piano delle Regole, Piano dei Servizi, Documento di Piano, PTC Parco Agricolo Sud Milano with Allegato A, geological and seismic norms, landscape contents. Each article is shown as governing, general or candidate, with its full text.
- Optional Q&A in Italian or English with Gemini (your own API key, kept in the QGIS authentication database) or a local Ollama model. The model answers only from the retrieved articles; citations outside them are removed and flagged.
- Works without any LLM provider (provider "None"): only the map-service queries use the network.
- Guidance only, not legal advice. The plugin queries the clicked point, not a whole parcel.
