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


def test_articles_json_complete(articles):
    assert len(articles) == 53
    assert [a["number"] for a in articles] == list(range(1, 54))
    for a in articles:
        assert a["id"] == f"PR-art-{a['number']}"
        assert a["text"].strip(), a["id"]
        assert a["title"].strip(), a["id"]
        assert a["version_date"] == "2022-12-19"
        assert a["pages"][0] <= a["pages"][1]
        assert "�" not in a["text"]
        assert "\xa0" not in a["text"]


def _article_refs(node, key_suffix="articles"):
    """Collect every int under a key that ends with `articles` (recursively)."""
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


@pytest.mark.parametrize("name", ["zone_map.yaml", "constraint_map.yaml"])
def test_mapped_articles_exist(articles, name):
    yaml = pytest.importorskip("yaml")
    data = yaml.safe_load((ROOT / "data" / name).read_text(encoding="utf-8"))
    refs = _article_refs(data)
    assert refs, f"no article references found in {name}"
    numbers = {a["number"] for a in articles}
    missing = sorted({r for r in refs if r not in numbers})
    assert not missing, f"{name} cites articles not in articles.json: {missing}"
    assert all(isinstance(r, int) for r in refs)
