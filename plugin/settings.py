"""Settings storage, Gemini key handling and the settings / first-run dialog.

Non-secret settings live in QgsSettings under "norme_milano/". The Gemini API key is looked up in
this order: (a) the encrypted QGIS authentication database (an auth config of method "Basic",
used only when the auth system works AND a master password is already set - the plugin never asks
for or creates one), (b) the plugin settings in the QGIS profile (plain text, key
"norme_milano/gemini_key"), (c) the GEMINI_API_KEY environment variable (read-only).
Saving uses (a) when available and silently falls back to (b). The key is never logged.
"""

import os

from qgis.core import QgsApplication, QgsAuthMethodConfig, QgsSettings
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from . import net, tasks
from ._compat import enum, llm, log, pipeline

PREFIX = "norme_milano/"
GEMINI_KEY_URL = "https://aistudio.google.com/apikey"
PROVIDERS = (("none", "Nessuno / None (constraints and articles only)"),
             ("gemini", "Gemini (Google)"),
             ("ollama", "Ollama (local)"))
DEFAULTS = {
    "provider": "none",
    "gemini_model": llm.DEFAULT_GEMINI_MODEL,
    "ollama_url": llm.DEFAULT_OLLAMA_URL,
    "ollama_model": llm.DEFAULT_OLLAMA_MODEL,
    "authcfg": "",
    "first_run_done": False,
}
PRIVACY_NOTE = (
    "Privacy: on the free Gemini tier Google may use prompts to improve its products. The "
    "question, the findings and the article texts are sent to the provider; with Ollama nothing "
    "leaves your machine. / Nel piano gratuito di Gemini, Google puo usare i prompt per "
    "migliorare i suoi prodotti."
)
KEY_SETTING = PREFIX + "gemini_key"
ENV_VAR = "GEMINI_API_KEY"
NOTE_PLAIN = ("Stored in your QGIS profile settings (not encrypted). To encrypt it, set a QGIS "
              "master password in Options > Authentication.")
NOTE_AUTH = "Stored encrypted in the QGIS password store."
NOTE_ENV = "Using %s from the environment." % ENV_VAR
NOTE_NONE_AUTH = "Will be stored encrypted in the QGIS password store."
REENTER_HELP = ("The stored Gemini key could not be read (the QGIS password store is locked or "
                "unavailable). Enter the key again in Settings.")
AUTH_CONFIG_NAME = "Norme Milano - Gemini API key"


class KeyStoreError(Exception):
    """The key could not be stored or read (message is safe to show; never contains the key)."""


# --------------------------------------------------------------------------- plain settings
def load_settings():
    qs = QgsSettings()
    out = {}
    for name, default in DEFAULTS.items():
        value = qs.value(PREFIX + name, default)
        if isinstance(default, bool):
            value = value in (True, "true", "True", 1, "1")
        elif value is None or (value == "" and default != ""):
            value = default
        out[name] = value
    if out["provider"] not in dict(PROVIDERS):
        out["provider"] = "none"
    return out


def save_settings(values):
    qs = QgsSettings()
    for name in DEFAULTS:
        if name in values:
            qs.setValue(PREFIX + name, values[name])


def _plain_key():
    value = QgsSettings().value(KEY_SETTING, "")
    return str(value).strip() if value else ""


def _env_key():
    return os.environ.get(ENV_VAR, "").strip()


def is_ask_available(settings):
    """Ollama chosen, or Gemini with a key from any of auth DB / profile settings / environment.

    Never touches the auth manager (called from initGui): only checks that a key is recorded.
    """
    if settings["provider"] == "ollama":
        return True
    return settings["provider"] == "gemini" and bool(
        settings.get("authcfg") or _plain_key() or _env_key())


# --------------------------------------------------------------------------- key storage
def auth_store_ready():
    """True when the QGIS auth system works and a master password is already set (no prompt)."""
    try:
        am = QgsApplication.authManager()
        return bool(am is not None and not am.isDisabled() and am.masterPasswordIsSet())
    except (AttributeError, RuntimeError) as exc:
        log("auth manager unavailable: %s" % type(exc).__name__)
        return False


def _ok(result):
    return bool(result[0] if isinstance(result, tuple) else result)


def _store_in_auth(key, authcfg):
    """Returns the auth config id, or "" when the auth store could not take the key."""
    try:
        am = QgsApplication.authManager()
        cfg = QgsAuthMethodConfig()
        cfg.setMethod("Basic")
        cfg.setName(AUTH_CONFIG_NAME)
        cfg.setConfig("username", "gemini-api-key")
        cfg.setConfig("password", key)
        if authcfg:
            cfg.setId(authcfg)
            if _ok(am.updateAuthenticationConfig(cfg)):
                return authcfg
            cfg.setId("")  # the stored config vanished: create a new one
        if _ok(am.storeAuthenticationConfig(cfg)) and cfg.id():
            return cfg.id()
    except (AttributeError, RuntimeError) as exc:
        log("could not use the auth store: %s" % type(exc).__name__)
    return ""


