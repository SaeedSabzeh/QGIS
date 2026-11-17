"""Zone-table lookup plus a small BM25 search over the PGT norms (Phase 2).

Standard library only. `lookup` turns the layer hits from `services.query_all` into findings using
data/zone_map.json and data/constraint_map.json (generated from the YAML by scripts/build_maps.py).
`search` is BM25 over data/articles.json, which holds several documents (data/documents.json):
ids look like "PR-art-45", "PS-art-11", "CG-art-45", "DPA1-sec-21". `retrieve` combines both:
mapped articles first, then search hits from normative documents before explanatory ones.
"""

import datetime
import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

from . import services

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
ID_PREFIX = "PR-art-"      # a bare article number means the Piano delle Regole

# ---------------------------------------------------------------------------------------------
# Data loading (cached)
# ---------------------------------------------------------------------------------------------
_cache = {}


def _load_json(name, data_dir=None):
    path = Path(data_dir or DATA_DIR) / name
    key = str(path)
    if key not in _cache:
        with open(path, encoding="utf-8") as fh:
            _cache[key] = json.load(fh)
    return _cache[key]


def load_articles(data_dir=None):
    return _load_json("articles.json", data_dir)


def load_maps(data_dir=None):
    """Return (zone_map, constraint_map) dicts."""
    return _load_json("zone_map.json", data_dir), _load_json("constraint_map.json", data_dir)


def load_documents(data_dir=None):
    """The document registry (data/documents.json) as {doc code: row}; {} when absent."""
    try:
        rows = _load_json("documents.json", data_dir)
    except (OSError, ValueError):
        return {}
    return {r["doc"]: r for r in rows}


def article_id(ref):
    """Normalise an article reference to an id: 45, "45" -> "PR-art-45"; ids such as
    "PS-art-11" or "DPA1-sec-21" are returned as they are."""
    if isinstance(ref, int):
        return ID_PREFIX + str(ref)
    s = str(ref).strip()
    if s.isdigit():
        return ID_PREFIX + str(int(s))
    return s


def articles_by_id(data_dir=None):
    return {a["id"]: a for a in load_articles(data_dir)}


def cite_label(a):
    """"Piano dei Servizi \u2013 art. 11" for an article record (degrades to "art. 11")."""
    name = a.get("doc_name") or a.get("doc") or ""
    lab = a.get("label") or ("art. %s" % a.get("number", ""))
    return ("%s \u2013 %s" % (name, lab)) if name else lab


def ref_label(ref, data_dir=None):
    """Label of the record a reference points to (falls back to the id)."""
    aid = article_id(ref)
    a = articles_by_id(data_dir).get(aid)
    return cite_label(a) if a else aid


def sources_used(ids, data_dir=None):
    """One line naming the documents (with version) behind the given ids, for the disclaimers."""
    by_id, docs = articles_by_id(data_dir), load_documents(data_dir)
    seen = []
    for aid in ids:
        code = (by_id.get(article_id(aid)) or {}).get("doc")
        if code and code not in seen:
            seen.append(code)
    parts = []
    for code in seen:
        d = docs.get(code) or {}
        v = d.get("version_date")
        extra = {"PTC": ", 2000 text; later amendments are local, outside Milan", "DPA1": ", explanatory"}.get(code, "")
        name = d.get("name", code)
        if d.get("checked_on"):
            c = str(d["checked_on"])
            extra += ", checked on %s/%s/%s" % (c[8:10], c[5:7], c[:4])
            try:
                age = (datetime.date.today() - datetime.date.fromisoformat(c)).days
            except ValueError:
                age = 0
            if age > STALE_CHECK_DAYS:
                extra += ", over %d days ago: check for a newer text" % STALE_CHECK_DAYS
        parts.append("%s (%s%s)" % (name, v, extra) if v else name)
    return "; ".join(parts)


