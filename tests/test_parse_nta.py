import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from parse_nta import split_articles  # noqa: E402

SYNTHETIC = "\f".join([
    # page 1: table of contents (also has art. lines, must be skipped)
    "Norme di attuazione\n3\n"
    "TITOLO I – DISPOSIZIONI GENERALI\n7\n"
    "CAPO I – CONTENUTI\n7\n"
    "art. 1 Ambito di applicazione\n7\n"
    "art. 2 Natura e contenuti\n7\n"
    "art. 3 Disciplina\n8\n",
    # page 2: body start
    "Norme di attuazione\n1\n"
    "TITOLO I – DISPOSIZIONI GENERALI \n"
    "CAPO I – CONTENUTI \n"
    "art. 1 Ambito di applicazione \n"
    "1. Il Piano individua:\n"
    "a. le aree edificate;\n"
    "b. le aree destinate all’agricoltura.\n"
    "2. Il Piano disciplina altresì\n"
    "gli ambiti di rigenerazione.\n"
    "art. 2 Natura e contenuti\n"
    "1. Il Piano ha carattere vinco-\n",
    # page 3: furniture on top, hyphen/compound wrap, citation line that is not a heading
    "2\nPiano delle Regole\n"
    "lante e plano-\n"
    "volumetrico; si applicano le disposizioni di cui\n"
    "art. 13 comma 5 delle presenti norme.\n"
    "CAPO II – DISCIPLINA\n"
    "art. 3 Disciplina\n"
    "2.\n"
    "Testo dell’articolo tre.\n",
])


def test_toc_is_skipped_and_numbers_sequential():
    arts = split_articles(SYNTHETIC)
    assert [a["number"] for a in arts] == [1, 2, 3]
    assert [a["id"] for a in arts] == ["PR-art-1", "PR-art-2", "PR-art-3"]
    assert arts[0]["title"] == "Ambito di applicazione"
    assert arts[0]["pages"] == [2, 2]


def test_furniture_stripped_and_text_faithful():
    arts = split_articles(SYNTHETIC)
    all_text = "\n".join(a["text"] for a in arts)
    assert "Norme di attuazione" not in all_text
    assert "Piano delle Regole" not in all_text
    assert " " not in all_text
    assert arts[0]["text"].split("\n") == [
        "1. Il Piano individua:",
        "a. le aree edificate;",
        "b. le aree destinate all’agricoltura.",
        "2. Il Piano disciplina altresì gli ambiti di rigenerazione.",
    ]


def test_wrapped_lines_joined_across_pages_and_citation_not_heading():
    art2 = split_articles(SYNTHETIC)[1]
    # "vinco-" + "lante" is a hyphen at a line end followed by a lowercase word: kept as is
    # (compound hyphens are never guessed away); the "art. 13 comma 5" line is not a heading
    assert "plano-volumetrico" in art2["text"]
    assert "art. 13 comma 5 delle presenti norme." in art2["text"]
    assert art2["pages"] == [2, 3]


def test_titolo_and_capo_tracked():
    arts = split_articles(SYNTHETIC)
    assert arts[0]["titolo"] == "TITOLO I – DISPOSIZIONI GENERALI"
    assert arts[0]["capo"] == "CAPO I – CONTENUTI"
    assert arts[2]["capo"] == "CAPO II – DISCIPLINA"
    # a CAPO line between articles must not leak into the previous article text
    assert "CAPO" not in arts[1]["text"]


def test_bare_item_number_joins_next_line():
    assert split_articles(SYNTHETIC)[2]["text"] == "2. Testo dell’articolo tre."


def test_no_articles():
    assert split_articles("nothing here") == []


# --- checks on the generated data files -----------------------------------------------

ARTICLES = ROOT / "data" / "articles.json"


@pytest.fixture(scope="module")
def articles():
    return json.loads(ARTICLES.read_text(encoding="utf-8"))


def _by_doc(articles, doc):
    return [a for a in articles if a["doc"] == doc]


def test_corpus_counts_and_pr_ids_unchanged(articles):
    pr = _by_doc(articles, "PR")
    assert [a["number"] for a in pr] == list(range(1, 54))       # 53 articles, ids as before
    assert [a["id"] for a in pr] == [f"PR-art-{n}" for n in range(1, 54)]
    assert [a["id"] for a in articles[:53]] == [a["id"] for a in pr]   # PR comes first
    assert len(_by_doc(articles, "PS")) == 14
    assert [a["number"] for a in _by_doc(articles, "PS")] == list(range(1, 15))
    assert len(_by_doc(articles, "DP")) == 8
    ptc = _by_doc(articles, "PTC")
    assert [a["number"] for a in ptc if a["id"].startswith("PTC-art-")] == list(range(1, 55))
    assert any(a["id"] == "PTC-all-A" for a in ptc)
    assert [a["number"] for a in _by_doc(articles, "CG")] == list(range(42, 52))
    assert len(_by_doc(articles, "CGS")) == 2
    assert len(_by_doc(articles, "DPA1")) >= 20


