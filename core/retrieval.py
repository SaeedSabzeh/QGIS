"""Zone-table lookup plus a small BM25 search over the PGT norms (Phase 2).

Standard library only. `lookup` turns the layer hits from `services.query_all` into findings using
data/zone_map.json and data/constraint_map.json (generated from the YAML by scripts/build_maps.py).
`search` is BM25 over data/articles.json, which holds several documents (data/documents.json):
ids look like "PR-art-45", "PS-art-11", "CG-art-45", "DPA1-sec-21". `retrieve` combines both:
mapped articles first, then search hits from normative documents before explanatory ones.
"""

import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

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
        extra = {"PTC": ", without later amendments", "DPA1": ", explanatory"}.get(code, "")
        name = d.get("name", code)
        parts.append("%s (%s%s)" % (name, v, extra) if v else name)
    return "; ".join(parts)


# ---------------------------------------------------------------------------------------------
# Layer -> map entry. A finding is produced for every hit of every layer listed here.
# ---------------------------------------------------------------------------------------------
# layer name (core.services.SERVICES) -> (map file, key in that file)
LAYER_RULES = {
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
    "pgra_R1": ("constraint", "pgra_risk"),
    "pgra_R2": ("constraint", "pgra_risk"),
    "pgra_R3": ("constraint", "pgra_risk"),
    "pgra_R4": ("constraint", "pgra_risk"),
}
for _s in "HML":
    for _n in ("RP", "RSCM", "RSP", "ACL"):
        LAYER_RULES["pgra_%s_%s" % (_s, _n)] = ("constraint", "pgra_hazard")

# Attribute fields worth showing per map key (matched case-insensitively; blanks dropped).
KEY_FIELDS = {
    "naf": ["COD_NUC"],
    "tuc": ["AMB_URB", "COD_DEST1", "DCOD_DEST1", "SPEC_DEST"],
    "at": ["AMB_TRAS", "NOME_AMB", "DFUN_PREV1"],
    "rigenerazione": ["CATEGORIA", "NOME_AMB"],
    "servizi": ["TIPO_SERV", "DTIPO_SERV", "STATO", "DSTATO", "LIV_TER"],
    "agricole": ["COD_AGR", "SPEC_AGR"],
    "paesaggio": ["COD_PAES", "TIPO_AMB", "DESCRIZION"],
    "sensibilita": ["CLASSE", "DESCRIZION"],
    "fattibilita_geologica": ["CLASSE", "DESCR_FATTIBILITA", "FATTORI_PERICOLO"],
    "natura2000_zsc_sic": ["COD_SITO", "NOME_SITO"],
    "natura2000_zps": ["COD_ZPS", "NOME_ZPS"],
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


def _zone_finding(layer, key, entry, attrs):
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
    "pgra_hazard": "Pericolosita alluvioni (PGRA)",
    "pgra_risk": "Rischio alluvioni (PGRA)",
}


def _constraint_finding(layer, key, entry, attrs):
    articles = _ids(entry.get("articles"))
    why = entry.get("why", "")
    note = entry.get("note", "")
    general = []
    values = _key_values(key, attrs)
    matched = {}
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
            general = [n for n in articles if n not in hz_ids]
            articles = hz_ids
            note = (note + " " + entry.get("hazard_mapping_note", "")).strip()
    return {
        "layer": layer, "category": key, "source": "constraint_map",
        "label": CONSTRAINT_LABELS.get(key, layer), "values": values, "matched_values": matched,
        "articles": articles, "general_articles": general, "explanatory_articles": [],
        "candidate_articles": [],
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


def lookup(query_result, data_dir=None):
    """Turn `query_all` output into a list of findings (one per hit)."""
    zone_map, constraint_map = load_maps(data_dir)
    zone_layers = zone_map.get("layers", {})
    constraints = constraint_map.get("constraints", {})
    findings = []
    for layer, hits in (query_result.get("layers") or {}).items():
        for attrs in hits or []:
            if layer == "pgra_APSFR":
                findings.append(_apsfr_finding(layer, attrs))
                continue
            rule = LAYER_RULES.get(layer)
            if not rule:
                continue
            src, key = rule
            if src == "zone":
                entry = zone_layers.get(key)
                if entry:
                    f = _zone_finding(layer, key, entry, attrs)
                    if key == "fattibilita_geologica":
                        _add_geology_constraint(f, constraints.get("geologia"))
                    findings.append(f)
            else:
                entry = constraints.get(key)
                if entry:
                    findings.append(_constraint_finding(layer, key, entry, attrs))
    return findings


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


def retrieve(query_result, question=None, k=5, index=None, data_dir=None, findings=None):
    """Mapped articles first, then up to `k` BM25 extras from `question` (no duplicates).

    The question should already be Italian keywords (see prompts.keywords_prompt). `k` bounds
    only the extras: every mapped article is kept. Extras come from all documents; hits of
    normative documents rank before those of explanatory ones (score order inside each group).
    Returns a dict: findings, mapped, extras, ids (ordered), provenance ({id: [...]}; extras
    are tagged role "bm25" with the score).
    """
    if findings is None:
        findings = lookup(query_result, data_dir)
    prov = article_provenance(findings)
    mapped = list(prov)
    extras = []
    if question and question.strip():
        hits = search(question, k=4 * k + len(mapped), index=index, data_dir=data_dir)
        by_id = articles_by_id(data_dir)
        # stable partition: normative first (the sort is stable, the hits are score-ordered)
        hits = sorted(hits, key=lambda h: not by_id.get(h[0], {}).get("normative", True))
        for aid, score in hits:
            if aid in prov or len(extras) >= k:
                continue
            extras.append(aid)
            prov[aid] = [{"layer": None, "category": None, "role": "bm25",
                          "score": round(score, 3)}]
    return {"findings": findings, "mapped": mapped, "extras": extras,
            "ids": mapped + extras, "provenance": prov}
