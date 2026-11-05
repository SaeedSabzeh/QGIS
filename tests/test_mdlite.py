import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.mdlite import to_html  # noqa: E402


def test_bold_italic_code():
    h = to_html("Un **testo** in *corsivo*, _anche cosi_ e `codice`.")
    assert h == ("<p>Un <b>testo</b> in <i>corsivo</i>, <i>anche cosi</i> e "
                 "<code>codice</code>.</p>")


def test_html_is_escaped_never_passed_through():
    h = to_html("<script>alert(1)</script> **<img src=x onerror=y>** `<b>`")
    assert "<script" not in h and "<img" not in h
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in h
    assert "<b>&lt;img src=x onerror=y&gt;</b>" in h
    assert "<code>&lt;b&gt;</code>" in h
    assert to_html("a & b") == "<p>a &amp; b</p>"
    assert "<a " not in to_html("[x](javascript:alert(1)) <a href='x'>y</a>")
    assert "<script" not in to_html("- <script>x</script>\n1. <script>y</script>\n# <script>z")


def test_script_in_heading_and_list_item():
    h = to_html("# <script>x</script>")
    assert h == "<p><b>&lt;script&gt;x&lt;/script&gt;</b></p>"


def test_headings():
    assert to_html("## Titolo") == "<p><b>Titolo</b></p>"
    assert to_html("### Titolo ###") == "<p><b>Titolo</b></p>"


def test_unordered_lists():
    assert to_html("- uno\n- due\n* tre") == "<ul><li>uno</li><li>due</li><li>tre</li></ul>"


def test_ordered_list_with_bold_and_continuation_and_nesting():
    md = ("1. **Fattibilità Geologica (Classe II)**: testo\n"
          "   continua\n"
          "   - sotto uno\n"
          "   - sotto due\n"
          "2. Secondo")
    h = to_html(md)
    assert h == ("<ol><li><b>Fattibilità Geologica (Classe II)</b>: testo<br>continua"
                 "<ul><li>sotto uno</li><li>sotto due</li></ul></li><li>Secondo</li></ol>")
    assert "**" not in h


def test_ordered_list_keeps_start_number_after_blank_line():
    h = to_html("1. a\n\n2. b")
    assert h == '<ol><li>a</li></ol><ol start="2"><li>b</li></ol>'


def test_paragraphs_and_line_breaks():
    assert to_html("uno\ndue\n\ntre") == "<p>uno<br>due</p><p>tre</p>"
    assert to_html("a\r\nb") == "<p>a<br>b</p>"
    assert to_html("") == "" and to_html(None) == ""


def test_list_then_paragraph():
    assert to_html("- a\n- b\nfine") == "<ul><li>a</li><li>b</li></ul><p>fine</p>"


def test_non_markup_underscores_and_stars_stay():
    h = to_html("snake_case_name e 2*3*4 e a * b")
    assert "<i>" not in h and "snake_case_name" in h and "2*3*4" in h


def test_unbalanced_markers_are_left_alone():
    assert to_html("**aperto") == "<p>**aperto</p>"
    assert to_html("`aperto") == "<p>`aperto</p>"