def store_gemini_key(key, authcfg=""):
    """Save `key`. Returns (authcfg, where): where is "auth" (encrypted; authcfg is its id) or
    "settings" (plain text in the QGIS profile; authcfg is ""). Falls back silently."""
    key = (key or "").strip()
    if not key:
        raise KeyStoreError("Empty key.")
    if auth_store_ready():
        new_id = _store_in_auth(key, authcfg)
        if new_id:
            QgsSettings().setValue(KEY_SETTING, "")  # no stale plain copy
            return new_id, "auth"
        log("auth store refused the key; using profile settings")
    QgsSettings().setValue(KEY_SETTING, key)
    return "", "settings"


def _read_from_auth(authcfg):
    if not authcfg or not auth_store_ready():
        return ""
    try:
        cfg = QgsAuthMethodConfig()
        if _ok(QgsApplication.authManager().loadAuthenticationConfig(authcfg, cfg, True)):
            return (cfg.config("password") or "").strip()
    except (AttributeError, RuntimeError) as exc:
        log("could not read the auth store: %s" % type(exc).__name__)
    return ""


def read_gemini_key(authcfg=""):
    """Return the key (auth store, then profile settings, then environment) or raise
    KeyStoreError. Never prompts for the master password. Call on the main thread."""
    key = _read_from_auth(authcfg) or _plain_key() or _env_key()
    if key:
        return key
    if authcfg:
        raise KeyStoreError(REENTER_HELP)
    raise KeyStoreError("No Gemini key configured. Enter it in Settings.")


def key_location(authcfg=""):
    """Where the key comes from: "auth", "auth-locked", "settings", "env" or "none" (for the UI)."""
    if authcfg and _read_from_auth(authcfg):
        return "auth"
    if authcfg and not _plain_key() and not _env_key():
        return "auth-locked"
    if _plain_key():
        return "settings"
    return "env" if _env_key() else "none"


def remove_gemini_key(authcfg=""):
    """Remove the key from the auth store and the profile settings (the env var is untouched)."""
    if authcfg and auth_store_ready():
        try:
            QgsApplication.authManager().removeAuthenticationConfig(authcfg)
        except (AttributeError, RuntimeError) as exc:
            log("could not remove the auth config: %s" % type(exc).__name__)
    QgsSettings().setValue(KEY_SETTING, "")


# --------------------------------------------------------------------------- client
def build_client(settings, api_key=None, transport=None):
    """LLM client for `settings` (a load_settings() dict); raises llm.LLMError if unusable."""
    if settings["provider"] == "ollama":
        return llm.make_client("ollama", settings["ollama_model"], base_url=settings["ollama_url"],
                               transport=transport)
    return llm.make_client("gemini", settings["gemini_model"], api_key=api_key,
                           transport=transport)


