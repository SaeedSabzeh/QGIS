"""Phase 1: split the NTA PDF at each `art. N` heading and write data/articles.json.

Usage: python scripts/parse_nta.py [path/to/NTA.pdf] [output.json]

The pure splitting logic lives in `split_articles(text)`, which takes the text of
the whole PDF with pages separated by form feeds ("\f"), so it can be tested
without PyMuPDF or the PDF. `pages` in the output are 1-based PDF page numbers
(the printed page number is the PDF page minus 2).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = ROOT / "data" / "raw" / "PR_Norme_Attuazione_20230308.pdf"
DEFAULT_OUT = ROOT / "data" / "articles.json"

SOURCE = "Piano delle Regole – Norme di attuazione, PGT Milano 2030"
VERSION_DATE = "2022-12-19"  # DCC 100 of 19/12/2022 (modified text)

FURNITURE = {"norme di attuazione", "piano delle regole"}
FURNITURE_WINDOW = 4  # furniture sits in the first lines of each page

ART_RE = re.compile(r"^art\.\s*(\d+)\b\s*(.*)$")
TITOLO_RE = re.compile(r"^(TITOLO)\s+([IVX]+)\s*[–—-]\s*(.*)$")
CAPO_RE = re.compile(r"^(CAPO)\s+([IVX]+)\s*[–—-]\s*(.*)$")
# line that starts a new comma / list item: "1.", "a.", "ii.", bullet
ITEM_RE = re.compile(r"^(\d+\.|[a-z]{1,2}\.|•)(\s|$)")


def _clean(s):
    return s.replace("\xa0", " ").replace("\xad", "").strip()


def _page_lines(text):
    """Yield (page_no, line) with page furniture removed."""
    for pno, page in enumerate(text.split("\f"), start=1):
        lines = page.split("\n")
        head = 0  # count of non-empty lines seen at page top
        for line in lines:
            c = _clean(line)
            if c and head < FURNITURE_WINDOW:
                head += 1
                if c.lower() in FURNITURE or c.isdigit():
                    continue
            yield pno, c


def _chain(lines, start):
    """Follow sequential `art. N` headings from lines[start] (an art. 1).
    Returns the list of (line_index, number)."""
    out = [(start, 1)]
    expect = 2
    for i in range(start + 1, len(lines)):
        m = ART_RE.match(lines[i][1])
        if m and int(m.group(1)) == expect:
            out.append((i, expect))
            expect += 1
    return out


def _join(parts):
    """Join wrapped lines of one paragraph; keep compound hyphens, drop soft ones."""
    out = ""
    for p in parts:
        if not out:
            out = p
        elif out.endswith("¬"):  # soft hyphen artefact of the PDF
            out = out[:-1] + p
        elif out.endswith("-") and out[-2:-1].isalpha() and p[:1].isalpha():
            out += p  # "plano-" + "volumetriche" -> "plano-volumetriche"
        else:
            out += " " + p
    return out.replace("¬", "")


def _paragraphs(lines):
    """lines: list of cleaned strings ('' = blank). Returns text with each
    numbered item / paragraph on its own line."""
    paras, cur = [], []
    for ln in lines:
        if not ln:
            if cur:
                paras.append(cur)
                cur = []
        elif ITEM_RE.match(ln):
            if cur:
                paras.append(cur)
            cur = [ln]
        else:
            cur.append(ln)
    if cur:
        paras.append(cur)
    # a bare "2." line followed by its text stays together on one line
    out = []
    for p in paras:
        if len(p) > 1 and ITEM_RE.match(p[0]) and re.fullmatch(r"(\d+\.|[a-z]{1,2}\.)", p[0]):
            p = [p[0] + " " + p[1]] + p[2:]
        out.append(_join(p))
    return "\n".join(out)


def split_articles(text):
    """Split NTA text into a list of article dicts (id, number, title, titolo,
    capo, text, pages). Table-of-contents entries are skipped."""
    lines = list(_page_lines(text))
    cands = [i for i, (_, l) in enumerate(lines)
             if (m := ART_RE.match(l)) and int(m.group(1)) == 1]
    if not cands:
        return []
    # TOC and body both contain an `art. 1`; the body chain ends last.
    chain = max((_chain(lines, c) for c in cands), key=lambda ch: ch[-1][0])
    first = chain[0][0]

    # context headings directly above art. 1
    start = first
    for j in range(first - 1, max(first - 8, -1), -1):
        if TITOLO_RE.match(lines[j][1]):
            start = j
            break
    head_idx = {i: n for i, n in chain}
    titolo = capo = None
    arts, cur = [], None
    i = start
    while i < len(lines):
        pno, l = lines[i]
        if i in head_idx:
            n = head_idx[i]
            m = ART_RE.match(l)
            cur = {"number": n, "title": m.group(2).strip(), "titolo": titolo,
                   "capo": capo, "pages": [pno, pno], "lines": []}
            arts.append(cur)
        elif (m := TITOLO_RE.match(l)):
            titolo = f"TITOLO {m.group(2)} – {m.group(3).strip()}"
            capo = None
        elif (m := CAPO_RE.match(l)):
            title = m.group(3).strip()
            # heading wrapped on the next line(s)
            while (i + 1 < len(lines) and lines[i + 1][1] and (i + 1) not in head_idx
                   and not CAPO_RE.match(lines[i + 1][1]) and not TITOLO_RE.match(lines[i + 1][1])
                   and lines[i + 1][1].isupper()):
                i += 1
                title += " " + lines[i][1]
            capo = f"CAPO {m.group(2)} – {title}"
        elif cur is not None:
            cur["lines"].append(l)
            if l:
                cur["pages"][1] = pno
        i += 1

    result = []
    for a in arts:
        text_ = _paragraphs(a["lines"])
        result.append({
            "id": f"PR-art-{a['number']}", "number": a["number"], "title": a["title"],
            "titolo": a["titolo"], "capo": a["capo"], "text": text_, "pages": a["pages"],
        })
    return result


def extract_text(pdf_path):
    import pymupdf  # PyMuPDF
    with pymupdf.open(str(pdf_path)) as doc:
        return "\f".join(page.get_text() for page in doc)


def build(pdf_path):
    pdf_path = Path(pdf_path)
    out = []
    for a in split_articles(extract_text(pdf_path)):
        out.append({
            "id": a["id"], "number": a["number"], "title": a["title"],
            "titolo": a["titolo"], "capo": a["capo"], "text": a["text"],
            "source": SOURCE, "source_file": pdf_path.name,
            "version_date": VERSION_DATE, "pages": a["pages"],
        })
    return out


def main(argv):
    pdf = Path(argv[1]) if len(argv) > 1 else DEFAULT_PDF
    dest = Path(argv[2]) if len(argv) > 2 else DEFAULT_OUT
    arts = build(pdf)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(arts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(arts)} articles -> {dest}")


if __name__ == "__main__":
    main(sys.argv)
