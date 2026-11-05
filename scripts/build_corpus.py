"""Build the multi-document corpus: data/articles.json + data/documents.json.

Usage: python scripts/build_corpus.py [--check]

Every source PDF in data/raw/ is described once in REGISTRY (doc code, title, file, version,
normative or not). Article ids are "<DOC>-art-N" for documents split at "art. N" headings
(PR, PS, DP, PTC, CG) and "<DOC>-sec-N" for documents split at headed sections (CGS seismic
annex, DPA1 landscape annex; N is the running section number, the printed number is kept in
"section"). The pure splitting logic is `split_articles` (scripts/parse_nta.py) and
`split_sections` below; both take plain text with pages separated by form feeds.

Needs PyMuPDF (dev-time only). Run from anywhere.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import parse_nta as P  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT_ARTICLES = ROOT / "data" / "articles.json"
OUT_DOCS = ROOT / "data" / "documents.json"

FF = chr(12)

# ---------------------------------------------------------------------------------------------
# Registry. `name` is the short label shown next to an article ("Piano dei Servizi - art. 11").
# ---------------------------------------------------------------------------------------------
REGISTRY = [
    {
        "doc": "PR", "kind": "articles", "normative": True,
        "name": "Piano delle Regole",
        "title": "Piano delle Regole – Norme di attuazione, PGT Milano 2030",
        "file": "PR_Norme_Attuazione_20251204.pdf",
        "version_date": "2025-12-04",
        "version_note": "In-force text: adopted DCC 43 of 12/06/2025, approved DCC 93 of "
                        "04/12/2025, BURL n. 5 of 28/01/2026. Replaces the text of 2023 (DCC 100 "
                        "of 19/12/2022).",
    },
    {
        "doc": "PS", "kind": "articles", "normative": True,
        "name": "Piano dei Servizi",
        "title": "Piano dei Servizi – Norme di attuazione, PGT Milano 2030",
        "file": "PS_Norme_Attuazione_Catalogo_20230308.pdf",
        "version_date": "2022-12-19",
        "version_note": "In force, modified after DCC 100 of 19/12/2022 (BURL n. 6 of 05/02/2020 "
                        "for the original approval). The Catalogo dei servizi (table of service "
                        "categories) that follows art. 14 in the PDF is not part of the corpus.",
    },
    {
        "doc": "DP", "kind": "articles", "normative": True,
        "name": "Documento di Piano",
        "title": "Documento di Piano – Norme di attuazione, PGT Milano 2030",
        "file": "DP_Norme_Attuazione_202002051_bis_vig.pdf",
        "version_date": "2019-10-14",
        "version_note": "Approved DCC 34 of 14/10/2019, BURL Serie Avvisi e Concorsi n. 6 of "
                        "05/02/2020. The closing 'Appendice' (referral to the Piano delle Regole "
                        "Titolo IV) is not part of the corpus.",
    },
    {
        "doc": "PTC", "kind": "articles", "normative": True,
        "name": "PTC Parco Agricolo Sud Milano",
        "title": "Parco Agricolo Sud Milano – Piano Territoriale di Coordinamento, "
                 "Norme Tecniche di Attuazione",
        "file": "PASM_PTC_DGR_7_818_20000803.pdf",
        "version_date": "2000-08-03",
        "version_note": "DGR 7/818 of 03/08/2000 (BURL 2nd suppl. straordinario n. 38 of "
                        "21/09/2000). The two later amendments were checked: DGR 8/4516 of "
                        "03/04/2007 (Tav. 26, one area in Colturano) and DGR 8/10833 of "
                        "16/12/2009 (new art. 30 bis and zoning, fontanile Rile in Settala) are "
                        "local changes outside Milan, so the 2000 text stands for Milan. No "
                        "consolidated text is published. The annexes A-D of the NTA are not "
                        "part of the corpus.",
    },
    {
        "doc": "CG", "kind": "articles", "normative": True,
        "name": "Componente geologica (norme)",
        "title": "Componente geologica, idrogeologica e sismica – Allegato 1: norme geologiche "
                 "di piano (art. 42-51)",
        "file": "1_CG_GAll01_Relazione_geologica_20200205.pdf",
        "version_date": "2020-02-05",
        "duplicate_of": "PR",
        "version_note": "Chapter 7 'Norme geologiche di piano' of the Relazione illustrativa "
                        "(BURL n. 6 of 05/02/2020). Art. 42-51 reproduce art. 42-51 of the Piano "
                        "delle Regole as of 2020: where the two differ, the current Piano delle "
                        "Regole text (PR) prevails. The explanatory chapters 1-6 are not part of "
                        "the corpus.",
    },
    {
        "doc": "CGS", "kind": "sections", "normative": True,
        "name": "Componente sismica",
        "title": "Componente sismica – Allegato 7: relazione illustrativa e norme specifiche",
        "file": "CG_GAll07_Relazione e norme_20200205.pdf",
        "version_date": "2020-02-05",
        "version_note": "BURL n. 6 of 05/02/2020. Two sections (soil category of foundation; "
                        "liquefaction analysis).",
    },
    {
        "doc": "DPA1", "kind": "sections", "normative": False,
        "name": "Documento di Piano – Allegato 1 (contenuti paesaggistici)",
        "title": "Documento di Piano – Allegato 1: Contenuti paesaggistici del piano, "
                 "Infrastrutture verdi e blu e Rete Ecologica Comunale",
        "file": "DP_DAll01_Contenuti_Paesaggistici_REC_202002051_bis_vig.pdf",
        "version_date": "2019-10-14",
        "version_note": "Explanatory / guidance report (prose, not articles), BURL n. 6 of "
                        "05/02/2020. The catalogue table 'Edifici e ambiti di rilevanza "
                        "storico-architettonica' and the bibliography are not part of the corpus.",
    },
]


# ---------------------------------------------------------------------------------------------
# Section splitter (headed prose)
# ---------------------------------------------------------------------------------------------
LONE_NUM = re.compile(r"^\d+(\.\d+)+$")


def split_sections(text, headings, prefix, begin_re=None, furniture=P.FURNITURE,
                   furniture_re=None, drop_re=None, item_re=P.ITEM_RE, dehyphen=True,
                   prose=True):
    """Split prose into sections at the given headings.

    `headings`: ordered list of dicts {key, title, rx, [lines], [parent], [skip]}; `rx` matches
    the first line of the heading (searched in order, after the previous heading); `lines` is how
    many lines the heading occupies (default 1); `skip` discards the text up to the next heading;
    `parent` is the key of a heading whose title becomes "capo". Sections with an empty body
    are not emitted. Returns dicts shaped like split_articles' (id, number = running index,
    section = printed key, title, titolo, capo, text, pages).
    """
    lines = list(P._page_lines(text, furniture, furniture_re, drop_re))
    cursor = 0
    if begin_re:
        for i, (_, l) in enumerate(lines):
            if begin_re.match(l):
                cursor = max(i - 2, 0)
                break
    found = []
    for h in headings:
        rx = re.compile(h["rx"])
        for i in range(cursor, len(lines)):
            if rx.match(lines[i][1]):
                found.append((i, h))
                cursor = i + 1
                break
        else:
            raise ValueError("heading not found: %s %s" % (h["key"], h["title"]))
    titles = {h["key"]: h for h in headings}
    out = []
    for n, (i, h) in enumerate(found):
        end = found[n + 1][0] if n + 1 < len(found) else len(lines)
        if h.get("skip"):
            continue
        body_start = i + h.get("lines", 1)
        body = [l for _, l in lines[body_start:end]]
        while body and (not body[-1] or LONE_NUM.match(body[-1])):
            body.pop()
        while body and not body[0]:
            body.pop(0)
        if not body:
            continue
        pages = [x for x, l in lines[body_start:end] if l]
        parent = titles.get(h.get("parent"))
        out.append({
            "section": h["key"], "title": h["title"], "text": P._paragraphs(
                body, item_re, dehyphen, prose),
            "capo": ("%s %s" % (parent["label"], parent["title"])) if parent else None,
            "titolo": h.get("titolo"), "pages": [pages[0], pages[-1]] if pages else [0, 0],
        })
    for k, s in enumerate(out, start=1):
        s["id"] = "%s-sec-%d" % (prefix, k)
        s["number"] = k
    return out


def _h(key, title, rx, parent=None, lines=1, skip=False, label=None, titolo=None):
    return {"key": key, "title": title, "rx": rx, "parent": parent, "lines": lines, "skip": skip,
            "label": label or key + ".", "titolo": titolo}


PART1 = "Contenuti paesaggistici del piano"
PART2 = "Infrastrutture verdi e blu e Rete Ecologica Comunale"


def dpa1_headings():
    t = PART1
    r = PART2
    return [
        _h("1", "Premessa", r"^1\.\s+Premessa", titolo=t),
        _h("1.2", "Elaborati inerenti la componente paesaggistica del PGT", r"^1\.2\s+Elaborati",
           parent="1", titolo=t),
        _h("2", "Il quadro di riferimento", r"^2\.\s+Il quadro di riferimento", titolo=t),
        _h("2.1", "Piano Paesaggistico Regionale (PPR)", r"^2\.1\s+Piano Paesaggistico",
           parent="2", titolo=t),
        _h("2.2", "Piano Territoriale Regionale d’Area dei Navigli Lombardi",
           r"^2\.2\s+Piano Territoriale Regionale", parent="2", titolo=t),
        _h("2.3", "Piano Territoriale di Coordinamento Provinciale (PTCP)",
           r"^2\.3\s+Piano Territoriale di Coordinamento Provinciale", parent="2", titolo=t),
        _h("2.4", "Piano Territoriale di Coordinamento del Parco Regionale Agricolo Sud Milano",
           r"^2\.4\s+Piano Territoriale di Coordinamento del Parco", parent="2", titolo=t),
        _h("3", "I caratteri culturali e naturali del paesaggio milanese",
           r"^3\.\s+I caratteri culturali", titolo=t),
        _h("3.1", "La matrice storica", r"^3\.1\s+La matrice storica", parent="3", titolo=t),
        _h("3.2", "Elementi strutturali, naturali e culturali", r"^3\.2\s+Elementi strutturali",
           parent="3", titolo=t),
        _h("3.3", "Rilevanza ed integrità del paesaggio (criteri e metodologia)",
           r"^3\.3\s+Rilevanza", parent="3", titolo=t),
        _h("4", "L’ambito di prevalenza del paesaggio urbano", r"^4\.\s+L.ambito di prevalenza",
           titolo=t),
        _h("4.1", "Gli elementi strutturanti del paesaggio urbano", r"^4\.1\s+Gli elementi",
           parent="4", titolo=t),
        _h("4.2", "Le unità riconosciute del paesaggio urbano", r"^4\.2\s+Le unità riconosciute",
           parent="4", titolo=t),
        _h("5", "L’ambito dei parchi regionali e agrario e le contiguità di paesaggio",
           r"^5\.\s+L.ambito dei parchi", lines=2, titolo=t),
        _h("5.1", "Le caratteristiche degli Ambiti dei parchi regionali e del paesaggio agrario",
           r"^5\.1\s+Le caratteristiche", parent="5", titolo=t),
        _h("6", "L’ambito “naturalistico” del corso del Lambro", r"^6\.\s+L.ambito .naturalistico",
           titolo=t),
        _h("6.1", "Ambito del corso del Lambro", r"^6\.1\s+Ambito del corso", parent="6", titolo=t),
        _h("7", "Le tutele culturali e paesaggistiche", r"^7\.\s+Le tutele culturali", titolo=t),
        _h("7.1", "La percezione collettiva del paesaggio", r"^7\.1\s+La percezione",
           parent="7", titolo=t),
        _h("8", "Sintesi percettiva", r"^8\.\s+Sintesi percettiva", titolo=t),
        _h("9", "La carta del paesaggio e la carta della sensibilità paesaggistica dei luoghi",
           r"^9\.\s+La carta del paesaggio", lines=2, titolo=t),
        _h("9.1", "Definizione dei livelli di sensibilità", r"^9\.1\s+Definizione dei livelli",
           parent="9", titolo=t),
        _h("9.2", "Criteri applicativi", r"^9\.2\s+Criteri applicativi", parent="9", titolo=t),
        _h("10", "Bibliografia (omitted) and building catalogue (omitted)",
           r"^10\.\s+Bibliografia", skip=True),
        _h("REC 1", "Premessa", r"^1\.\s+Premessa", label="REC 1.", titolo=r),
        _h("REC 2", "Schema di Rete Ecologica Comunale – Tavola D03",
           r"^2\.\s+Schema di Rete Ecologica", label="REC 2.", titolo=r),
        _h("REC 3", "Infrastrutture Verdi e Blu e Rete Ecologica Comunale – Tavola S03",
           r"^3\.\s+Infrastrutture Verdi e Blu", lines=2, label="REC 3.", titolo=r),
        _h("REC 3.1", "Infrastrutture per la realizzazione di reti ambientali",
           r"^3\.1\s+Infrastrutture per la realizzazione", parent="REC 3", label="REC 3.1",
           titolo=r),
        _h("REC 3.2", "Infrastrutture per la riqualificazione ambientale e la resilienza degli "
           "ambiti costruiti", r"^3\.2\s+Infrastrutture per la riqualificazione", lines=2,
           parent="REC 3", label="REC 3.2", titolo=r),
        _h("REC 3.3", "Infrastrutture per l’incremento delle prestazioni ecologiche "
           "dell’ambiente urbano", r"^3\.3\s+Infrastrutture per l.incremento", lines=2,
           parent="REC 3", label="REC 3.3", titolo=r),
        _h("REC 3.4", "Spazi di appoggio ed elementi funzionali alle Infrastrutture Verdi e Blu",
           r"^3\.4\s+Spazi di appoggio", parent="REC 3", label="REC 3.4", titolo=r),
        _h("REC 3.5", "Parchi da consolidare e connettere attraverso le Infrastrutture Verdi e "
           "Blu in prospettiva del Parco Metropolitano", r"^3\.5\s+Parchi da consolidare",
           lines=2, parent="REC 3", label="REC 3.5", titolo=r),
    ]


def cgs_headings():
    t = "Relazione illustrativa e norme specifiche"
    return [
        _h("1.1", "Categoria del suolo di fondazione", r"^Categoria del suolo di fondazione\s*$",
           titolo=t),
        _h("1.2", "Analisi del fenomeno della liquefazione",
           r"^Analisi del fenomeno della liquefazione\s*$", titolo=t),
    ]


# ---------------------------------------------------------------------------------------------
# Per-document parsers
# ---------------------------------------------------------------------------------------------
GENERIC_FURNITURE = {
    "norme di attuazione", "piano delle regole", "piano dei servizi", "documento di piano",
    "contenuti paesaggistici del piano", "componenti geologica, idrogeologica e sismica",
    "relazione illustrativa e norme geologiche di piano",
}
LABEL_DROP = re.compile(r"^(Piano dei Servizi|Documento di Piano|Norme di attuazione|"
                        r"Componenti Geologica, Idrogeologica e Sismica)$")
PS_STOP = re.compile(r"^CATEGORIA$")        # start of the Catalogo table
DP_STOP = re.compile(r"^Appendice$")

PTC_DROP = re.compile(r"^(\d{1,3}|2º Suppl\. Straordinario.*|Bollettino Ufficiale della Regione "
                      r"Lombardia|[—–-]{2,}.*)$")
PTC_ART = re.compile(r"^Art\.\s*(\d+)$")
PTC_ITEM = re.compile(r"^(\d+\.|[a-z]{1,2}\)|\d+\)|•|–)(\s|$)")
PTC_ANNEX_ITEM = re.compile(r"^(Comparto \d|Sub-comparto|Comuni interessati|Orientamenti e indirizzi:|% minima)")
PTC_STOP = re.compile(r"^ALLEGATO b\)")
PTC_TITLE_FIX = {
    26: "Territori agricoli e verde di cintura urbana – ambito dei piani di cintura urbana",
    27: "Territori di collegamento tra città e campagna – fruizione",
    36: "Sub-zone parchi urbani – Impianti sportivi e ricreativi esistenti",
    40: "Emergenze storico-architettoniche. Manufatti della storia agraria",
}


def fix_ptc_text(t):
    """Undo the BURL font encoding: ligatures and accents typed as vowel + ` or ´."""
    for a, b in (("ﬁ", "fi"), ("ﬂ", "fl"), ("ﬀ", "ff"), ("ﬃ", "ffi"), ("ﬄ", "ffl"),
                 ("ı`", "ì"), ("ı´", "í")):
        t = t.replace(a, b)
    grave = dict(zip("aeiouAEIOU", "àèìòùÀÈÌÒÙ"))
    acute = dict(zip("aeiouAEIOU", "áéíóúÁÉÍÓÚ"))
    t = re.sub(r"([aeiouAEIOU])`", lambda m: grave[m.group(1)], t)
    t = re.sub(r"([aeiouAEIOU])´", lambda m: acute[m.group(1)], t)
    # Titolo / Capo headings: "Titolo II\nNORME GENERALI\nDEL PARCO\nArt. 15"
    def ctx(m):
        title = " ".join(x.strip() for x in m.group(3).strip().split("\n"))
        return "\n%s %s – %s\nArt." % (m.group(1).upper(), m.group(2), title)
    t = re.sub(r"\n(Titolo|Capo) ([IVX]+)\n((?:(?!Art\.|Titolo|Capo)[^\n]+\n)+?)Art\.(?=\s)", ctx, t)
    return t