# ---------------------------------------------------------------------------------------------
# Layer -> map entry. A finding is produced for every hit of every layer listed here.
# ---------------------------------------------------------------------------------------------
# layer name (core.services.SERVICES) -> (map file, key in that file)
LAYER_RULES = {
    **{name: ("zone", name) for name in services.MUNICIPAL_ZONES},
    "milano_geology": ("zone", "fattibilita_geologica"),
    "milano_accessibility": ("zone", "milano_accessibility"),
    "milano_rigen_ambientale": ("zone", "milano_rigen_ambientale"),
    "milano_piazze": ("zone", "milano_piazze"),
    "milano_nodi": ("zone", "milano_nodi"),
    "milano_nuclei_esterni": ("zone", "milano_nuclei_esterni"),
    "milano_gfu": ("zone", "milano_gfu"),
    "milano_pedonale": ("zone", "milano_pedonale"),
    "milano_in_itinere": ("zone", "milano_in_itinere"),
    "milano_pa_obbligatori": ("zone", "milano_pa_obbligatori"),
    "milano_agricoltura": ("zone", "milano_agricoltura"),
    "milano_ticinello": ("zone", "milano_ticinello"),
    "milano_plis_lambro": ("zone", "milano_plis_lambro"),
    "milano_plis_martesana": ("zone", "milano_plis_martesana"),
    "milano_ers": ("zone", "milano_ers"),
    "milano_navigli_136": ("zone", "milano_navigli_136"),
    "milano_navigli_riapertura": ("zone", "milano_navigli_riapertura"),
    "milano_mobilita_nuova": ("zone", "milano_mobilita_nuova"),
    "milano_verde": ("zone", "milano_verde"),
    "milano_park_north": ("constraint", "parco_regionale"),
    "milano_park_south": ("constraint", "parco_regionale"),
    "pgt_naf": ("zone", "naf"),
    "pgt_previsioni_tuc": ("zone", "tuc"),
    "pgt_at": ("zone", "at"),
    "pgt_rigenerazione": ("zone", "rigenerazione"),
    "pgt_servizi": ("zone", "servizi"),
    "pgt_agricole": ("zone", "agricole"),
    "pgt_paesaggio": ("zone", "paesaggio"),
    "pgt_sensibilita": ("zone", "sensibilita"),
    "pgt_fattibilita_geo": ("zone", "fattibilita_geologica"),
    "natura2000_zsc": ("constraint", "natura2000_zsc_sic"),
    "natura2000_zps": ("constraint", "natura2000_zps"),
    "parchi_regionali": ("constraint", "parco_regionale"),
    "pgra_R1": ("constraint", "pgra_risk"),
    "pgra_R2": ("constraint", "pgra_risk"),
    "pgra_R3": ("constraint", "pgra_risk"),
    "pgra_R4": ("constraint", "pgra_risk"),
}
for _name in services.IDENTIFY:
    LAYER_RULES[_name] = ("identify", _name)
for _s in "HML":
    for _n in ("RP", "RSCM", "RSP", "ACL"):
        LAYER_RULES["pgra_%s_%s" % (_s, _n)] = ("constraint", "pgra_hazard")

# Attribute fields worth showing per map key (matched case-insensitively; blanks dropped).
KEY_FIELDS = {
    "milano_naf": ["nomeambito", "tipo"],
    "milano_adr": ["ambito", "nomeambito"],
    "milano_aru": ["ambito", "nomeambito"],
    "naf": ["COD_NUC"],
    "tuc": ["AMB_URB", "COD_DEST1", "DCOD_DEST1", "SPEC_DEST"],
    "at": ["AMB_TRAS", "NOME_AMB", "DFUN_PREV1"],
    "rigenerazione": ["CATEGORIA", "NOME_AMB"],
    "servizi": ["TIPO_SERV", "DTIPO_SERV", "STATO", "DSTATO", "LIV_TER"],
    "agricole": ["COD_AGR", "SPEC_AGR"],
    "paesaggio": ["COD_PAES", "TIPO_AMB", "DESCRIZION"],
    "sensibilita": ["CLASSE", "DESCRIZION"],
    "fattibilita_geologica": ["CLASSE", "DESCR_FATTIBILITA", "FATTORI_PERICOLO", "rif_norma"],
    "natura2000_zsc_sic": ["COD_SITO", "NOME_SITO"],
    "natura2000_zps": ["COD_ZPS", "NOME_ZPS"],
    "parco_regionale": ["NOME_PA", "NOME_ENTE", "DATTUA_PA", "nome"],
    "pgra_hazard": ["Codscenar", "Tritorno", "Nomeelidr", "Ambitoter"],
    "pgra_risk": ["Ris", "Danno", "CatUE", "Nomeelidr"],
}
ROMAN = {"I": "1", "II": "2", "III": "3", "IV": "4", "V": "5"}


def _get(attrs, name):
    """Case-insensitive attribute getter (the PGRA layers spell Codscenar/CodScen differently)."""
    if name in attrs:
        return attrs[name]
    low = name.lower()
    for k, v in attrs.items():
        if k.lower() == low:
            return v
    return None


def _blank(v):
    return v is None or (isinstance(v, str) and not v.strip())


