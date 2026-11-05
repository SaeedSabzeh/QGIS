"""Settings storage, Gemini key handling (QgsAuthManager) and the settings / first-run dialog.

Non-secret settings live in QgsSettings under "norme_milano/". The Gemini API key is stored ONLY
in the encrypted QGIS authentication database (an auth config of method "Basic" whose password
is the key); QgsSettings keeps just the auth config id.
"""

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
from ._compat import enum, llm, pipeline

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
AUTH_HELP = (
    "The key is stored in the QGIS encrypted authentication database, which needs a master "
    "password: set one in Settings > Options > Authentication, then try again. / La chiave "
    "e salvata nel database di autenticazione cifrato di QGIS, che richiede una password "
    "principale: impostarla in Impostazioni > Opzioni > Autenticazione."
)
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


def is_ask_available(settings):
    """Gemini key stored, or Ollama chosen."""
    if settings["provider"] == "ollama":
        return True
    return settings["provider"] == "gemini" and bool(settings.get("authcfg"))


# --------------------------------------------------------------------------- key in auth DB
def _auth_manager():
    am = QgsApplication.authManager()
    if am is None or am.isDisabled():
        raise KeyStoreError("The QGIS authentication system is not available. " + AUTH_HELP)
    if not am.masterPasswordIsSet() and not am.setMasterPassword(True):
        raise KeyStoreError("The authentication master password is not set. " + AUTH_HELP)
    return am


def _ok(result):
    return bool(result[0] if isinstance(result, tuple) else result)


def store_gemini_key(key, authcfg=""):
    """Save `key` in the auth DB (updating `authcfg` when it exists). Returns the auth config id."""
    key = (key or "").strip()
    if not key:
        raise KeyStoreError("Empty key.")
    am = _auth_manager()
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
    if not _ok(am.storeAuthenticationConfig(cfg)) or not cfg.id():
        raise KeyStoreError("Could not store the key in the authentication database. " + AUTH_HELP)
    return cfg.id()


def read_gemini_key(authcfg):
    """Return the stored key, or raise KeyStoreError. Call on the main thread."""
    if not authcfg:
        raise KeyStoreError("No Gemini key configured.")
    am = _auth_manager()
    cfg = QgsAuthMethodConfig()
    if not _ok(am.loadAuthenticationConfig(authcfg, cfg, True)):
        raise KeyStoreError("The stored Gemini key could not be read. Enter it again in Settings.")
    key = cfg.config("password")
    if not key:
        raise KeyStoreError("The stored Gemini key is empty. Enter it again in Settings.")
    return key


def remove_gemini_key(authcfg):
    if not authcfg:
        return
    try:
        _auth_manager().removeAuthenticationConfig(authcfg)
    except KeyStoreError:
        pass


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
        self.gemini_key.setPlaceholderText(
            "stored (leave empty to keep it)" if s["authcfg"] else "paste your Gemini API key")
        form.addRow("Gemini API key", self.gemini_key)
        link = QLabel('<a href="%s">Create a Gemini key (Google AI Studio)</a>' % GEMINI_KEY_URL)
        link.setOpenExternalLinks(True)
        form.addRow("", link)
        self.remove_key = QPushButton("Remove stored key")
        self.remove_key.setEnabled(bool(s["authcfg"]))
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
        self.remove_key.setEnabled(False)
        self.gemini_key.setPlaceholderText("paste your Gemini API key")
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
                s["authcfg"] = store_gemini_key(typed, s["authcfg"])
            except KeyStoreError as exc:
                QMessageBox.warning(self, "Norme Milano", str(exc))
                return  # stay open; the key was not written anywhere
            self.gemini_key.clear()
        s["first_run_done"] = True
        save_settings(s)
        self._settings = s
        super().accept()

    def done(self, result):
        if self._test_task is not None:
            try:
                self._test_task.cancel()
            except Exception:
                pass
        super().done(result)
