"""Splitter variants used by scripts/build_corpus.py, on synthetic text (no PDF needed)."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_corpus as bc  # noqa: E402
from parse_nta import split_articles  # noqa: E402

FF = chr(12)

# "art. N Title" with a table of contents, a trailing catalogue and a running header
INLINE = FF.join([
    "Indice\n5\nart. 1 Uno\n5\nart. 2 Due\n",
    "Piano dei Servizi\nart. 1 Uno\n1. Primo testo.\nart. 2 Due con titolo che finisce con di\n"
    "lungo\n1. Secondo testo\ncontinua qui.\nPiano dei Servizi\n3. terzo.\n",
    "CATEGORIA\nBorsa\n",
])


def test_inline_titles_continue_stop_and_drop_labels():
    arts = split_articles(INLINE, prefix="PS", stop_re=bc.PS_STOP, drop_re=bc.LABEL_DROP)
    assert [a["id"] for a in arts] == ["PS-art-1", "PS-art-2"]
    assert arts[1]["title"] == "Due con titolo che finisce con di lungo"
    assert "Piano dei Servizi" not in arts[1]["text"] and "Borsa" not in arts[1]["text"]
    assert arts[1]["text"].startswith("1. Secondo testo continua qui.")


def test_numbering_can_start_above_one():
    text = "art. 42 Definizione\n1. Testo.\nart. 43 Classi\n1. Altro.\n"
    arts = split_articles(text, prefix="CG", first=42)
    assert [a["id"] for a in arts] == ["CG-art-42", "CG-art-43"]


PTC = FF.join([
    "Indice\nArt.\n1 – Effetti\n",
    "\nTitolo I\nDISPOSIZIONI GENERALI\nArt. 1\nAmbito e contenuti\ndel piano – PTC\n"
    "1. Il piano ha ef-\nfetti di piano paesi-\nstico.\n2 Bollettino\nArt. 2\nElaborati\n"
    "1. Elenco:\na) norme;\nb) tavole.\n7\n"
    "2º Suppl. Straordinario al n. 38 - 21 settembre 2000\n"
    "Bollettino Ufﬁciale della Regione Lombardia\n"
    "Capo I\nTerritori\nArt. 3\nTerritori agricoli\n1. Citta` e campagna.\n",
])


def test_block_titles_dehyphenation_and_context():
    arts = split_articles(
        bc.fix_ptc_text(PTC), prefix="PTC", art_re=bc.PTC_ART, drop_re=bc.PTC_DROP,
        item_re=bc.PTC_ITEM, dehyphen=True, block_titles=True)
    assert [a["id"] for a in arts] == ["PTC-art-1", "PTC-art-2", "PTC-art-3"]
    assert arts[0]["title"] == "Ambito e contenuti del piano – PTC"
    assert arts[0]["text"].startswith("1. Il piano ha effetti di piano paesistico.")
    assert arts[0]["titolo"] == "TITOLO I – DISPOSIZIONI GENERALI"
    assert arts[1]["text"].splitlines() == ["1. Elenco:", "a) norme;", "b) tavole."]
    assert arts[2]["capo"] == "CAPO I – Territori" and "Città e campagna" in arts[2]["text"]


def test_fix_ptc_text_accents_and_ligatures():
    assert bc.fix_ptc_text("e` nonche´ deﬁnito sı` citta`") == "è nonché definito sì città"


SECTIONS = FF.join([
    "Documento di Piano\n5\nIndice\n9. La carta\n9.1 Definizione dei livelli ... 46\n",
    "Contenuti paesaggistici del piano\n"
    "La componente paesaggistica e` il quadro.\n9. La carta del paesaggio e la\n"
    "sensibilita dei luoghi\n9.1 Definizione dei livelli\n"
    "Una frase lunga che prosegue sulla riga seguente per tutta la colonna di testo qui\n"
    "e finisce qui.\nSecondo paragrafo.\n9.2 Criteri\nTesto dei criteri.\n"
    "10. Bibliografia\n• libro uno\n1. Premessa\nTesto REC.\n",
])


def test_sections_skip_empty_parents_and_discarded_regions():
    heads = [
        bc._h("9", "La carta", r"^9\.\s+La carta", lines=2),
        bc._h("9.1", "Definizione dei livelli", r"^9\.1\s+Definizione", parent="9"),
        bc._h("9.2", "Criteri", r"^9\.2\s+Criteri", parent="9"),
        bc._h("10", "Bibliografia", r"^10\.\s+Bibliografia", skip=True),
        bc._h("REC 1", "Premessa", r"^1\.\s+Premessa", label="REC 1."),
    ]
    secs = bc.split_sections(
        SECTIONS, heads, "DPA1", begin_re=re.compile(r"^La componente paesaggistica"),
        furniture={"documento di piano", "contenuti paesaggistici del piano"})
    assert [s["id"] for s in secs] == ["DPA1-sec-1", "DPA1-sec-2", "DPA1-sec-3"]
    assert [s["section"] for s in secs] == ["9.1", "9.2", "REC 1"]       # "9" has no body
    assert secs[0]["capo"] == "9. La carta"
    assert secs[0]["text"].splitlines() == [
        "Una frase lunga che prosegue sulla riga seguente per tutta la colonna di testo qui "
        "e finisce qui.", "Secondo paragrafo."]
    assert "libro uno" not in " ".join(s["text"] for s in secs)


def test_registry_is_consistent():
    docs = [d["doc"] for d in bc.REGISTRY]
    assert docs[0] == "PR" and len(docs) == len(set(docs)) and set(docs) == set(bc.PARSERS)
    assert [d["doc"] for d in bc.REGISTRY if not d["normative"]] == ["DPA1"]
    for d in bc.REGISTRY:
        assert (ROOT / "data" / "raw" / d["file"]).suffix == ".pdf"
        assert d["kind"] in ("articles", "sections") and d["version_date"]
