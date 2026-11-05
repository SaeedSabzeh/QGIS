"""Tiny, safe markdown-to-HTML converter for model answers (stdlib only, no Qt).

Supports **bold**, *italic* / _italic_, `code`, headings (# ...), unordered lists (-, *, a
bullet), ordered lists (1. or 1)) with one or more nesting levels, paragraphs and line breaks.
All text is HTML-escaped FIRST; the only tags ever produced are <p>, <br>, <b>, <i>, <code>,
<ul>, <ol>, <li>, so raw HTML (or a <script>) in the input can never reach the output as markup.
Links and images are not interpreted: they stay plain text.
"""

import re
from html import escape

_CODE = re.compile(r"(`[^`\n]+`)")
_BOLD = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*")
_ITALIC_STAR = re.compile(r"(?<![\w*])\*(?=[^\s*])(.+?)(?<=[^\s*])\*(?![\w*])")
_ITALIC_UNDER = re.compile(r"(?<![\w_])_(?=[^\s_])(.+?)(?<=[^\s_])_(?![\w_])")
_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
_BULLET = re.compile(r"^(\s*)[-*•]\s+(.*)$")
_ORDERED = re.compile(r"^(\s*)(\d{1,4})[.)]\s+(.*)$")
_RULE = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")


def _inline(text):
    """Escape `text`, then apply the inline markers."""
    out = []
    for piece in _CODE.split(text):
        if len(piece) > 2 and piece[0] == "`" and piece[-1] == "`":
            out.append("<code>%s</code>" % escape(piece[1:-1]))
            continue
        piece = escape(piece)
        piece = _BOLD.sub(r"<b>\1</b>", piece)
        piece = _ITALIC_STAR.sub(r"<i>\1</i>", piece)
        piece = _ITALIC_UNDER.sub(r"<i>\1</i>", piece)
        out.append(piece)
    return "".join(out)


def _indent(ws):
    return len(ws.expandtabs(4))


def to_html(text):
    """Markdown-lite text -> HTML fragment (safe: input is escaped, only simple tags emitted)."""
    out = []
    para = []          # lines of the current paragraph
    stack = []         # open lists: [kind, indent]; each always has an open <li>

    def flush_para():
        if para:
            out.append("<p>%s</p>" % "<br>".join(_inline(x) for x in para))
            del para[:]

    def close_lists(keep=0):
        while len(stack) > keep:
            out.append("</li></%s>" % stack.pop()[0])

    def add_item(kind, ind, body, start=None):
        while stack and ind < stack[-1][1]:
            close_lists(len(stack) - 1)
        if stack and ind == stack[-1][1] and kind != stack[-1][0]:
            close_lists(len(stack) - 1)
        if stack and ind == stack[-1][1]:
            out.append("</li>")  # sibling item: close the previous one
        else:
            if kind == "ul":
                out.append("<ul>")
            else:
                out.append('<ol start="%d">' % start if start and start != 1 else "<ol>")
            stack.append([kind, ind])
        out.append("<li>%s" % _inline(body))

    for raw in str(text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if not raw.strip():
            flush_para()
            close_lists()
            continue
        head = _HEADING.match(raw)
        bullet = _BULLET.match(raw)
        ordered = _ORDERED.match(raw)
        if head:
            flush_para()
            close_lists()
            out.append("<p><b>%s</b></p>" % _inline(head.group(2)))
        elif _RULE.match(raw):
            flush_para()
            close_lists()
        elif bullet:
            flush_para()
            add_item("ul", _indent(bullet.group(1)), bullet.group(2))
        elif ordered:
            flush_para()
            add_item("ol", _indent(ordered.group(1)), ordered.group(3), int(ordered.group(2)))
        elif stack and raw[:1] in (" ", "\t"):
            out.append("<br>%s" % _inline(raw.strip()))  # continuation of a list item
        else:
            close_lists()
            para.append(raw.strip())
    flush_para()
    close_lists()
    return "".join(out)