def _key_values(key, attrs):
    out = {}
    for f in KEY_FIELDS.get(key, []):
        v = _get(attrs, f)
        if not _blank(v):
            out[f] = v.strip() if isinstance(v, str) else v
    scheda = _get(attrs, "SCHEDA_NEW")
    if isinstance(scheda, str) and scheda.startswith("http"):
        out["SCHEDA_NEW"] = scheda
    return out


def _union(*lists):
    seen, out = set(), []
    for lst in lists:
        for n in lst or []:
            if n not in seen:
                seen.add(n)
                out.append(n)
    return out


def _norm_value(v):
    s = str(v).strip()
    return ROMAN.get(s.upper(), s)


def _ids(lst):
    return [article_id(n) for n in lst or []]


PARCO_SUD = "parco agricolo sud milano"
MUNICIPAL_PARKS = {"milano_park_north": "Parco Nord Milano",
                   "milano_park_south": "Parco Agricolo Sud Milano"}
NORTH_PTC = "https://parconord.milano.it/wp-content/uploads/2019/09/Norme-Tecniche-di-Attuazione-PTC-Parco-Nord-Milano-2020.pdf"


def in_parco_sud(query_result):
    """True when a parchi_regionali hit of `query_result` is the Parco Agricolo Sud Milano."""
    layers = query_result.get("layers") or {}
    if layers.get("milano_park_south"):
        return True
    for attrs in layers.get("parchi_regionali") or []:
        name = _get(attrs, "NOME_PA")
        if isinstance(name, str) and name.strip().lower() == PARCO_SUD:
            return True
    return False


def _zone_finding(layer, key, entry, attrs, in_park=False):
    articles = _ids(entry.get("articles"))
    general = _ids(entry.get("general_articles"))
    explanatory = _ids(entry.get("explanatory_articles"))
    candidates = _ids(entry.get("candidate_articles"))
    why = entry.get("why", "")
    note = entry.get("note", "")
    verify = bool(entry.get("verify", False))
    matched = {}
    for field, table in (entry.get("by_value") or {}).items():
        raw = _get(attrs, field)
        if _blank(raw):
            continue
        sub = table.get(_norm_value(raw))
        if not sub:
            continue
        matched[field] = _norm_value(raw)
        articles = _union(articles, _ids(sub.get("articles")))
        general = _union(general, _ids(sub.get("general_articles")))
        explanatory = _union(explanatory, _ids(sub.get("explanatory_articles")))
        candidates = _union(candidates, _ids(sub.get("candidate_articles")))
        if sub.get("why"):
            why = (why + " " + sub["why"]).strip()
        if sub.get("note"):
            note = (note + " " + sub["note"]).strip()
        verify = verify or bool(sub.get("verify", False))
    park = entry.get("inside_parco_sud")
    if in_park and park:
        # inside the Parco Agricolo Sud Milano the PTC candidates named here are promoted
        articles = _union(articles, _ids(park.get("articles")))
        general = _union(general, _ids(park.get("general_articles")))
        explanatory = _union(explanatory, _ids(park.get("explanatory_articles")))
        if park.get("why"):
            why = (why + " " + park["why"]).strip()
        if park.get("note"):
            note = (note + " " + park["note"]).strip()
        verify = verify or bool(park.get("verify", False))
    general = [n for n in general if n not in articles]
    explanatory = [n for n in explanatory if n not in articles and n not in general]
    candidates = [n for n in candidates
                  if n not in articles and n not in general and n not in explanatory]
    return {
        "layer": layer, "category": key, "source": "zone_map",
        "label": entry.get("description", key),
        "values": _key_values(key, attrs), "matched_values": matched,
        "articles": articles, "general_articles": general, "explanatory_articles": explanatory,
        "candidate_articles": candidates,
        "why": why, "note": note, "verify": verify, "external_rule": entry.get("external_rule"),
    }


CONSTRAINT_LABELS = {
    "natura2000_zsc_sic": "Natura 2000: ZSC/SIC",
    "natura2000_zps": "Natura 2000: ZPS",
    "parco_regionale": "Parco regionale",
    "pgra_hazard": "Pericolosita alluvioni (PGRA)",
    "pgra_risk": "Rischio alluvioni (PGRA)",
}


