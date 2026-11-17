"""Dock panel: constraints at the clicked point, linked articles, question and answer.

One language at a time (Italian or English, see i18n.py). Results get most of the height;
the legal notes sit behind a one-line footer.
"""

import re
from html import escape
from urllib.parse import urlsplit

from qgis.PyQt.QtCore import QSize, Qt, QUrl, pyqtSignal
from qgis.PyQt.QtGui import QBrush, QColor, QDesktopServices, QFont, QKeySequence
from qgis.PyQt.QtWidgets import (
    QApplication,
    QDockWidget,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

try:  # Qt6 moved QShortcut to QtGui
    from qgis.PyQt.QtGui import QShortcut
except ImportError:
    from qgis.PyQt.QtWidgets import QShortcut

from . import early_access, i18n
from ._compat import enum, mdlite, prompts, retrieval

MAX_VALUE_CHARS = 80
MIN_WIDTH = 280
MUTED = "#5f6368"
ACCENT = "#1a5fb4"
WHY_PREVIEW = 150  # characters of the explanation shown before "more"

# Short document names for compact article references.
DOC_SHORT = {
    "PR": "PdR", "PS": "PdS", "DP": "DdP", "DPA1": "DdP All. 1", "PTC": "PTC Parco Sud",
    "CG": "Comp. geologica", "CGS": "Comp. sismica",
}
FAMILY_COLOR = {
    "zoning": "#2f6db5", "landscape": "#3b8a3e", "geology": "#9a6b1f",
    "flood": "#b23b3b", "nature": "#13806e",
}
ROLE_ORDER = {"governing": 0, "general": 1, "candidate": 2, "explanatory": 3}
SKIP_KEYS = {"SCHEDA_NEW", "AMB_TRAS", "OBJECTID", "SHAPE", "GLOBALID"}
REF_RE = re.compile(r"\b([A-Z][A-Za-z0-9]*)-(art|sec|all)-([0-9]+[a-z]?(?:\.[0-9]+)?)\b")


def _wrap(text):
    return " ".join(str(text).split())


def early_access_tip(t):
    """Tooltip for the early-access link: what happens when it is clicked."""
    if early_access.SIGNUP_EMAIL:
        return t("ea_tip_mail") % early_access.SIGNUP_EMAIL
    return t("ea_tip")


def _source_link(url, label):
    try:
        parts = urlsplit(str(url or ""))
    except ValueError:
        return ""
    if parts.scheme == "https" and parts.hostname and parts.username is None:
        return '<a href="%s">%s</a>' % (escape(parts.geturl(), quote=True), escape(label))
    return ""


def family(f):
    """Constraint family for the colour chip: zoning, landscape, geology, flood or nature."""
    key = ("%s %s" % (f.get("category", ""), f.get("layer", ""))).lower()
    if "pgra" in key or "allag" in key or "flood" in key:
        return "flood"
    if "geolog" in key or "fattib" in key or "sism" in key:
        return "geology"
    if "paes" in key or "sensib" in key or "landscape" in key or "136" in key:
        return "landscape"
    if any(word in key for word in ("parc", "park", "natura", "zsc", "zps", "plis",
                                     "ticinello", "verde", "agricolt")):
        return "nature"
    return "zoning"


def _sentence(value):
    text = _wrap(value)
    if text.isupper() and " " in text:  # long all-caps descriptions, not short codes
        text = text[:1] + text[1:].lower()
    return text


def human_values(values, label=""):
    """Readable attribute values: no field names, no codes, nothing repeated."""
    out = []
    for key, value in (values or {}).items():
        k = str(key).upper()
        if k in SKIP_KEYS or k.startswith(("COD_", "TIPO_", "ID_")) or value in (None, ""):
            continue
        if k == "CLASSE":
            text = "Classe %s" % value
        elif isinstance(value, (int, float)) or str(value).strip().isdigit():
            continue
        elif str(value).startswith(("http://", "https://")):
            continue
        else:
            text = _sentence(value)
        if text.strip():
            out.append(text[:MAX_VALUE_CHARS * 3])
    # drop anything the title or a longer value already says
    kept = []
    head = _wrap(label).lower()
    for text in sorted(out, key=len, reverse=True):
        low = text.lower()
        bare = low.replace("classe ", "")
        if low in head or any(low in k.lower() or k.lower().startswith(bare + " ")
                              for k in kept):
            continue
        kept.append(text)
    return [t for t in out if t in kept]


def _parse_ref(ref):
    match = re.match(r"^([A-Za-z0-9]+)-(art|sec|all)-(.+)$", str(ref))
    return match.groups() if match else None


def _ref_word(kind, lang, many=False):
    return {"art": ("artt." if lang == "it" else "arts.") if many else "art.",
            "sec": "sez." if lang == "it" else "sec.",
            "all": "All." if lang == "it" else "Annex"}[kind]


def short_ref(ref, lang="en"):
    """"PdR art. 6" for "PR-art-6"; unknown ids fall back to the corpus label."""
    parsed = _parse_ref(ref)
    if not parsed:
        return retrieval.ref_label(ref)
    doc, kind, num = parsed
    return "%s %s %s" % (DOC_SHORT.get(doc, doc), _ref_word(kind, lang), num)


def compact_refs(ids, lang="en", links=True):
    """"PdR artt. 18, 19 · PTC Parco Sud art. 1" with each number linking to its article."""
    groups, order, others = {}, [], []
    for ref in ids:
        parsed = _parse_ref(ref)
        if parsed is None:
            others.append(ref)
            continue
        doc, kind, num = parsed
        if (doc, kind) not in groups:
            groups[(doc, kind)] = []
            order.append((doc, kind))
        groups[(doc, kind)].append((num, ref))
    parts = []
    for doc, kind in order:
        items = groups[(doc, kind)]
        nums = ", ".join(
            ('<a href="art:%s">%s</a>' % (escape(ref, quote=True), escape(num))) if links
            else escape(num) for num, ref in items)
        parts.append("%s %s %s" % (escape(DOC_SHORT.get(doc, doc)),
                                   _ref_word(kind, lang, len(items) > 1), nums))
    for ref in others:
        parts.append(escape(retrieval.ref_label(ref)))
    return " · ".join(parts)


def tidy_text(text, lang="en"):
    """Plan abbreviations as shown elsewhere ("PR art." -> "PdR art.", "PR-art-6" -> "PdR art. 6")."""
    text = REF_RE.sub(lambda m: short_ref(m.group(0), lang), str(text or ""))
    return re.sub(r"\b(PR|PS|DP)( artt?\.)", lambda m: DOC_SHORT[m.group(1)] + m.group(2), text)


def _refs(ids):
    """"Piano dei Servizi – art. 11, Piano delle Regole – art. 8" for a list of ids."""
    return ", ".join(retrieval.ref_label(n) for n in ids)


def finding_summary(f, lang="en"):
    """(headline, [detail lines]) as plain text, used for logs and tests."""
    t = lambda key: i18n.text(key, lang)  # noqa: E731
    head = f.get("label") or f.get("category") or f.get("layer", "")
    details = human_values(f.get("values", {}), head)
    if details:
        head += " (%s)" % "; ".join(details)
    if f.get("verify"):
        head += "  [%s]" % t("verify")
    lines = []
    for key in ("articles", "general_articles", "explanatory_articles", "candidate_articles"):
        if f.get(key):
            title = t({"articles": "governing", "general_articles": "general",
                       "explanatory_articles": "explanatory",
                       "candidate_articles": "candidate"}[key])
            lines.append("%s: %s" % (title, _refs(f[key])))
    if f.get("why"):
        lines.append("%s: %s" % (t("why"), _wrap(f["why"])))
    if f.get("note"):
        lines.append("Note: " + _wrap(f["note"]))
    if f.get("verify"):
        lines.append(t("verify_note"))
    ext = f.get("external_rule")
    if ext:
        lines.append("%s%s: %s" % (t("external"),
                                   " (%s)" % t("unverified") if ext.get("verify") else "",
                                   _wrap(ext.get("text", ""))))
    return head, lines


def _preview(text):
    """The first WHY_PREVIEW characters of a long explanation, cut at a word."""
    if len(text) <= WHY_PREVIEW:
        return text
    return text[:WHY_PREVIEW].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def finding_html(f, lang="en", index=0, expanded=False):
    """One constraint as a card: colour bar, family, title, readable values, linked articles."""
    t = lambda key: i18n.text(key, lang)  # noqa: E731
    fam = family(f)
    color = FAMILY_COLOR[fam]
    head = f.get("label") or f.get("category") or f.get("layer", "")
    small = "<p style='margin:2px 0 0 0; color:%s; font-size:small'>" % MUTED
    body = ["<a name='c%d'></a><p style='margin:0'><span style='color:%s; font-size:small'>"
            "<b>%s</b></span>" % (index, color, escape(t("fam_" + fam)).upper())]
    if f.get("verify"):
        body.append(" &nbsp;<span style='background-color:#fff1c2; color:#6b4a00;"
                    " font-size:small'>&nbsp;%s&nbsp;</span>" % escape(t("verify")))
    body.append("</p><p style='margin:1px 0 0 0'><b>%s</b></p>" % escape(str(head)))
    values = human_values(f.get("values", {}), head)
    if values:
        body.append("<p style='margin:1px 0 0 0'>%s</p>" % escape(" · ".join(values)))
    for key, title in (("articles", "governing"), ("general_articles", "general"),
                       ("explanatory_articles", "explanatory"),
                       ("candidate_articles", "candidate")):
        if f.get(key):
            style = "margin:3px 0 0 0" if key == "articles" else \
                "margin:1px 0 0 0; color:%s" % MUTED
            body.append("<p style='%s'>%s: %s</p>" % (style, escape(t(title)),
                                                      compact_refs(f[key], lang)))
    # explanation: the source notes are written in English
    why = tidy_text(_wrap(f.get("why", "")), lang)
    note = tidy_text(_wrap(f.get("note", "")), lang)
    if why or note:
        if lang == "it" and not expanded:
            body.append("%s<a href='more:%d'>%s</a></p>" % (small, index, escape(t("why_en_only"))))
        elif expanded:
            if why:
                body.append("%s%s: %s</p>" % (small, escape(t("why")), escape(why)))
            if note:
                body.append("%s%s</p>" % (small, escape(note)))
            body.append("%s<a href='more:%d'>%s</a></p>" % (small, index, escape(t("less"))))
        else:
            first = why or note
            body.append("%s%s: %s <a href='more:%d'>%s</a></p>" % (
                small, escape(t("why")), escape(_preview(first)), index, escape(t("more"))))
    if f.get("verify"):
        body.append("%s%s</p>" % (small, escape(t("verify_note"))))
    ext = f.get("external_rule")
    if ext:
        body.append("%s<b>%s%s:</b> %s</p>" % (
            small, escape(t("external")), " (%s)" % escape(t("unverified")) if ext.get("verify")
            else "", escape(_wrap(ext.get("text", "")))))
    links = [x for x in (_source_link(f.get("map_url"), t("official_map")),
                         _source_link(f.get("document_url"), t("official_park"))) if x]
    if links:
        body.append("%s%s</p>" % (small, " · ".join(links)))
    return ("<table width='100%%' cellspacing='0' cellpadding='0' style='margin-bottom:12px'>"
            "<tr><td width='4' bgcolor='%s'></td><td width='8'></td><td>%s</td></tr></table>"
            % (color, "".join(body)))


def summary_html(findings, lang="en"):
    """"5 constraints: NAF · Fattibilità geologica · …", each name jumping to its card."""
    names = []
    for i, f in enumerate(findings):
        fam = family(f)
        title = str(f.get("label") or i18n.text("fam_" + fam, lang))
        title = re.split(r" \(| - ", title)[0].strip()
        if len(title) > 28:
            title = title[:27].rsplit(" ", 1)[0] + "…"
        names.append("<a href='goto:%d' style='color:%s; text-decoration:none'>%s</a>" % (
            i, FAMILY_COLOR[fam], escape(title)))
    return "<p style='margin:0 0 8px 0; color:%s'>%s %s</p>" % (
        MUTED, escape(i18n.text("summary", lang) % len(findings)), " · ".join(names))


def _normalize_markdown(text):
    """Put inline " - **item**" runs on their own lines so they render as a list."""
    return re.sub(r"[ \t]+-[ \t]+(?=\*\*)", "\n- ", str(text or ""))


class RulesDock(QDockWidget):
    askRequested = pyqtSignal(str)
    settingsRequested = pyqtSignal()
    earlyAccessRequested = pyqtSignal()
    earlyAccessDismissed = pyqtSignal()

    def __init__(self, parent=None, lang=None):
        super().__init__("Norme Milano", parent)
        self.setObjectName("NormeMilanoDock")
        self.lang = lang or i18n.resolve("auto")
        self._articles_loaded = {}
        self._rows = {}
        self._items = {}
        self._expanded = set()
        self._findings = []
        self._errors = {}
        self._ask_allowed = False
        self._busy = False
        self._details_open = False
        self._sources = ""
        self._last_res = None
        self._last_ans = None
        self._hint = None
        self._point_status = ""
        self._answer_shown = False
        self.ASKING = self.t("asking")

        body = QWidget()
        body.setMinimumWidth(MIN_WIDTH)
        root = QVBoxLayout(body)
        root.setContentsMargins(8, 6, 8, 6)
        root.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(4)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setStyleSheet("color: %s;" % MUTED)
        top.addWidget(self.status, 1)
        self.settings_button = QToolButton()
        self.settings_button.setAutoRaise(True)
        self._set_settings_icon()
        self.settings_button.clicked.connect(self.settingsRequested.emit)
        top.addWidget(self.settings_button)
        root.addLayout(top)

        self.outside = QLabel()
        self.outside.setWordWrap(True)
        self.outside.setAlignment(enum(Qt, "AlignmentFlag", "AlignCenter"))
        self.outside.setVisible(False)
        root.addWidget(self.outside, 1)

        self.split = QSplitter(enum(Qt, "Orientation", "Vertical"))
        self.split.setChildrenCollapsible(False)
        root.addWidget(self.split, 1)

        # 1. constraints
        self.findings = self._browser(150)
        self.sec_findings, self.head_findings = self._section(self.findings)
        # 2. articles
        self.articles = QTreeWidget()
        self.articles.setHeaderHidden(True)
        self.articles.setWordWrap(False)
        self.articles.setTextElideMode(enum(Qt, "TextElideMode", "ElideRight"))
        self.articles.setMinimumHeight(90)
        self.articles.itemExpanded.connect(self._load_article_text)
        self.sec_articles, self.head_articles = self._section(self.articles)
        # 3. question and answer
        qbox = QWidget()
        ql = QVBoxLayout(qbox)
        ql.setContentsMargins(0, 0, 0, 0)
        ql.setSpacing(5)
        row = QHBoxLayout()
        row.setSpacing(6)
        self.question = QPlainTextEdit()
        lines = self.question.fontMetrics().lineSpacing() if hasattr(
            self.question.fontMetrics(), "lineSpacing") else 16
        try:
            self.question.setFixedHeight(int(lines) * 3 + 12)
        except TypeError:  # fake widgets in tests
            pass
        row.addWidget(self.question, 1)
        self.ask_button = QPushButton()
        self.ask_button.setDefault(True)
        self.ask_button.clicked.connect(self._on_ask)
        row.addWidget(self.ask_button, 0, enum(Qt, "AlignmentFlag", "AlignBottom"))
        ql.addLayout(row)
        self.ask_hint = QLabel("")
        self.ask_hint.setWordWrap(True)
        self.ask_hint.setStyleSheet("color: %s;" % MUTED)
        self.ask_hint.linkActivated.connect(lambda _link: self.settingsRequested.emit())
        ql.addWidget(self.ask_hint)
        self.answer = self._browser(140)
        try:
            self.answer.document().setIndentWidth(14)
        except (AttributeError, TypeError):
            pass
        self.answer.setVisible(False)
        ql.addWidget(self.answer, 1)
        cap = QHBoxLayout()
        cap.setSpacing(6)
        self.answer_caption = QLabel("")
        self.answer_caption.setWordWrap(True)
        self.answer_caption.setStyleSheet("color: %s;" % MUTED)
        self.answer_caption.linkActivated.connect(self._on_anchor)
        cap.addWidget(self.answer_caption, 1)
        self.copy_button = QToolButton()
        self.copy_button.setAutoRaise(True)
        self.copy_button.clicked.connect(self._copy_answer)
        cap.addWidget(self.copy_button)
        self.caption_row = QWidget()
        self.caption_row.setLayout(cap)
        self.caption_row.setVisible(False)
        ql.addWidget(self.caption_row)
        self.sec_question, self.head_question = self._section(qbox)
        shortcut = QShortcut(QKeySequence("Ctrl+Return"), self.question)
        shortcut.activated.connect(self._on_ask)
        self._fit_question()

        # early-access strip (hidden until main.py shows it)
        self.ea_strip = QFrame()
        self.ea_strip.setObjectName("eaStrip")
        self.ea_strip.setStyleSheet(
            "QFrame#eaStrip { background: #eef4fb; border: 1px solid #c9dcf2; border-radius: 4px; }")
        strip = QHBoxLayout(self.ea_strip)
        strip.setContentsMargins(8, 3, 2, 3)
        strip.setSpacing(4)
        self.ea_label = QLabel()
        self.ea_label.setWordWrap(True)
        self.ea_label.linkActivated.connect(lambda _link: self.earlyAccessRequested.emit())
        strip.addWidget(self.ea_label, 1)
        self.ea_close = QToolButton()
        self.ea_close.setText("\u00d7")
        self.ea_close.setAutoRaise(True)
        self.ea_close.clicked.connect(self.earlyAccessDismissed.emit)
        strip.addWidget(self.ea_close)
        self.ea_strip.setVisible(False)
        root.addWidget(self.ea_strip)

        # footer: one line, details on demand
        self.sources_label = QLabel("")
        self.sources_label.setVisible(False)
        self.footer = QLabel()
        self.footer.setWordWrap(True)
        self.footer.setStyleSheet("color: %s;" % MUTED)
        self.footer.linkActivated.connect(self._toggle_details)
        root.addWidget(self.footer)
        self.details = QLabel()
        self.details.setWordWrap(True)
        self.details.setStyleSheet("color: %s;" % MUTED)
        self.details.setVisible(False)
        root.addWidget(self.details)

        self.setWidget(body)
        self.retranslate(self.lang)
        self.set_ask_enabled(False, "")

    # ------------------------------------------------------------------ building blocks
    def t(self, key):
        return i18n.text(key, self.lang)

    def _set_settings_icon(self):
        try:
            from qgis.core import QgsApplication
            self.settings_button.setIcon(QgsApplication.getThemeIcon("/mActionOptions.svg"))
        except (ImportError, AttributeError, TypeError):
            pass

    def _browser(self, min_height):
        view = QTextBrowser()
        view.setOpenLinks(False)
        view.anchorClicked.connect(self._on_anchor)
        view.setMinimumHeight(min_height)
        return view

    def _section(self, widget):
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(3)
        head = QLabel()
        head.setStyleSheet("font-weight: bold;")
        lay.addWidget(head)
        lay.addWidget(widget, 1)
        self.split.addWidget(box)
        return box, head

    def _fit_question(self):
        """The question block takes only the height it needs until an answer arrives."""
        try:
            if self._answer_shown:
                self.sec_question.setMaximumHeight(16777215)
                stretch = (3, 2, 4)
            else:
                self.sec_question.setMaximumHeight(self.sec_question.sizeHint().height())
                stretch = (5, 3, 0)
            for i, value in enumerate(stretch):
                self.split.setStretchFactor(i, value)
        except (AttributeError, TypeError):  # fake widgets in tests
            pass

    def retranslate(self, lang):
        """Switch the panel language and re-render what is on screen."""
        self.lang = lang
        self.ASKING = self.t("asking")
        self.setWindowTitle("Norme Milano")
        self.head_findings.setText(self.t("sec_constraints"))
        self.head_articles.setText(self.t("sec_articles"))
        self.head_question.setText(self.t("sec_question"))
        self.question.setPlaceholderText(self.t("placeholder"))
        self.ask_button.setText(self.t("ask"))
        self.settings_button.setToolTip(self.t("settings"))
        self.copy_button.setText(self.t("copy"))
        self.ea_label.setText("%s <a href='ea'>%s</a>" % (escape(self.t("ea_strip")),
                                                         escape(self.t("ea_link"))))
        self.ea_label.setToolTip(early_access_tip(self.t))
        self.ea_close.setToolTip(self.t("ea_close_tip"))
        self._render_footer()
        if self._last_res is not None:
            self.show_point_result(self._last_res)
            if self._last_ans is not None:
                self.show_answer(self._last_ans)
        else:
            self.set_status(self.t("idle"))
        self._render_hint()

    def _render_footer(self):
        self.footer.setText(self.t("footer_hide" if self._details_open else "footer"))
        disclaimer = prompts.DISCLAIMER_IT if self.lang == "it" else prompts.DISCLAIMER_EN
        limitation = prompts.LIMITATION_IT if self.lang == "it" else prompts.LIMITATION_EN
        parts = [escape(disclaimer), escape(limitation)]
        if self._sources:
            parts.append(escape(self.t("docs_used") % self._sources))
        self.details.setText("<small>%s</small>" % "<br><br>".join(parts))
        self.details.setVisible(self._details_open)

    def _toggle_details(self, _link=""):
        self._details_open = not self._details_open
        self._render_footer()

    def _on_anchor(self, url):
        target = url.toString() if hasattr(url, "toString") else str(url)
        if target.startswith("art:"):
            item = self._items.get(target[4:])
            if item is not None:
                self.articles.setCurrentItem(item)
                self.articles.scrollToItem(item)
            return
        if target.startswith("more:"):
            index = int(target[5:])
            self._expanded.symmetric_difference_update({index})
            self.show_findings(self._findings, self._errors)
            self.findings.scrollToAnchor("c%d" % index)
            return
        if target.startswith("goto:"):
            self.findings.scrollToAnchor("c%s" % target[5:])
            return
        if target.startswith("https://"):
            QDesktopServices.openUrl(QUrl(target))

    def _copy_answer(self):
        text = self.answer.toPlainText() if hasattr(self.answer, "toPlainText") else ""
        QApplication.clipboard().setText(text)
        self.copy_button.setText(self.t("copied"))

    # ------------------------------------------------------------------ status / state
    def set_status(self, text):
        self.status.setText(text)

    def set_sources(self, text):
        """Documents (with version) behind the articles shown, listed under Details."""
        self._sources = text or ""
        self.sources_label.setText(self._sources)
        self._render_footer()

    def _show_outside(self, message):
        """Outside Milan: one centred message instead of the three sections."""
        self.split.setVisible(message is None)
        self.outside.setVisible(message is not None)
        if message is not None:
            self.outside.setText("<p><b>%s</b></p><p style='color:%s'>%s</p>" % (
                escape(self.t("outside_title")), MUTED, escape(message)))

    def set_querying(self, lat, lon):
        self._last_res = self._last_ans = None
        self.set_status("%s  ·  %s" % (self.t("querying"), self.t("point") % (lat, lon)))
        self._show_outside(None)
        self.findings.clear()
        self.articles.clear()
        self._items = {}
        self._expanded = set()
        self._hide_answer()
        self.set_sources("")

    def _hide_answer(self):
        self.answer.clear()
        self._answer_shown = False
        self.answer.setVisible(False)
        self.caption_row.setVisible(False)
        self._fit_question()

    def set_ask_enabled(self, enabled, hint=""):
        """Enable the question box; when disabled, `hint` (or the no-provider note) explains why."""
        self._ask_allowed = bool(enabled)
        self.ask_button.setEnabled(self._ask_allowed and not self._busy)
        self.question.setEnabled(self._ask_allowed)
        self._hint = None if enabled else (hint or None)
        self._render_hint()

    def set_ask_state(self, provider_ready, has_point):
        """Question box state from whether a model is set up and a point has been clicked."""
        if not provider_ready:
            self.set_ask_enabled(False, "")
        elif not has_point:
            self.set_ask_enabled(False, self.t("click_first"))
        else:
            self.set_ask_enabled(True)

    def _render_hint(self):
        text = "" if self._ask_allowed else (self._hint or self.t("no_provider"))
        self.ask_hint.setText(text)
        self.ask_hint.setVisible(bool(text))
        self._fit_question()

    def set_asking(self, busy):
        self._busy = bool(busy)
        self.ask_button.setEnabled(self._ask_allowed and not busy)
        if busy:
            self.set_status(self.ASKING)

    def set_progress(self, message):
        """Model progress line ("Trying gemini-...", "... busy, trying ..."); GUI thread only
        (the task delivers it through a queued signal). Ignored once the request is over."""
        if self._busy and message:
            self.set_status("%s\n%s" % (self.ASKING, message))

    def _on_ask(self):
        text = self.question.toPlainText().strip()
        if text and self._ask_allowed and not self._busy:
            self.askRequested.emit(text)

    # ------------------------------------------------------------------ results
    def show_point_result(self, res):
        self._last_res = res
        p = res["point"]
        errors = res.get("errors", {})
        msg = self.t("point") % (p["lat"], p["lon"])
        if res.get("all_failed"):
            msg += "  ·  " + self.t("all_failed")
        elif errors:
            msg += "  ·  " + self.t("some_failed") % (len(errors), res.get("layers_total", 0))
        self._point_status = msg
        self.set_status(msg)
        if res.get("scope_note"):
            self._show_outside(res["scope_note"])
            self.set_sources("")
            return
        self._show_outside(None)
        self.show_findings(res["findings"], errors)
        self.show_articles(res["articles"])
        self.set_sources(res.get("sources", ""))

    def show_findings(self, findings, errors=None):
        self._findings, self._errors = list(findings), dict(errors or {})
        parts = []
        if not findings:
            parts.append("<p>%s</p>" % escape(self.t("no_constraints")))
        elif len(findings) > 1:
            parts.append(summary_html(findings, self.lang))
        for i, f in enumerate(findings):
            parts.append(finding_html(f, self.lang, i, i in self._expanded))
        if errors:
            parts.append("<p style='color:%s; font-size:small'>%s: %s</p>" % (
                MUTED, escape(self.t("layer_errors")),
                escape("; ".join("%s: %s" % (n, _wrap(e)) for n, e in sorted(errors.items())))))
        self.findings.setHtml("".join(parts))

    def _group_header(self, key):
        item = QTreeWidgetItem([self.t(key).upper()])
        font = QFont()
        font.setBold(True)
        item.setFont(0, font)
        item.setForeground(0, QBrush(QColor(MUTED)))
        try:
            item.setFlags(enum(Qt, "ItemFlag", "NoItemFlags"))
        except (AttributeError, TypeError):
            pass
        return item

    def show_articles(self, rows, cited=()):
        self.articles.clear()
        self._articles_loaded = {}
        self._items = {}
        self._rows = {r["id"]: r for r in rows}
        if not rows:
            self.articles.addTopLevelItem(QTreeWidgetItem([self.t("no_articles")]))
            return
        cited = set(cited)

        def best_role(r):
            return min((ROLE_ORDER.get(x, 9) for x in (r.get("roles") or [])), default=9)

        ordered = sorted(rows, key=lambda r: (0 if r["id"] in cited else 1, best_role(r)))
        governing = [r for r in ordered if best_role(r) == 0 or r["id"] in cited]
        others = [r for r in ordered if r not in governing]
        first_cited = None
        for group_key, group in (("grp_governing", governing), ("grp_general", others)):
            if not group:
                continue
            if governing and others:
                self.articles.addTopLevelItem(self._group_header(group_key))
            for r in group:
                item = self._article_item(r, r["id"] in cited)
                self.articles.addTopLevelItem(item)
                self._items[r["id"]] = item
                if first_cited is None and r["id"] in cited:
                    first_cited = item
        if first_cited is not None:
            self.articles.setCurrentItem(first_cited)
            self.articles.scrollToItem(first_cited)

    def _article_item(self, r, is_cited):
        roles = list(r.get("roles") or [])
        label = "%s – %s" % (short_ref(r["id"], self.lang) if _parse_ref(r["id"])
                                  else (r.get("cite") or "Art. %s" % r.get("number")),
                                  r.get("title", ""))
        if is_cited:
            label = "✓ " + label
        item = QTreeWidgetItem([label])
        tips = [self.t("role_" + x) for x in roles if ("role_" + x) in i18n.STRINGS]
        if is_cited:
            tips.insert(0, self.t("role_cited"))
        if r.get("normative") is False:
            tips.append(self.t("role_explanatory"))
        full = "%s – %s" % (r.get("cite") or label, r.get("title", ""))
        item.setToolTip(0, "%s\n%s" % (full, ", ".join(dict.fromkeys(tips))))
        font = QFont()
        if is_cited:
            item.setForeground(0, QBrush(QColor(ACCENT)))
            font.setBold(True)
        elif "governing" not in roles and "general" not in roles:
            font.setItalic(True)
            item.setForeground(0, QBrush(QColor(MUTED)))
        item.setFont(0, font)
        item.setData(0, enum(Qt, "ItemDataRole", "UserRole"), r["id"])
        child = QTreeWidgetItem([""])  # placeholder, text widget is built on first expand
        item.addChild(child)
        return item

    def _load_article_text(self, item):
        rid = item.data(0, enum(Qt, "ItemDataRole", "UserRole"))
        row = self._rows.get(rid)
        if row is None or rid in self._articles_loaded:
            return
        self._articles_loaded[row["id"]] = True
        child = item.child(0)
        link = _source_link(row.get("source_url"), self.t("open_publication"))
        if link:
            edit = QTextBrowser()
            edit.setOpenExternalLinks(True)
            pages = row.get("pages") or []
            meta = [escape(str(row.get("version_date") or ""))]
            if pages:
                meta.append(escape(self.t("pages") % "–".join(map(str, dict.fromkeys(pages)))))
            meta.append(link)
            edit.setHtml("<p style='color:%s'>%s</p><p>%s</p>" % (
                MUTED, " · ".join(x for x in meta if x),
                escape(row["text"]).replace("\n", "<br>")))
        else:
            edit = QPlainTextEdit(row["text"])
            edit.setReadOnly(True)
        edit.setMinimumHeight(220)
        child.setSizeHint(0, QSize(0, 230))
        self.articles.setItemWidget(child, 0, edit)

    def show_answer(self, ans):
        self._last_ans = ans
        parts = []
        if ans.get("source_check") == "review":
            parts.append("<p style='background-color:#fff1c2; color:#6b4a00'>&nbsp;%s</p>"
                         % escape(self.t("check_sources")))
        text = ans.get("answer_it") if self.lang == "it" else ans.get("answer_en")
        text = text or ans.get("answer_en") or ans.get("answer_it") or ""
        html = mdlite.to_html(_normalize_markdown(tidy_text(text, self.lang)))
        parts.append(re.sub(r"<p>\s*</p>", "", html))
        cited = ans.get("cited_articles") or []
        if evidence := ans.get("evidence"):
            linked = {row["id"]: row for row in ans.get("articles", [])}
            parts.append("<p style='margin-top:8px'><b>%s</b></p>" % escape(self.t("passages")))
            for item in evidence:
                row = linked.get(item["article_id"], {})
                citation = short_ref(item["article_id"], self.lang)
                source = _source_link(row.get("source_url"), citation) or escape(citation)
                parts.append("<p style='margin:2px 0 6px 0'>%s<br><i>%s</i></p>" % (
                    source, escape(item["quote"])))
        if ans.get("rejected_citations"):
            parts.append("<p><b>%s</b></p>" % escape(
                self.t("rejected") % ", ".join(ans["rejected_citations"])))
        if ans.get("parse_error"):
            parts.append("<p>%s</p>" % escape(self.t("parse_error")))
        for w in ans.get("warnings", []):
            parts.append("<p><i>%s</i></p>" % escape(w))
        self.answer.setHtml("".join(parts))
        if self._point_status:
            self.set_status(self._point_status)  # replace "Preparing the answer…"
        self._answer_shown = True
        self.answer.setVisible(True)
        caption = self.t("answered_by") % (
            escape(str(ans.get("model", "?"))),
            compact_refs(cited, self.lang) if cited else escape(self.t("none")))
        if ans.get("fallback_model"):
            caption += "<br><span style='color:#6b4a00'>%s</span>" % escape(self.t("fallback_note"))
        self.answer_caption.setText(caption)
        self.copy_button.setText(self.t("copy"))
        self.caption_row.setVisible(True)
        self._fit_question()
        if ans.get("articles"):
            self.show_articles(ans["articles"], cited=cited)
        if ans.get("sources"):
            self.set_sources(ans["sources"])

    def show_early_access(self, visible):
        self.ea_strip.setVisible(bool(visible))

    def show_error(self, text):
        self.set_status(text)