def test_corpus_records_are_well_formed(articles):
    ids = [a["id"] for a in articles]
    assert len(ids) == len(set(ids))
    docs = {d["doc"]: d for d in json.loads((ROOT / "data" / "documents.json").read_text("utf-8"))}
    assert set(docs) == {a["doc"] for a in articles}
    for a in articles:
        d = docs[a["doc"]]
        assert a["text"].strip() and a["title"].strip(), a["id"]
        assert a["normative"] is d["normative"] and a["doc_name"] == d["name"]
        assert a["version_date"] == d["version_date"] and a["source_file"] == d["file"]
        assert a["pages"][0] <= a["pages"][1]
        assert a["label"], a["id"]
        assert "�" not in a["text"] and "�" not in a["title"], a["id"]
        assert " " not in a["text"]
        # no leftover page furniture / PDF encoding artefacts
        for line in a["text"].split(chr(10)):
            assert line.strip() not in ("Piano dei Servizi", "Documento di Piano",
                                        "Norme di attuazione"), a["id"]
        assert "`" not in a["text"] or a["doc"] != "PTC", a["id"]
        if a["doc"] == "DPA1":
            assert a["normative"] is False
        else:
            assert a["normative"] is True
    assert all(a["version_date"] == "2025-12-04" for a in _by_doc(articles, "PR"))
    assert "without later amendments" in docs["PTC"]["version_note"].replace("NOT included", "without later amendments")         or "NOT included" in docs["PTC"]["version_note"]


def test_pr_2025_text_is_the_source(articles):
    a45 = {a["id"]: a for a in articles}["PR-art-45"]
    assert "torrente Seveso" in a45["text"] and "iiibis" in a45["text"]   # new in the 2025 text
    assert "PR_Norme_Attuazione_20251204.pdf" == a45["source_file"]


def _article_refs(node, key_suffix="articles"):
    """Collect every reference under a key that ends with `articles` (recursively)."""
    found = []
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(k, str) and k.endswith(key_suffix) and isinstance(v, list):
                found.extend(v)
            else:
                found.extend(_article_refs(v, key_suffix))
    elif isinstance(node, list):
        for v in node:
            found.extend(_article_refs(v, key_suffix))
    return found


def _as_id(ref):
    return f"PR-art-{ref}" if isinstance(ref, int) else str(ref)


@pytest.mark.parametrize("name", ["zone_map", "constraint_map"])
def test_mapped_articles_exist(articles, name):
    ids = {a["id"] for a in articles}
    for ext in ("json", "yaml"):
        path = ROOT / "data" / f"{name}.{ext}"
        if ext == "yaml":
            yaml = pytest.importorskip("yaml")
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        else:
            data = json.loads(path.read_text(encoding="utf-8"))
        refs = _article_refs(data)
        assert refs, f"no article references found in {path.name}"
        missing = sorted({_as_id(r) for r in refs if _as_id(r) not in ids})
        assert not missing, f"{path.name} cites ids not in articles.json: {missing}"
        assert all(isinstance(r, str) and "-" in r for r in refs)    # ids, not bare numbers


def test_map_json_matches_yaml():
    yaml = pytest.importorskip("yaml")
    for name in ("zone_map", "constraint_map"):
        y = yaml.safe_load((ROOT / "data" / f"{name}.yaml").read_text(encoding="utf-8"))
        j = json.loads((ROOT / "data" / f"{name}.json").read_text(encoding="utf-8"))
        assert y == j, f"{name}.json is stale: run scripts/build_maps.py"


def test_explanatory_ids_are_not_normative(articles):
    by_id = {a["id"]: a for a in articles}
    zone = json.loads((ROOT / "data" / "zone_map.json").read_text(encoding="utf-8"))
    for key, entry in zone["layers"].items():
        for ref in _article_refs(entry, "explanatory_articles"):
            assert by_id[ref]["normative"] is False, (key, ref)
        for role in ("articles", "general_articles"):
            for ref in entry.get(role, []):
                assert by_id[_as_id(ref)]["normative"] is True, (key, ref)