def _constraint_finding(layer, key, entry, attrs):
    articles = _ids(entry.get("articles"))
    why = entry.get("why", "")
    note = entry.get("note", "")
    general = _ids(entry.get("general_articles"))
    values = _key_values(key, attrs)
    matched = {}
    by_value = entry.get("by_value") or {}
    hit = False
    for field, table in by_value.items():
        raw = _get(attrs, field)
        sub = None if _blank(raw) else table.get(str(raw).strip())
        if not sub:
            continue
        hit = True
        matched[field] = str(raw).strip()
        articles = _union(articles, _ids(sub.get("articles")))
        general = _union(general, _ids(sub.get("general_articles")))
        why = (why + " " + sub.get("why", "")).strip()
        note = (note + " " + sub.get("note", "")).strip()
    if by_value and not hit and entry.get("unmatched_note"):
        note = (note + " " + entry["unmatched_note"]).strip()
    mapping = entry.get("hazard_mapping")
    if mapping:
        scen = _get(attrs, "Codscenar") or _get(attrs, "CodScen")
        if _blank(scen):  # fall back to the layer name pgra_H_RP -> H
            parts = layer.split("_")
            scen = parts[1] if len(parts) >= 3 else None
        scen = str(scen).strip().upper() if scen else None
        if scen in mapping:
            hz = mapping[scen]
            matched["Codscenar"] = scen
            values["nta_scenario"] = hz.get("nta_scenario")
            hz_ids = _ids(hz.get("articles"))
            general = _union(general, [n for n in articles if n not in hz_ids])
            articles = hz_ids
            note = (note + " " + entry.get("hazard_mapping_note", "")).strip()
    return {
        "layer": layer, "category": key, "source": "constraint_map",
        "label": CONSTRAINT_LABELS.get(key, layer), "values": values, "matched_values": matched,
        "articles": articles, "general_articles": [n for n in general if n not in articles],
        "explanatory_articles": [], "candidate_articles": [],
        "why": why, "note": note, "verify": bool(entry.get("verify", False)),
        "external_rule": entry.get("external_rule"),
    }


def _apsfr_finding(layer, attrs):
    vals = {}
    for f in ("nameAPSFR", "relZoneId", "specHazTyp"):
        if not _blank(attrs.get(f)):
            vals[f] = attrs[f].strip() if isinstance(attrs[f], str) else attrs[f]
    return {
        "layer": layer, "category": "pgra_apsfr", "source": "constraint_map",
        "label": "Area a potenziale rischio significativo di alluvione (APSFR)",
        "values": vals, "matched_values": {}, "articles": [], "general_articles": [],
        "explanatory_articles": [], "candidate_articles": [], "why": "", "verify": False,
        "external_rule": None,
        "note": "Context only: see the PGRA hazard and risk findings for the rules.",
    }


def _add_geology_constraint(finding, geo):
    """Attach the geology constraint's external rule and class note to the zone finding."""
    if not geo:
        return
    finding["external_rule"] = geo.get("external_rule")
    cls = finding["matched_values"].get("CLASSE")
    roman = {v: k for k, v in ROMAN.items()}.get(cls)
    cnote = ((geo.get("classes") or {}).get(roman) or {}).get("note")
    if cnote:
        finding["note"] = (finding["note"] + " " + cnote).strip()


def _municipal_attributes(layer, attrs):
    if layer in MUNICIPAL_PARKS:
        return dict(attrs, NOME_PA=MUNICIPAL_PARKS[layer])
    if layer == "milano_geology":
        # G.17 supplies the subclass and the native article/subparagraph reference.
        code = str(_get(attrs, "classi_new") or "")
        cls = re.match(r"IV|III|II|I|V", code.upper())
        label = str(_get(attrs, "legenda") or "")
        return dict(attrs, CLASSE=label.split(" - ", 1)[0] if label else (cls[0] if cls else None),
                    DESCR_FATTIBILITA=_get(attrs, "legenda"), FATTORI_PERICOLO=code)
    return attrs


def _apply_municipal_context(finding, layer, municipal_zones, layers, errors):
    if layer in services.MUNICIPAL_ZONES and (
        len(municipal_zones) > 1 or any(key in errors for key in services.MUNICIPAL_ZONES)
    ):
        finding["candidate_articles"] = finding["articles"]
        finding["articles"] = []
        finding["verify"] = True
        finding["note"] = (
            "Multiple municipal zone categories intersect here. Compare their boundaries on Tav. R.02."
            if len(municipal_zones) > 1 else
            "Some municipal zone layers were unavailable. Verify the detailed category on Tav. R.02."
        )
    if layer == "pgt_previsioni_tuc" and municipal_zones:
        finding["candidate_articles"] = []
        finding["note"] = "The regional TUC finding provides broad context. See the Comune's Tav. R.02 finding for the detailed category."
    if layer == "pgt_naf" and "milano_naf" in layers:
        finding["candidate_articles"] = finding["articles"]
        finding["articles"] = []
        finding["verify"] = True
        finding["note"] = "The regional layer identifies the broader historic area. Verify this point on the Comune's Tav. R.02 and R.03."