def parse_pr(text):
    return P.split_articles(text, prefix="PR")


def parse_ps(text):
    return P.split_articles(text, prefix="PS", stop_re=PS_STOP, drop_re=LABEL_DROP)


def parse_dp(text):
    return P.split_articles(text, prefix="DP", stop_re=DP_STOP, drop_re=LABEL_DROP)


def parse_ptc(text):
    arts = P.split_articles(
        fix_ptc_text(text), prefix="PTC", art_re=PTC_ART, drop_re=PTC_DROP, item_re=PTC_ITEM,
        dehyphen=True, stop_re=PTC_STOP, block_titles=True)
    for a in arts:
        a["title"] = PTC_TITLE_FIX.get(a["number"], P._join(a["title"].split("\n"), True))
        a["title"] = re.sub(r"(\w)- (?=[a-zàèéìòù])", r"\1", a["title"])
        # sub-title naming the sector plan ("Piano di settore «Fruizione»") is not the title
        a["title"] = re.sub(r"\s+Piano di settore «.*$", "", a["title"])
    annex = _ptc_annex_a(fix_ptc_text(text))
    if annex:
        arts.append(annex)
    return arts


def _ptc_annex_a(text):
    """Allegato A of the NTA ("orientamenti e indirizzi" of the 5 cintura-urbana comparti):
    the guidance art. 26 refers to. Returned as one record, id PTC-all-A."""
    lines = list(P._page_lines(text, P.FURNITURE, None, PTC_DROP))
    start = end = None
    for i, (_, l) in enumerate(lines):
        if l == "TERRITORI AGRICOLI E VERDE DI CINTURA URBANA" and start is None:
            start = i + 1
        elif start is not None and re.match(r"^ALLEGATO B$", l):
            end = i
            break
    if start is None or end is None:
        return None
    body = [l for _, l in lines[start:end]]
    pages = [p for p, l in lines[start:end] if l]
    return {
        "id": "PTC-all-A", "number": None, "label": "all. A",
        "title": "Territori agricoli e verde di cintura urbana: orientamenti e indirizzi per "
                 "la formazione dei Piani di cintura urbana (comparti 1-5)",
        "titolo": "ALLEGATI ALLE NORME TECNICHE DI ATTUAZIONE", "capo": None,
        "text": P._paragraphs(body, PTC_ANNEX_ITEM, True, False), "pages": [pages[0], pages[-1]],
    }


