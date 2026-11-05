"""Dock panel: constraints found, articles (expandable full text), question box + answer."""

from html import escape

from qgis.PyQt.QtCore import QSize, Qt, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QDockWidget,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ._compat import enum, mdlite, prompts, retrieval

MAX_VALUE_CHARS = 80
MIN_WIDTH = 320


def _wrap(text):
    return " ".join(str(text).split())


def _refs(ids):
    """"Piano dei Servizi \u2013 art. 11, Piano delle Regole \u2013 art. 8" for a list of ids."""
    return ", ".join(retrieval.ref_label(n) for n in ids)


def finding_summary(f):
    """(headline, [detail lines]) for a finding: category, key values, VERIFY, notes."""
    values = ", ".join("%s=%s" % (k, v) for k, v in f.get("values", {}).items()
                       if k != "SCHEDA_NEW")
    head = f.get("label") or f.get("category") or f.get("layer", "")
    if values:
        head += " (%s)" % values[:MAX_VALUE_CHARS * 3]
    if f.get("verify"):
        head += "  [VERIFY]"
    lines = []
    for key, title in (("articles", "Governing articles / Articoli"),
                       ("general_articles", "General articles"),
                       ("explanatory_articles", "Explanatory sections (non-normative)"),
                       ("candidate_articles", "Candidate articles (uncertain)")):
        if f.get(key):
            lines.append("%s: %s" % (title, _refs(f[key])))
    if f.get("why"):
        lines.append("Why: " + _wrap(f["why"]))
    if f.get("note"):
        lines.append("Note: " + _wrap(f["note"]))
    if f.get("verify"):
        lines.append("VERIFY: this link is uncertain, not confirmed by a human.")
    ext = f.get("external_rule")
    if ext:
        lines.append("External rule (outside the PGT texts%s): %s" % (
            ", unverified" if ext.get("verify") else "", _wrap(ext.get("text", ""))))
    return head, lines


def finding_html(f):
    """Rich-text block for one finding (all text escaped, long text wraps)."""
    values = ", ".join("%s=%s" % (k, v) for k, v in f.get("values", {}).items()
                       if k != "SCHEDA_NEW")
    head = f.get("label") or f.get("category") or f.get("layer", "")
    para = "<p style='margin-top:0; margin-bottom:2px'>"
    out = ["<p style='margin-top:8px; margin-bottom:2px'><b>%s</b>" % escape(str(head))]
    if values:
        out.append(" (%s)" % escape(values[:MAX_VALUE_CHARS * 3]))
    if f.get("verify"):
        out.append(" <span style='background-color:#ffe08a; color:#5a3b00'>"
                   "&nbsp;<b>VERIFY</b>&nbsp;</span>")
    out.append("</p>")
    for key, title in (("articles", "Governing articles / Articoli"),
                       ("general_articles", "General articles"),
                       ("explanatory_articles", "Explanatory sections (non-normative)"),
                       ("candidate_articles", "Candidate articles (uncertain)")):
        if f.get(key):
            out.append("%s<i>%s:</i> %s</p>" % (para, escape(title), escape(_refs(f[key]))))
    if f.get("why"):
        out.append("%s<b>Why:</b> %s</p>" % (para, escape(_wrap(f["why"]))))
    if f.get("note"):
        out.append("%s<b>Note:</b> %s</p>" % (para, escape(_wrap(f["note"]))))
    if f.get("verify"):
        out.append(para + "<b>VERIFY:</b> this link is uncertain, not confirmed by a human.</p>")
    ext = f.get("external_rule")
    if ext:
        out.append("%s<b>External rule (outside the PGT texts%s):</b> %s</p>" % (
            para, ", unverified" if ext.get("verify") else "",
            escape(_wrap(ext.get("text", "")))))
    return "".join(out) + "<hr>"