def lookup(query_result, data_dir=None):
    """Turn `query_all` output into a list of findings (one per hit)."""
    zone_map, constraint_map = load_maps(data_dir)
    zone_layers = zone_map.get("layers", {})
    constraints = constraint_map.get("constraints", {})
    findings = []
    layers = query_result.get("layers") or {}
    errors = query_result.get("errors") or {}
    municipal_zones = [layer for layer in services.MUNICIPAL_ZONES if layers.get(layer)]
    municipal_parks = {name.casefold() for layer, name in MUNICIPAL_PARKS.items() if layers.get(layer)}
    in_park = in_parco_sud(query_result)
    for layer, hits in layers.items():
        if (layer == "pgt_naf" and municipal_zones) or (
            layer == "pgt_fattibilita_geo" and layers.get("milano_geology")
        ):
            continue
        for attrs in hits or []:
            if layer == "parchi_regionali" and str(_get(attrs, "NOME_PA")).strip().casefold() in municipal_parks:
                continue
            attrs = _municipal_attributes(layer, attrs)
            if layer == "pgra_APSFR":
                findings.append(_apsfr_finding(layer, attrs))
                continue
            rule = LAYER_RULES.get(layer)
            if not rule:
                continue
            src, key = rule
            if src == "identify":
                f = _identify_finding(layer, (zone_map.get("identify") or {}).get(key), attrs)
                if f:
                    findings.append(f)
                continue
            if src == "zone":
                entry = zone_layers.get(key)
                if entry:
                    f = _zone_finding(layer, key, entry, attrs, in_park)
                    _apply_municipal_context(f, layer, municipal_zones, layers, errors)
                    if key == "fattibilita_geologica":
                        _add_geology_constraint(f, constraints.get("geologia"))
                    findings.append(f)
            else:
                entry = constraints.get(key)
                if entry:
                    f = _constraint_finding(layer, key, entry, attrs)
                    if layer in MUNICIPAL_PARKS:
                        f["verify"] = False
                    if _get(attrs, "NOME_PA") == MUNICIPAL_PARKS["milano_park_north"]:
                        f["document_url"] = NORTH_PTC
                    if layer == "milano_park_south":
                        for number in re.findall(r"\bArt\.\s*(25|26|27)\b", str(_get(attrs, "nome")), re.I):
                            f["articles"] = _union(f["articles"], [f"PTC-art-{number}"])
                            f["why"] += " Tav. R.02 identifies the park zone and references this PTC article."
                    findings.append(f)
    findings.extend(_identify_failures(errors, zone_map))
    _flag_previous_plan(findings)
    if layers.get("milano_geology"):
        _demote_flood_geology(findings)
    if (all(name in layers for name in services.MUNICIPAL_ZONES)
            and not any(name in errors for name in services.MUNICIPAL_ZONES)):
        _demote_regional_tuc(findings, municipal_zones)
    findings = _dedupe(findings)
    for finding in findings:
        finding["map_url"] = (services.SERVICES.get(finding["layer"])
                              or services.IDENTIFY.get(finding["layer"]))
    return findings


STALE_CHECK_DAYS = 90
MILANO_2030 = "20200205"  # Milano 2030 in force since 05/02/2020
GEOLOGY_ARTICLES = {"PR-art-%d" % n for n in (43, 44, 45, 46)} | {
    "CG-art-%d" % n for n in (43, 44, 45, 46)}
INTERNAL_KEYS = ("objectid", "shape", "fid", "id", "st_", "globalid", "_layer")


def _identify_finding(layer, entry, attrs):
    """One finding for a layer of a whole-map identify, or None for labels and drawing aids."""
    if not entry:
        return None
    name = str(attrs.get("_layerName") or "").strip()
    if not name or any(word in name.lower() for word in entry.get("skip", [])):
        return None
    layer_id = str(attrs.get("_layerId"))
    override = (entry.get("layers") or {}).get(layer_id)
    renamed = bool(override and override.get("name")
                   and not name.casefold().startswith(override["name"].casefold()))
    # A layer with its own rule uses only that rule; the map default is for the other layers.
    rule = dict(override if override and not renamed else entry.get("default") or {})
    rule.pop("name", None)
    rule["description"] = "%s - %s" % (entry.get("map", layer), name)
    f = _zone_finding(layer, layer, rule, attrs)
    f["values"] = {k: v for k, v in attrs.items()
                   if not str(k).lower().startswith(INTERNAL_KEYS) and not _blank(v)
                   and str(v).strip() not in ("---", "Null", "0")}
    if renamed:
        # nothing is governing until a human confirms what the renamed layer is
        f["verify"] = True
        f["candidate_articles"] = _union(_union(f.get("articles", []), f.get("candidate_articles", [])),
                                         override.get("articles", []))
        f["articles"] = []
        f["note"] = ("The Comune's service now names layer %s \"%s\" (expected \"%s\"), so the "
                     "article could not be confirmed. " % (layer_id, name, override["name"])
                     + f.get("note", "")).strip()
    reference = _legal_reference(attrs)
    if reference and not f.get("external_rule"):
        f["external_rule"] = {"text": reference, "verify": False}
    return f