CG_START = "7. Norme geologiche di piano"


def parse_cg(text):
    cut = text.rfind("\n" + CG_START)
    if cut < 0:
        return []
    text = FF * text.count(FF, 0, cut) + text[cut:]
    arts = P.split_articles(text, prefix="CG", first=42, drop_re=LABEL_DROP)
    for a in arts:
        a["titolo"] = a["titolo"] or "Norme geologiche di piano"
    return arts


def parse_cgs(text):
    return split_sections(
        text, cgs_headings(), "CGS", furniture_re=re.compile(r"^0809-03-01-01-00_"))


def parse_dpa1(text):
    return split_sections(
        text, dpa1_headings(), "DPA1",
        begin_re=re.compile(r"^La componente paesaggistica del territorio comunale"),
        furniture={"documento di piano", "contenuti paesaggistici del piano"})


PARSERS = {"PR": parse_pr, "PS": parse_ps, "DP": parse_dp, "PTC": parse_ptc, "CG": parse_cg,
           "CGS": parse_cgs, "DPA1": parse_dpa1}


def _label(rec, kind):
    if rec.get("label"):
        return rec["label"]
    if kind == "articles":
        return "art. %s" % rec["number"]
    return "sez. %s" % rec.get("section", rec["number"])


def build_records(docs=None, raw=RAW, extract=P.extract_text):
    """Parse every document of REGISTRY. Returns (articles, registry rows with counts)."""
    articles, registry = [], []
    for d in REGISTRY:
        if docs and d["doc"] not in docs:
            continue
        text = extract(Path(raw) / d["file"])
        text = text.replace("\xad", "")
        recs = PARSERS[d["doc"]](text)
        for r in recs:
            r["text"] = r["text"].replace("\xa0", " ").strip()
            articles.append({
                "id": r["id"], "doc": d["doc"], "doc_name": d["name"], "normative": d["normative"],
                **({"duplicate_of": d["duplicate_of"]} if d.get("duplicate_of") else {}),
                "number": r["number"], "label": _label(r, d["kind"]),
                **({"section": r["section"]} if "section" in r else {}),
                "title": r["title"], "titolo": r.get("titolo"), "capo": r.get("capo"),
                "text": r["text"], "source": d["title"], "source_file": d["file"],
                "version_date": d["version_date"], "pages": r["pages"],
            })
        registry.append({**d, "count": len(recs)})
    return articles, registry


def main(argv):
    articles, registry = build_records()
    for row in registry:
        print("%-5s %3d records  %s" % (row["doc"], row["count"], row["file"]))
    OUT_ARTICLES.write_text(json.dumps(articles, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    OUT_DOCS.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print("%d records -> %s, registry -> %s" % (len(articles), OUT_ARTICLES, OUT_DOCS))


if __name__ == "__main__":
    main(sys.argv)
