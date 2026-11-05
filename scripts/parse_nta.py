"""Split an NTA PDF at each `art. N` heading (the Piano delle Regole by default).

The whole multi-document corpus (data/articles.json + data/documents.json) is built by
scripts/build_corpus.py, which reuses `split_articles` from here. Running this script writes the
PR articles only (to the given output file; default data/articles.json would drop the other
documents, so prefer build_corpus.py).

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
DEFAULT_PDF = ROOT / "data" / "raw" / "PR_Norme_Attuazione_20251204.pdf"
DEFAULT_OUT = ROOT / "data" / "articles_pr_only.json"

SOURCE = "Piano delle Regole – Norme di attuazione, PGT Milano 2030"
VERSION_DATE = "2025-12-04"  # DCC 93 of 04/12/2025 (in force, BURL n.5 of 28/01/2026)

FURNITURE = {"norme di attuazione", "piano delle regole"}
FURNITURE_WINDOW = 4  # furniture sits in the first lines of each page

ART_RE = re.compile(r"^art\.\s*(\d+)\b\s*(.*)$")
TITOLO_RE = re.compile(r"^(TITOLO)\s+([IVX]+)\s*[–—-]\s*(.*)$")
CAPO_RE = re.compile(r"^(CAPO)\s+([IVX]+)\s*[–—-]\s*(.*)$")
# line that starts a new comma / list item: "1.", "a.", "ii.", bullet
ITEM_RE = re.compile(r"^(\d+\.|[a-z]{1,2}\.|•)(\s|$)")


def _clean(s):
    return s.replace("\xa0", " ").replace("\xad", "").strip()


def _page_lines(text, furniture=FURNITURE, furniture_re=None, drop_re=None):
    """Yield (page_no, line) with page furniture removed.

    `furniture`: lowercase lines dropped when they sit in the first lines of a page (page
    numbers too). `furniture_re`: same, but a compiled regex. `drop_re`: a regex for lines
    dropped wherever they are on the page (running headers, separators, lone page numbers).
    """
    for pno, page in enumerate(text.split(chr(12)), start=1):
        head = 0  # count of non-empty lines seen at page top
        for line in page.split(chr(10)):
            c = _clean(line)
            if c and head < FURNITURE_WINDOW:
                head += 1
                if c.lower() in furniture or c.isdigit() or (furniture_re and furniture_re.match(c)):
                    continue
            if c and drop_re and drop_re.match(c):
                continue
            yield pno, c


def _chain(lines, start, art_re=ART_RE, first=1):
    """Follow sequential `art. N` headings from lines[start] (the first article).
    Returns the list of (line_index, number)."""
    out = [(start, first)]
    expect = first + 1
    for i in range(start + 1, len(lines)):
        m = art_re.match(lines[i][1])
        if m and int(m.group(1)) == expect:
            out.append((i, expect))
            expect += 1
    return out


def _join(parts, dehyphen=False):
    """Join wrapped lines of one paragraph; keep compound hyphens, drop soft ones.

    With `dehyphen` (texts typeset with syllable hyphenation: "agrico-" + "lo") a hyphen at
    the end of a line before a lowercase continuation is dropped."""
    out = ""
    for p in parts:
        if not out:
            out = p
        elif out.endswith("¬"):  # soft hyphen artefact of the PDF
            out = out[:-1] + p
        elif dehyphen and out.endswith("-") and out[-2:-1].isalpha() and p[:1].islower():
            out = out[:-1] + p
        elif out.endswith("-") and out[-2:-1].isalpha() and p[:1].isalpha():
            out += p  # "plano-" + "volumetriche" -> "plano-volumetriche"
        else:
            out += " " + p
    return out.replace("¬", "")


def _paragraphs(lines, item_re=ITEM_RE, dehyphen=False, prose=False):
    """lines: list of cleaned strings ('' = blank). Returns text with each
    numbered item / paragraph on its own line. With `prose`, a line that follows a
    sentence-ending line clearly shorter than the column also starts a paragraph."""
    full = 0
    if prose:
        lens = sorted(len(x) for x in lines if x)
        full = lens[int(len(lens) * 0.9)] if lens else 0
    paras, cur = [], []
    for ln in lines:
        if not ln:
            if cur:
                paras.append(cur)
                cur = []
        elif item_re.match(ln):
            if cur:
                paras.append(cur)
            cur = [ln]
        elif prose and cur and cur[-1][-1:] in ".:;!?" and len(cur[-1]) < 0.8 * full:
            paras.append(cur)
            cur = [ln]
        else:
            cur.append(ln)
    if cur:
        paras.append(cur)
    # a bare "2." line followed by its text stays together on one line
    out = []
    for p in paras:
        if len(p) > 1 and item_re.match(p[0]) and re.fullmatch(r"(\d+\.|[a-z]{1,2}\.)", p[0]):
            p = [p[0] + " " + p[1]] + p[2:]
        out.append(_join(p, dehyphen))
    return "\n".join(out)


_CONT_END = re.compile(r"(?:^|\s)(?:a|ad|di|del|dei|della|delle|dello|degli|e|ed|il|la|le|lo|in|nel|nella|"
                       r"nei|per|con|da|dal|dalla|al|alla|alle|agli|ai|o|su|sul|sulla)$|[-,]$", re.I)


def split_articles(text, prefix="PR", art_re=ART_RE, first=1, furniture=FURNITURE,
                   furniture_re=None, drop_re=None, item_re=ITEM_RE, dehyphen=False,
                   prose=False, stop_re=None, block_titles=False):
    """Split NTA text into a list of article dicts (id, number, title, titolo,
    capo, text, pages). Table-of-contents entries are skipped.

    Defaults reproduce the Piano delle Regole ("art. N Title" on one line, numbering from 1).
    `prefix` gives the ids ("<prefix>-art-N"); `first` is the number of the first article;
    `stop_re` ends the last article at the first matching line (appendix, catalogue);
    `block_titles` is for headings "Art. N" alone on a line with the title on the following
    lines (up to the first numbered paragraph); an inline title that ends on a connective
    ("... dei") continues on the next line."""
    lines = list(_page_lines(text, furniture, furniture_re, drop_re))
    cands = [i for i, (_, l) in enumerate(lines)
             if (m := art_re.match(l)) and int(m.group(1)) == first]
    if not cands:
        return []
    # TOC and body both contain the first article; the body chain ends last.
    chain = max((_chain(lines, c, art_re, first) for c in cands), key=lambda ch: ch[-1][0])
    start = chain[0][0]
    stop_at = len(lines)
    if stop_re:
        for j in range(chain[-1][0] + 1, len(lines)):
            if stop_re.match(lines[j][1]):
                stop_at = j
                break

    # context headings directly above the first article
    for j in range(start - 1, max(start - 8, -1), -1):
        if TITOLO_RE.match(lines[j][1]):
            start = j
            break
    head_idx = {i: n for i, n in chain}
    titolo = capo = None
    arts, cur = [], None
    in_title = False
    i = start
    while i < stop_at:
        pno, l = lines[i]
        if i in head_idx:
            n = head_idx[i]
            m = art_re.match(l)
            title = (m.group(2) if m.lastindex and m.lastindex >= 2 else "").strip()
            cur = {"number": n, "title": title, "titolo": titolo,
                   "capo": capo, "pages": [pno, pno], "lines": []}
            arts.append(cur)
            in_title = block_titles
            if not block_titles:
                while (title and _CONT_END.search(title) and i + 1 < stop_at and lines[i + 1][1]
                       and (i + 1) not in head_idx):
                    i += 1
                    title += " " + lines[i][1]
                cur["title"] = title
        elif in_title and cur is not None:
            if item_re.match(l) or not l:
                in_title = False
                if l:
                    cur["lines"].append(l)
            else:
                cur["title"] = (cur["title"] + " " + l).strip()
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
        text_ = _paragraphs(a["lines"], item_re, dehyphen, prose)
        result.append({
            "id": f"{prefix}-art-{a['number']}", "number": a["number"], "title": a["title"],
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