LEGAL_KEYS = ("rifleg", "rifart", "rif_norme", "legenda")
LAW_RE = re.compile(r"\b(?:d\.?\s?lgs|legge|l\.?\s?r|lr|dgr|d\.?g\.?r|dpr|d\.?p\.?r|r\.?d|dm|d\.?m|"
                    r"art)\b\.?", re.IGNORECASE)


def _legal_reference(attrs):
    """The law a vincolo record names itself (e.g. "Dlgs. 3-04-2006 n. 152"), if any. Legend
    labels count only when they name a law; a decree date follows the law it belongs to."""
    parts, decree = [], None
    for key, value in attrs.items():
        name = str(key).lower()
        text = "" if _blank(value) else str(value).strip()
        if not text or text in ("---", "Null", "0"):
            continue
        if name == "data_decr":
            decree = text
        elif name in LEGAL_KEYS and LAW_RE.search(text) and text not in parts:
            parts.append(text)
    if parts and decree:
        parts.append("decreto del %s" % decree)
    return "; ".join(parts)


def _identify_failures(errors, zone_map):
    """A visible card for each whole map that did not answer: its vincoli are unknown."""
    out = []
    for layer, error in errors.items():
        entry = (zone_map.get("identify") or {}).get(layer)
        if layer not in services.IDENTIFY or not entry:
            continue
        rule = {"description": "%s - not checked" % entry.get("map", layer), "verify": True,
                "note": ("This map did not answer (%s), so its constraints at this point are "
                         "unknown, not absent. Check the map before relying on the result."
                         % str(error)[:80])}
        f = _zone_finding(layer, layer, rule, {})
        f["values"] = {}
        out.append(f)
    return out


def _demote_regional_tuc(findings, municipal_zones):
    """The regional TUC record is context, not the rule, once the Comune's own zone layers
    answered: either the municipal zone (NAF/ADR/ARU) governs, or there is none here.
    Called only when the municipal zone layers answered (no hit is then a real answer)."""
    if municipal_zones:
        note = ("The Comune's own zone on Tav. R.02 (%s) governs here; this regional TUC record "
                "is context. " % ", ".join(z.removeprefix("milano_").upper() for z in municipal_zones))
    else:
        note = ("No municipal zone (NAF, ADR, ARU) on Tav. R.02 here, so this regional TUC record "
                "gives context only; check the Comune's maps for the zone. ")
    for f in findings:
        if f["layer"] == "pgt_previsioni_tuc" and f.get("articles"):
            f["general_articles"] = _union(f["articles"], f.get("general_articles", []))
            f["articles"] = []
            f["note"] = (note + f.get("note", "")).strip()


def _dedupe(findings):
    """Drop repeated findings. Whole-map (identify) hits of the same layer are merged, keeping
    the values of the first; other layers are merged only when their values are identical."""
    seen, out = {}, []
    for f in findings:
        values = () if f["layer"] in services.IDENTIFY else tuple(
            sorted(map(str, (f.get("values") or {}).items())))
        key = (f["layer"], f.get("label"), tuple(f.get("articles", [])), values)
        if key not in seen:
            seen[key] = f
            out.append(f)
    return out


def _flag_previous_plan(findings):
    """Regional transformation-area records dated before Milano 2030 are not current rules."""
    for f in findings:
        if f["layer"] != "pgt_at":
            continue
        match = re.search(r"_(\d{8})_", str((f.get("values") or {}).get("SCHEDA_NEW") or ""))
        if match and match.group(1) < MILANO_2030:
            d = match.group(1)
            f["verify"] = True
            f["note"] = ("This regional record comes from the previous plan (scheda dated "
                         "%s/%s/%s). Milano 2030, in force since 05/02/2020, may treat this area "
                         "differently: check Tav. R.02 and the Documento di Piano. "
                         % (d[6:], d[4:6], d[:4]) + f.get("note", "")).strip()