# --------------------------------------------------------------------------- dialog
class SettingsDialog(QDialog):
    def __init__(self, parent=None, first_run=False):
        super().__init__(parent)
        self.setWindowTitle("Norme Milano - Impostazioni / Settings")
        self._settings = load_settings()
        self._test_task = None
        s = self._settings

        layout = QVBoxLayout(self)
        if first_run:
            welcome = QLabel(
                "<b>Benvenuto / Welcome.</b> Without any provider the plugin shows the constraints "
                "and the mapped articles. To ask free-text questions choose Gemini or Ollama.")
            welcome.setWordWrap(True)
            layout.addWidget(welcome)

        form = QFormLayout()
        self.provider = QComboBox()
        for value, label in PROVIDERS:
            self.provider.addItem(label, value)
        self.provider.setCurrentIndex(max(0, self.provider.findData(s["provider"])))
        form.addRow("Fornitore / Provider", self.provider)

        self.gemini_model = QLineEdit(s["gemini_model"])
        form.addRow("Gemini model", self.gemini_model)
        self.gemini_key = QLineEdit()
        self.gemini_key.setEchoMode(enum(QLineEdit, "EchoMode", "Password"))
        form.addRow("Gemini API key", self.gemini_key)
        self.key_note = QLabel("")
        self.key_note.setWordWrap(True)
        form.addRow("", self.key_note)
        link = QLabel('<a href="%s">Create a Gemini key (Google AI Studio)</a>' % GEMINI_KEY_URL)
        link.setOpenExternalLinks(True)
        form.addRow("", link)
        self.remove_key = QPushButton("Remove stored key")
        self.remove_key.clicked.connect(self._remove_key)
        form.addRow("", self.remove_key)

        self.ollama_url = QLineEdit(s["ollama_url"])
        form.addRow("Ollama base URL", self.ollama_url)
        self.ollama_model = QLineEdit(s["ollama_model"])
        form.addRow("Ollama model", self.ollama_model)
        layout.addLayout(form)

        privacy = QLabel(PRIVACY_NOTE)
        privacy.setWordWrap(True)
        layout.addWidget(privacy)

        row = QHBoxLayout()
        self.test_button = QPushButton("Test connection / Prova la connessione")
        self.test_button.clicked.connect(self._test_connection)
        row.addWidget(self.test_button)
        self.test_result = QLabel("")
        self.test_result.setWordWrap(True)
        row.addWidget(self.test_result, 1)
        layout.addLayout(row)

        buttons = QDialogButtonBox(
            enum(QDialogButtonBox, "StandardButton", "Ok")
            | enum(QDialogButtonBox, "StandardButton", "Cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.provider.currentIndexChanged.connect(self._sync_enabled)
        self._sync_enabled()
        self._refresh_key_ui()

    # -- helpers
    def _provider(self):
        return self.provider.currentData()

    def _sync_enabled(self, *_):
        gem = self._provider() == "gemini"
        oll = self._provider() == "ollama"
        for w in (self.gemini_model, self.gemini_key):
            w.setEnabled(gem)
        for w in (self.ollama_url, self.ollama_model):
            w.setEnabled(oll)
        self.test_button.setEnabled(gem or oll)

    def _refresh_key_ui(self):
        """Placeholder, storage note and Remove button from the current key state."""
        where = key_location(self._settings["authcfg"])
        stored = where in ("auth", "auth-locked", "settings")
        self.gemini_key.setPlaceholderText(
            "stored (leave empty to keep it)" if stored else "paste your Gemini API key")
        if where == "auth":
            note = NOTE_AUTH
        elif where == "auth-locked":
            note = REENTER_HELP
        elif where == "settings":
            note = NOTE_PLAIN
        elif where == "env":
            note = NOTE_ENV
        else:
            note = NOTE_NONE_AUTH if auth_store_ready() else NOTE_PLAIN
        self.key_note.setText(note)
        self.remove_key.setEnabled(bool(self._settings["authcfg"]) or bool(_plain_key()))

    def _collect(self):
        s = dict(self._settings)
        s.update(provider=self._provider(),
                 gemini_model=self.gemini_model.text().strip() or DEFAULTS["gemini_model"],
                 ollama_url=self.ollama_url.text().strip() or DEFAULTS["ollama_url"],
                 ollama_model=self.ollama_model.text().strip() or DEFAULTS["ollama_model"])
        return s

    def _remove_key(self):
        remove_gemini_key(self._settings["authcfg"])
        self._settings["authcfg"] = ""
        save_settings(self._settings)
        self._refresh_key_ui()
        self.test_result.setText("Stored key removed.")

    def _test_connection(self):
        s = self._collect()
        try:
            key = None
            if s["provider"] == "gemini":
                key = self.gemini_key.text().strip() or read_gemini_key(s["authcfg"])
        except KeyStoreError as exc:
            self.test_result.setText(str(exc))
            return
        self.test_button.setEnabled(False)
        self.test_result.setText("Testing... / Verifica in corso...")

        def work(is_canceled):
            client = build_client(s, key, net.make_transport(is_canceled))
            client.fallbacks = ()  # test the chosen model only
            return pipeline.check_connection(client)

        def done(model, error):
            self._test_task = None
            self.test_button.setEnabled(True)
            self.test_result.setText(("OK: %s" % model) if error is None else "Failed: %s" % error)

        self._test_task = tasks.start("Norme Milano: test connection", work, done)

    def accept(self):
        s = self._collect()
        typed = self.gemini_key.text().strip()
        if s["provider"] == "gemini" and typed:
            try:
                s["authcfg"], _where = store_gemini_key(typed, s["authcfg"])
            except KeyStoreError as exc:
                QMessageBox.warning(self, "Norme Milano", str(exc))
                return  # stay open; the key was not written anywhere
            self.gemini_key.clear()
        s["first_run_done"] = True
        save_settings(s)
        self._settings = s
        self._refresh_key_ui()
        super().accept()

    def done(self, result):
        if self._test_task is not None:
            try:
                self._test_task.cancel()
            except RuntimeError as exc:  # underlying C++ task already deleted
                log("settings dialog: task already gone (%s)" % type(exc).__name__)
        super().done(result)