class RulesDock(QDockWidget):
    askRequested = pyqtSignal(str)
    settingsRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Norme Milano", parent)
        self.setObjectName("NormeMilanoDock")
        self._articles_loaded = {}
        self._rows = {}
        self._ask_allowed = False
        self._busy = False
        body = QWidget()
        body.setMinimumWidth(MIN_WIDTH)
        root = QVBoxLayout(body)

        self.status = QLabel("Click a point on the map / Fare clic su un punto della mappa.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        split = QSplitter(enum(Qt, "Orientation", "Vertical"))
        root.addWidget(split, 1)

        # 1. findings
        box1 = QGroupBox("Vincoli / Constraints found")
        l1 = QVBoxLayout(box1)
        self.findings = QTextBrowser()
        self.findings.setOpenExternalLinks(False)
        l1.addWidget(self.findings)
        split.addWidget(box1)

        # 2. articles
        box2 = QGroupBox("Articoli / Articles")
        l2 = QVBoxLayout(box2)
        self.articles = QTreeWidget()
        self.articles.setHeaderHidden(True)
        self.articles.setWordWrap(True)
        self.articles.setUniformRowHeights(False)
        self.articles.setTextElideMode(enum(Qt, "TextElideMode", "ElideNone"))
        self.articles.itemExpanded.connect(self._load_article_text)
        l2.addWidget(self.articles)
        split.addWidget(box2)

        # 3. question
        box3 = QGroupBox("Domanda / Question")
        l3 = QVBoxLayout(box3)
        self.question = QPlainTextEdit()
        self.question.setPlaceholderText("Ask about the rules at this point (IT or EN)...")
        self.question.setMaximumHeight(70)
        l3.addWidget(self.question)
        row = QHBoxLayout()
        self.ask_button = QPushButton("Ask / Chiedi")
        self.ask_button.clicked.connect(self._on_ask)
        row.addWidget(self.ask_button)
        self.settings_button = QPushButton("Settings...")
        self.settings_button.clicked.connect(self.settingsRequested.emit)
        row.addWidget(self.settings_button)
        row.addStretch(1)
        l3.addLayout(row)
        self.ask_hint = QLabel("")
        self.ask_hint.setWordWrap(True)
        l3.addWidget(self.ask_hint)
        self.answer = QTextBrowser()
        self.answer.setOpenExternalLinks(False)
        l3.addWidget(self.answer)
        split.addWidget(box3)

        # permanent footer
        self.sources_label = QLabel("")
        self.sources_label.setWordWrap(True)
        root.addWidget(self.sources_label)
        footer = QLabel("<small>%s<br>%s<br>%s<br>%s</small>" % tuple(escape(t) for t in (
            prompts.DISCLAIMER_EN, prompts.DISCLAIMER_IT, prompts.LIMITATION_EN,
            prompts.LIMITATION_IT)))
        footer.setWordWrap(True)
        root.addWidget(footer)

        self.setWidget(body)
        self.set_ask_enabled(False, "")

    # ------------------------------------------------------------------ status / state
    def set_status(self, text):
        self.status.setText(text)

    def set_sources(self, text):
        """Line naming the documents (with version) behind the articles shown."""
        self.sources_label.setText(
            "<small>Documents used: %s.</small>" % escape(text) if text else "")

    def set_querying(self, lat, lon):
        self.status.setText("Querying / Interrogazione in corso... (lat %.5f, lon %.5f)"
                            % (lat, lon))
        self.findings.clear()
        self.articles.clear()
        self.answer.clear()

    def set_ask_enabled(self, enabled, hint=""):
        self._ask_allowed = bool(enabled)
        self.ask_button.setEnabled(self._ask_allowed)
        self.question.setEnabled(self._ask_allowed)
        self.ask_hint.setText("" if enabled else hint or (
            "Questions need a provider: open Settings and choose Gemini (with a key) or Ollama. "
            "/ Le domande richiedono un fornitore: aprire Impostazioni."))

    ASKING = "Asking the model... / Interrogazione del modello in corso..."

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
        if text:
            self.askRequested.emit(text)

    # ------------------------------------------------------------------ results
    def show_point_result(self, res):
        p = res["point"]
        errors = res.get("errors", {})
        msg = "Point lat %.5f, lon %.5f. " % (p["lat"], p["lon"])
        if res.get("all_failed"):
            msg += "All map services failed (network or proxy?). "
        elif errors:
            msg += "%d of %d layers failed (non-fatal): %s. " % (
                len(errors), res.get("layers_total", 0), ", ".join(sorted(errors)))
        self.set_status(msg.strip())
        self.show_findings(res["findings"], errors)
        self.show_articles(res["articles"])
        self.set_sources(res.get("sources", ""))

    def show_findings(self, findings, errors=None):
        parts = []
        if not findings:
            parts.append("<p>No planning constraint or zone found at this point.</p>")
        for f in findings:
            parts.append(finding_html(f))
        if errors:
            parts.append("<p><small><span style='color:#777'>Layer errors:</span></small></p><ul>")
            for name, err in sorted(errors.items()):
                parts.append("<li><small><span style='color:#777'>%s: %s</span></small></li>"
                             % (escape(str(name)), escape(_wrap(err))))
            parts.append("</ul>")
        self.findings.setHtml("".join(parts))

    def show_articles(self, rows, cited=()):
        self.articles.clear()
        self._articles_loaded = {}
        self._rows = {r["id"]: r for r in rows}
        if not rows:
            self.articles.addTopLevelItem(QTreeWidgetItem(["No mapped articles."]))
            return
        cited = set(cited)
        for r in rows:
            roles = ", ".join(r["roles"])
            tags = roles + ("; cited" if r["id"] in cited else "")
            cite = r.get("cite") or ("Art. %s" % r.get("number"))
            if r.get("normative") is False:
                tags += "; explanatory, non-normative"
            label = "%s \u2013 %s\n[%s]" % (cite, r["title"], tags)
            item = QTreeWidgetItem([label])
            item.setToolTip(0, label)
            item.setData(0, enum(Qt, "ItemDataRole", "UserRole"), r["id"])
            child = QTreeWidgetItem([""])  # placeholder, text widget is built on first expand
            item.addChild(child)
            self.articles.addTopLevelItem(item)

    def _load_article_text(self, item):
        rid = item.data(0, enum(Qt, "ItemDataRole", "UserRole"))
        row = self._rows.get(rid)
        if row is None or rid in self._articles_loaded:
            return
        self._articles_loaded[row["id"]] = True
        child = item.child(0)
        edit = QPlainTextEdit(row["text"])
        edit.setReadOnly(True)
        edit.setMinimumHeight(220)
        child.setSizeHint(0, QSize(0, 230))
        self.articles.setItemWidget(child, 0, edit)

    def show_answer(self, ans):
        parts = [
            "<p><b>Risposta (IT)</b></p>%s" % mdlite.to_html(ans["answer_it"]),
            "<p><b>Answer (EN)</b></p>%s" % mdlite.to_html(ans["answer_en"]),
            "<p><b>Model:</b> %s<br><b>Cited articles:</b> %s</p>" % (
                escape(str(ans.get("model", "?"))),
                escape(", ".join(ans["cited_articles"]) or "none")),
        ]
        if ans.get("rejected_citations"):
            parts.append("<p><b>WARNING:</b> the model cited articles that were not supplied; "
                         "they were removed: %s</p>" % escape(", ".join(ans["rejected_citations"])))
        if ans.get("parse_error"):
            parts.append("<p><b>WARNING:</b> the model reply was not valid JSON; shown as raw "
                         "text, citations dropped.</p>")
        for w in ans.get("warnings", []):
            parts.append("<p><i>%s</i></p>" % escape(w))
        self.answer.setHtml("".join(parts))
        self.show_articles(ans.get("articles", []), cited=ans["cited_articles"])
        self.set_status("Answered by %s." % ans.get("model", "?"))
        self.set_sources(ans.get("sources", ""))

    def show_error(self, text):
        self.set_status(text)