def _demote_flood_geology(findings):
    """With the Comune's own geology class (Tav. G.17), flood findings' geology articles are
    context, not the governing rule."""
    for f in findings:
        if not f["layer"].startswith("pgra_"):
            continue
        moved = [a for a in f.get("articles", []) if a in GEOLOGY_ARTICLES]
        if moved:
            f["articles"] = [a for a in f["articles"] if a not in GEOLOGY_ARTICLES]
            f["general_articles"] = _union(f.get("general_articles", []), moved)
            f["note"] = ("The Comune's geology class (Tav. G.17) decides which geology article "
                         "applies here. " + f.get("note", "")).strip()


# Role order: directly governing articles first, then general, explanatory (non-normative), then
# candidates.
ROLES = ("articles", "general_articles", "explanatory_articles", "candidate_articles")


def article_provenance(findings):
    """Ordered {article id: [{layer, category, role}, ...]} across findings, deduplicated."""
    prov = {}
    for role in ROLES:
        for f in findings:
            for n in f.get(role, []):
                prov.setdefault(article_id(n), []).append(
                    {"layer": f["layer"], "category": f["category"], "role": role})
    return prov


# ---------------------------------------------------------------------------------------------
# BM25
# ---------------------------------------------------------------------------------------------
STOPWORDS = frozenset(
    "a ad al alla alle allo agli ai anche che chi ci col come con cui da dal dalla dalle dei del "
    "della delle dello degli di e ed era essere gli ha hanno ho i il in io la le lo loro ma mi "
    "nel nella nelle nello negli nei no non o per piu quale quali quando se si sia sono su sul "
    "sulla sulle sui suo sua suoi tra fra tu un una uno va vi voi cosa dove puo possono "
    "the of and to is are an for on what which can how do does be at it with by".split()
)


def _strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def _stem(tok):
    # crude: drop up to two trailing vowels, keeping at least 4 characters
    for _ in range(2):
        if len(tok) > 4 and tok[-1] in "aeio":
            tok = tok[:-1]
    return tok


ROMAN_TOKENS = frozenset(["i", "ii", "iii", "iv", "v"])


def tokenize(text, stem=True, loose=False):
    """Lowercase, strip accents, split on non-alphanumerics, drop stopwords, crude stemming.

    "classe III" also yields a joined token "class_iii", so the class number is not lost. With
    `loose` (queries) the numeral need not follow "classe" directly.
    """
    raws = re.findall(r"[a-z0-9]+", _strip_accents(text.lower()))
    has_class = any(r in ("classe", "classi") for r in raws)
    out = []
    prev = None
    for raw in raws:
        if raw in ROMAN_TOKENS and (prev in ("classe", "classi") or (loose and has_class)):
            out.append("class_" + raw)
        prev = raw
        if raw in STOPWORDS or (len(raw) < 2 and not raw.isdigit()):
            continue
        out.append(_stem(raw) if stem and not raw.isdigit() else raw)
    return out


class BM25:
    """Okapi BM25 over a list of (doc_id, text)."""

    def __init__(self, docs, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.ids = [d[0] for d in docs]
        self.tf = [Counter(tokenize(d[1])) for d in docs]
        self.len = [sum(c.values()) for c in self.tf]
        self.avg = (sum(self.len) / len(self.len)) if self.len else 0.0
        df = Counter()
        for c in self.tf:
            df.update(c.keys())
        n = len(docs)
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def search(self, query, k=5):
        q = tokenize(query, loose=True)
        scores = []
        for i, c in enumerate(self.tf):
            s = 0.0
            for t in q:
                f = c.get(t)
                if f:
                    norm = 1 - self.b + self.b * self.len[i] / (self.avg or 1.0)
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * norm)
            if s > 0:
                scores.append((self.ids[i], s))
        scores.sort(key=lambda x: (-x[1], x[0]))
        return scores[:k]


def article_search_text(a):
    # the title counts three times: a hit in the title is a strong signal
    return " ".join([a.get("title") or ""] * 3 + [a.get("capo") or "", a.get("text") or ""])


def build_index(articles=None, data_dir=None):
    articles = articles if articles is not None else load_articles(data_dir)
    # records that merely reproduce another document (CG = PR art. 42-51) are not searched:
    # they would crowd the real article out of the hits. They stay citable when mapped.
    return BM25([(a["id"], article_search_text(a)) for a in articles
                 if not a.get("duplicate_of")])


_index_cache = {}


def search(query, k=5, index=None, data_dir=None):
    """Return [(article id, score)] for the top `k` articles."""
    if index is None:
        key = str(Path(data_dir or DATA_DIR))
        if key not in _index_cache:
            _index_cache[key] = build_index(data_dir=data_dir)
        index = _index_cache[key]
    return index.search(query, k)


