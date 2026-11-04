# qgis-norme-milano

A QGIS plugin that shows which planning rules apply at a point in Milan. Click the map and it lists:

- the PGT zone at that point and the NTA (Norme Tecniche di Attuazione) articles mapped to it,
- constraints from the Natura 2000 and PGRA flood-risk layers,
- optionally, an answer to a free-text question, written by an LLM (Gemini or a local Ollama model) and citing only the retrieved articles.

> **Status:** early development (Phase 0: checking the data sources). See [docs/implementation-plan.md](docs/implementation-plan.md).

> **Disclaimer:** answers are guidance only, not legal advice. In v1 the plugin queries a single point, not a whole parcel, so a parcel crossing two zones can be misreported.

## Layout

```
plugin/   QGIS plugin shell (metadata.txt, map tool, dock panel, settings)
core/     QGIS-free library: map-service queries, retrieval, LLM calls, prompts
data/     articles.json, zone_map.yaml, constraint_map.yaml
scripts/  parse_nta.py (split the NTA PDF), probe_services.py (Phase 0 checks)
eval/     evaluation questions and runner
tests/    pytest tests for core/
docs/     implementation plan and the original proposal (Persian)
```

## Development

The core library uses only the Python standard library at runtime, so it works inside QGIS on Windows without installing packages. Development tools are listed in `requirements-dev.txt`.

```bash
pip install -r requirements-dev.txt
pytest
python scripts/probe_services.py 45.4642 9.1900
```

## Licence

GPL-2.0-or-later (required by the official QGIS plugin repository). See [LICENSE](LICENSE).
