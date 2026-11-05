"""Dock panel: constraints found, articles (expandable full text), question box + answer."""

from html import escape

from qgis.PyQt.QtCore import QSize, Qt, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QDockWidget, QGroupBox, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QSplitter,
    QTextBrowser, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from ._compat import enum, prompts

MAX_VALUE_CHARS = 80


def _wrap(text):
    return " ".join(str(text).split())


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
                       ("candidate_articles", "Candidate articles (uncertain)")):
        if f.get(key):
            lines.append("%s: %s" % (title, ", ".join("Art. %s" % n for n in f[key])))
    if f.get("why"):
        lines.append("Why: " + _wrap(f["why"]))
    if f.get("note"):
        lines.append("Note: " + _wrap(f["note"]))
    if f.get("verify"):
        lines.append("VERIFY: this link is uncertain, not confirmed by a human.")
    ext = f.get("external_rule")
    if ext:
        lines.append("External rule (outside the NTA%s): %s" % (
            ", unverified" if ext.get("verify") else "", _wrap(ext.get("text", ""))))
    return head, lines


class RulesDock(QDockWidget):
    askRequested = pyqtSignal(str)
    settingsRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Norme Milano", parent)
        self.setObjectName("NormeMilanoDock")
        self._articles_loaded = {}
        self._rows = {}
        self._ask_allowed = False
        body = QWidget()
        root = QVBoxLayout(body)

        self.status = QLabel("Click a point on the map / Fare clic su un punto della mappa.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        split = QSplitter(enum(Qt, "Orientation", "Vertical"))
        root.addWidget(split, 1)

        # 1. findings
        box1 = QGroupBox("Vincoli / Constraints found")
        l1 = QVBoxLayout(box1)
        self.findings = QTreeWidget()
        self.findings.setHeaderHidden(True)
        self.findings.setWordWrap(True)
        l1.addWidget(self.findings)
        split.addWidget(box1)

        # 2. articles
        box2 = QGroupBox("Articoli / Articles")
        l2 = QVBoxLayout(box2)
        self.articles = QTreeWidget()
        self.articles.setHeaderHidden(True)
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

    def set_asking(self, busy):
        self.ask_button.setEnabled(self._ask_allowed and not busy)
        if busy:
            self.set_status("Asking the model... / Interrogazione del modello in corso...")

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

    def show_findings(self, findings, errors=None):
        self.findings.clear()
        if not findings:
            self.findings.addTopLevelItem(QTreeWidgetItem(
                ["No planning constraint or zone found at this point."]))
        for f in findings:
            head, lines = finding_summary(f)
            item = QTreeWidgetItem([head])
            item.setToolTip(0, head)
            for line in lines:
                child = QTreeWidgetItem([line])
                child.setToolTip(0, line)
                item.addChild(child)
            self.findings.addTopLevelItem(item)
        for name, err in sorted((errors or {}).items()):
            item = QTreeWidgetItem(["Layer error: %s" % name])
            item.setToolTip(0, str(err))
            item.addChild(QTreeWidgetItem([str(err)]))
            self.findings.addTopLevelItem(item)
        self.findings.expandAll()

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
            label = "Art. %s - %s  <%s>%s" % (
                r["number"], r["title"], roles, "  [cited]" if r["id"] in cited else "")
            item = QTreeWidgetItem([label])
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
            "<p><b>Risposta (IT)</b><br>%s</p>" % escape(ans["answer_it"]).replace("\n", "<br>"),
            "<p><b>Answer (EN)</b><br>%s</p>" % escape(ans["answer_en"]).replace("\n", "<br>"),
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

    def show_error(self, text):
        self.set_status(text)