# BM25 extras kept by default. With no mapped article the search hits are the only evidence and
# the prompt is far below its budget, so more of them are kept (eval 2026-11-05: gold at rank 7-8).
EXTRAS_K = 5
EXTRAS_K_UNMAPPED = 8
QUERY_TERMS = (
    (r"\bfloor[- ]area (?:index|ratio)\b|\bFAR\b", "indice edificabilità territoriale"),
    (r"consolidated urban fabric", "tessuto urbano consolidato"),
    (r"public service areas|service provision", "dotazione servizi territoriali"),
    (r"public[- ]transport accessibility", "accessibilità trasporto pubblico"),
    (r"change of use", "mutamento destinazione uso"),
    (r"building setbacks|setback distances", "distanze confini fabbricati"),
    (r"flood hazard|flood risk", "pericolosità alluvionale PGRA"),
    (r"basements?|below[- ]ground floors?", "piani interrati seminterrati"),
    (r"groundwater|water table", "falda acquifera fattibilità geologica"),
    (r"\bnavigli[oi]\b|\bcanals?\b", "navigli reticolo idrografico fasce di rispetto sponde"),
    (r"edificabilit[aà] territoriale massim[oa]|maximum (?:floor[- ]area|FAR)",
     "criteri di densità accessibilità trasporto pubblico indice massimo"),
)
DOCUMENT_NAMES = (
    ("PR", r"\bPR\b|piano delle regole"),
    ("PS", r"\bPS\b|piano dei servizi"),
    ("DP", r"\bDP\b|documento di piano"),
    ("PTC", r"\bPTC\b|piano territoriale di coordinamento"),
)


def _question_context(keywords, question):
    """Keep explicit documents/references and add Italian terms for English searches."""
    text = question or keywords
    additions = [terms for pattern, terms in QUERY_TERMS if re.search(pattern, text, re.I)]
    docs, refs = [], []
    for doc, aliases in DOCUMENT_NAMES:
        if re.search(aliases, text, re.I):
            docs.append(doc)
        for number in re.findall(rf"(?:{aliases})[\s,–-]+art(?:icolo)?[.\s-]*(\d+)\b", text, re.I):
            refs.append(f"{doc}-art-{number}")
    return " ".join([keywords, *additions]), docs, refs


def extras_k(n_mapped, k=None):
    """Number of BM25 extras retrieve() keeps: `k` when given, else by whether anything is mapped."""
    if k is not None:
        return k
    return EXTRAS_K if n_mapped else EXTRAS_K_UNMAPPED


def retrieve(query_result, question=None, k=None, index=None, data_dir=None, findings=None,
             original_question=None):
    """Mapped articles first, then up to `k` BM25 extras from `question` (no duplicates).

    The question should already be Italian keywords (see prompts.keywords_prompt). `k` bounds
    only the extras: every mapped article is kept. When `k` is None it is EXTRAS_K with mapped
    articles and EXTRAS_K_UNMAPPED without (see extras_k). Extras come from all documents; hits of
    normative documents rank before those of explanatory ones (score order inside each group).
    Returns a dict: findings, mapped, extras, ids (ordered), provenance ({id: [...]}; extras
    are tagged role "bm25" with the score).
    """
    if findings is None:
        findings = lookup(query_result, data_dir)
    prov = article_provenance(findings)
    mapped = list(prov)
    k = extras_k(len(mapped), k)
    extras = []
    if question and question.strip():
        query, requested_docs, references = _question_context(question, original_question)
        by_id = articles_by_id(data_dir)
        limit = len(by_id) if requested_docs else 4 * k + len(mapped)
        hits = search(query, k=limit, index=index, data_dir=data_dir)
        # stable partition: normative first (the sort is stable, the hits are score-ordered)
        hits = sorted(hits, key=lambda h: not by_id.get(h[0], {}).get("normative", True))
        named = [(aid, 0) for aid in references if aid in by_id]
        for doc in requested_docs:
            match = next((hit for hit in hits if by_id.get(hit[0], {}).get("doc") == doc), None)
            if match:
                named.append(match)
        for aid, score in named + hits:
            if aid in prov or len(extras) >= k:
                continue
            extras.append(aid)
            prov[aid] = [{"layer": None, "category": None, "role": "bm25",
                          "score": round(score, 3)}]
    return {"findings": findings, "mapped": mapped, "extras": extras,
            "ids": mapped + extras, "provenance": prov}
