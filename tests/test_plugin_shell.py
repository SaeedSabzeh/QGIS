"""Plugin shell tests against a fake `qgis` package (QGIS itself is not needed)."""

import ast
import importlib
import json
import py_compile
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import fake_qgis  # noqa: E402
from fake_qgis import FakeNAM, FakeReply  # noqa: E402

PLUGIN_FILES = ["__init__.py", "_compat.py", "dock.py", "main.py", "map_tool.py", "net.py",
                "settings.py", "tasks.py"]
SECRET = "SECRET-KEY-123"


@pytest.fixture
def env():
    fake_qgis.install()
    plugin = importlib.import_module("plugin")
    yield plugin
    fake_qgis.uninstall()


class FakeCanvas:
    def __init__(self):
        self.tool = None

    def setMapTool(self, tool):  # noqa: N802
        self.tool = tool

    def unsetMapTool(self, tool):  # noqa: N802
        if self.tool is tool:
            self.tool = None

    def mapTool(self):  # noqa: N802
        return self.tool

    def mapSettings(self):  # noqa: N802
        return fake_qgis.Stub()

    def scene(self):
        return fake_qgis.Stub()


class FakeIface:
    def __init__(self):
        self.canvas = FakeCanvas()
        self.calls = []

    def mapCanvas(self):  # noqa: N802
        return self.canvas

    def mainWindow(self):  # noqa: N802
        return fake_qgis.Stub()

    def messageBar(self):  # noqa: N802
        return fake_qgis.Stub()

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)

        def rec(*args):
            self.calls.append((name, args))
        return rec

    def called(self, name):
        return [a for n, a in self.calls if n == name]


# ----------------------------------------------------------------------------- lifecycle
def test_import_factory_init_unload(env):
    iface = FakeIface()
    p = env.classFactory(iface)
    assert type(p).__name__ == "NormeMilanoPlugin"
    p.initGui()
    assert len(iface.called("addToolBarIcon")) == 1
    assert len(iface.called("addPluginToMenu")) == 2  # main action + settings
    assert len(iface.called("addDockWidget")) == 1
    p.run(True)
    assert iface.canvas.mapTool() is p.tool
    p.run(False)
    assert iface.canvas.mapTool() is None
    p.run(True)
    from plugin import tasks
    p.unload()
    assert len(iface.called("removeToolBarIcon")) == 1
    assert len(iface.called("removePluginMenu")) == 2
    assert len(iface.called("removeDockWidget")) == 1
    assert iface.canvas.mapTool() is None
    assert p.dock is None and p.tool is None and p.action is None
    assert not tasks._ACTIVE


def test_map_tool_click_emits_lat_lon(env):
    iface = FakeIface()
    p = env.classFactory(iface)
    p.initGui()
    got = []
    p.tool.pointQueried.connect(lambda lat, lon: got.append((lat, lon)))

    class Ev:
        def __init__(self, button):
            self._b = button

        def button(self):
            return self._b

        def pos(self):
            return fake_qgis.Stub()

    from qgis.PyQt.QtCore import Qt
    p.tool.canvasReleaseEvent(Ev(Qt.MouseButton.RightButton))
    assert got == []
    p.tool.canvasReleaseEvent(Ev(Qt.MouseButton.LeftButton))
    assert got == [(45.4642, 9.19)]  # (lat, lon), not (x, y)
    p.unload()


# ----------------------------------------------------------------------------- network
@pytest.mark.parametrize("status,transient", [
    (429, True), (500, True), (502, True), (503, True), (504, True),
    (400, False), (401, False), (403, False), (404, False)])
def test_http_status_mapping(env, status, transient):
    from plugin import net
    from plugin._compat import llm
    with pytest.raises(llm.LLMError) as ei:
        net.interpret("https://x.test/a?key=" + SECRET, status, b"nope", retry_after="7")
    err = ei.value
    assert err.status == status and err.transient is transient
    assert err.retry_after == 7.0
    assert SECRET not in str(err)


def test_no_response_is_transient_and_bad_json_is_not(env):
    from plugin import net
    from plugin._compat import llm
    with pytest.raises(llm.LLMError) as ei:
        net.interpret("https://x.test/a", 0, b"", net_error="timeout")
    assert ei.value.transient and ei.value.status is None
    with pytest.raises(llm.LLMError) as ei:
        net.interpret("https://x.test/a", 200, b"<html>")
    assert not ei.value.transient
    assert net.interpret("https://x.test/a", 200, b'{"a": 1}') == {"a": 1}


def test_transport_sends_key_in_header_only_and_retries(env):
    from plugin import net
    from plugin._compat import llm
    replies = [FakeReply(503, b"busy"), FakeReply(429, b"slow", {"Retry-After": "2"}),
               FakeReply(200, json.dumps({"candidates": [{"content": {"parts": [
                   {"text": '{"answer_it": "ok"}'}]}}]}).encode())]
    FakeNAM.responder = lambda m, req, data: replies.pop(0)
    sleeps = []
    client = llm.GeminiClient(SECRET, "m1", transport=net.make_transport(), fallbacks=(),
                              sleep=sleeps.append, max_attempts=3)
    assert "ok" in client.complete({"system": "s", "user": "u"})
    assert sleeps and sleeps[1] == 2.0  # Retry-After honoured through the adapter
    for method, req, data in FakeNAM.calls:
        assert method == "POST"
        assert SECRET not in req.url
        assert req.headers["x-goog-api-key"] == SECRET
        assert SECRET not in (data or b"").decode()


def test_transport_failure_keeps_fallback_chain(env):
    from plugin import net
    from plugin._compat import llm

    def responder(method, req, data):
        if "/models/m1:" in req.url:
            return FakeReply(503, b"overloaded")
        return FakeReply(200, json.dumps({"candidates": [{"content": {"parts": [
            {"text": "{}"}]}}]}).encode())

    FakeNAM.responder = responder
    client = llm.GeminiClient(SECRET, "m1", transport=net.make_transport(), fallbacks=("m2",),
                              sleep=lambda s: None, max_attempts=2)
    client.complete({"system": "", "user": "u"})
    assert client.last_model == "m2"


def test_fetch_cancel(env):
    from plugin import net
    FakeNAM.responder = lambda *a: FakeReply(200, b"{}")
    fetch = net.make_fetch(lambda: True)
    with pytest.raises(net.Canceled):
        fetch("https://x.test/q")


# ----------------------------------------------------------------------------- settings / key
def _auth(**kw):
    from qgis.core import QgsApplication
    am = QgsApplication.authManager()
    for k, v in kw.items():
        setattr(am, k, v)
    return am


def test_key_encrypted_when_master_password_set(env, monkeypatch):
    from qgis.core import QgsSettings

    from plugin import settings
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    s = settings.load_settings()
    assert s["provider"] == "none" and not settings.is_ask_available(s)
    authcfg, where = settings.store_gemini_key(SECRET)
    assert where == "auth" and authcfg
    s.update(provider="gemini", authcfg=authcfg)
    settings.save_settings(s)
    assert settings.is_ask_available(settings.load_settings())
    assert settings.read_gemini_key(authcfg) == SECRET
    assert settings.key_location(authcfg) == "auth"
    assert all(SECRET not in str(v) for v in QgsSettings.store.values())
    assert all(k.startswith("norme_milano/") for k in QgsSettings.store)
    assert _auth().configs[authcfg]["password"] == SECRET
    # updating keeps the same auth config id
    assert settings.store_gemini_key("other", authcfg) == (authcfg, "auth")
    settings.remove_gemini_key(authcfg)
    with pytest.raises(settings.KeyStoreError):
        settings.read_gemini_key(authcfg)


def test_disabled_auth_falls_back_to_profile_settings(env, monkeypatch):
    from qgis.core import QgsSettings

    from plugin import settings
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    _auth(disabled=True)
    authcfg, where = settings.store_gemini_key(SECRET)  # no error, no dialog
    assert (authcfg, where) == ("", "settings")
    assert QgsSettings.store["norme_milano/gemini_key"] == SECRET
    assert settings.read_gemini_key("") == SECRET
    assert settings.key_location("") == "settings"
    s = settings.load_settings()
    s["provider"] = "gemini"
    assert settings.is_ask_available(s)
    assert SECRET not in str(s)
    assert _auth().configs == {}


def test_master_password_not_set_falls_back_too(env, monkeypatch):
    from plugin import settings
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    _auth(master_set=False)
    assert not settings.auth_store_ready()
    assert settings.store_gemini_key(SECRET) == ("", "settings")
    assert settings.read_gemini_key("") == SECRET


def test_locked_auth_store_at_read_time(env, monkeypatch):
    from plugin import settings
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    authcfg, _ = settings.store_gemini_key(SECRET)
    _auth(master_set=False)  # locked later
    s = settings.load_settings()
    s.update(provider="gemini", authcfg=authcfg)
    assert settings.is_ask_available(s)  # does not touch the auth manager
    with pytest.raises(settings.KeyStoreError) as ei:
        settings.read_gemini_key(authcfg)
    assert "Enter the key again" in str(ei.value) and SECRET not in str(ei.value)
    assert settings.key_location(authcfg) == "auth-locked"
    # a profile-settings or environment key still works while the store is locked
    monkeypatch.setenv("GEMINI_API_KEY", "ENV-KEY-1")
    assert settings.read_gemini_key(authcfg) == "ENV-KEY-1"


def test_environment_key_is_read_only_fallback(env, monkeypatch):
    from qgis.core import QgsSettings

    from plugin import settings
    monkeypatch.setenv("GEMINI_API_KEY", "ENV-KEY-1")
    s = settings.load_settings()
    s["provider"] = "gemini"
    assert settings.is_ask_available(s)
    assert settings.read_gemini_key("") == "ENV-KEY-1"
    assert settings.key_location("") == "env"
    settings.remove_gemini_key("")  # cannot remove the environment variable
    assert settings.read_gemini_key("") == "ENV-KEY-1"
    # a stored key wins over the environment
    _auth(disabled=True)
    settings.store_gemini_key(SECRET)
    assert settings.read_gemini_key("") == SECRET
    assert "ENV-KEY-1" not in str(QgsSettings.store)


def test_remove_clears_both_stores(env, monkeypatch):
    from qgis.core import QgsSettings

    from plugin import settings
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    authcfg, _ = settings.store_gemini_key(SECRET)
    QgsSettings().setValue("norme_milano/gemini_key", SECRET)  # also a plain copy
    settings.remove_gemini_key(authcfg)
    assert _auth().configs == {}
    assert not QgsSettings.store["norme_milano/gemini_key"]
    with pytest.raises(settings.KeyStoreError):
        settings.read_gemini_key("")
    assert settings.key_location("") == "none"


def test_migrates_authcfg_from_0_1_0(env, monkeypatch):
    from plugin import settings
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    am = _auth()
    am.configs["old0001"] = {"password": SECRET, "method": "Basic"}
    assert settings.read_gemini_key("old0001") == SECRET
    assert settings.store_gemini_key("new-key", "old0001") == ("old0001", "auth")
    assert am.configs["old0001"]["password"] == "new-key"


def test_key_never_in_errors_or_logs(env, monkeypatch, capsys):
    import qgis.core

    from plugin import settings
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    logged = []
    qgis.core.QgsMessageLog.logMessage = lambda *a, **k: logged.append(a)
    am = _auth()

    def boom(*a, **k):
        raise RuntimeError("auth backend gone")
    am.storeAuthenticationConfig = boom
    assert settings.store_gemini_key(SECRET) == ("", "settings")  # falls back, no raise
    am.loadAuthenticationConfig = boom
    assert settings.read_gemini_key("x") == SECRET
    _auth(master_set=False)
    with pytest.raises(settings.KeyStoreError) as ei:
        settings.store_gemini_key("")
    texts = [str(ei.value)] + [str(x) for x in logged]
    out = capsys.readouterr()
    assert logged and all(SECRET not in t for t in texts + [out.out, out.err])


def test_dialog_note_and_masked_field(env, monkeypatch):
    from plugin import settings

    class Label:
        def __init__(self, text=""):
            self.text = text

        def setText(self, text):  # noqa: N802
            self.text = text

        def __getattr__(self, name):
            return lambda *a, **k: None

    monkeypatch.setattr(settings, "QLabel", Label)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    _auth(disabled=True)
    dlg = settings.SettingsDialog(None)
    assert dlg.key_note.text == settings.NOTE_PLAIN and "not encrypted" in settings.NOTE_PLAIN
    _auth(disabled=False)
    assert settings.SettingsDialog(None).key_note.text == settings.NOTE_NONE_AUTH
    monkeypatch.setenv("GEMINI_API_KEY", "ENV-KEY-1")
    assert settings.SettingsDialog(None).key_note.text == settings.NOTE_ENV
    st = settings.load_settings()
    st["authcfg"], _ = settings.store_gemini_key(SECRET)
    settings.save_settings(st)
    assert settings.SettingsDialog(None).key_note.text == settings.NOTE_AUTH


def test_initgui_does_not_touch_auth_manager(env, monkeypatch):
    am = _auth()

    def fail(*a, **k):
        raise AssertionError("auth manager touched at startup")
    for name in ("isDisabled", "masterPasswordIsSet", "setMasterPassword",
                 "loadAuthenticationConfig"):
        setattr(am, name, fail)
    p = env.classFactory(FakeIface())
    p.initGui()
    p.unload()


def test_ollama_enables_ask_without_key(env):
    from plugin import settings
    s = settings.load_settings()
    s["provider"] = "ollama"
    assert settings.is_ask_available(s)
    assert settings.build_client(s).model == s["ollama_model"]


def test_dialog_and_dock_construct(env):
    from plugin import dock, settings
    settings.SettingsDialog(None, first_run=True)
    d = dock.RulesDock(None)
    d.set_ask_enabled(True)
    head, lines = dock.finding_summary({
        "label": "X", "values": {"A": 1}, "verify": True, "articles": [3], "why": "w",
        "note": "n", "external_rule": {"text": "ext", "verify": True}})
    assert "[VERIFY]" in head and "A=1" in head
    assert any("External rule" in x and "unverified" in x for x in lines)


def test_findings_rendered_as_wrapped_html(env):
    from plugin import dock
    d = dock.RulesDock(None)
    long_note = "Capo IV " + "molto lungo " * 40 + "<b>fine</b>"
    d.show_findings([{
        "label": "Nuclei <NAF>", "values": {"COD_NUC": 15}, "verify": True,
        "articles": [3], "general_articles": [4], "candidate_articles": [5],
        "why": "Perche & motivo", "note": long_note,
        "external_rule": {"text": "ext rule", "verify": True}}], {"layerX": "boom <err>"})
    html = d.findings.toHtml()
    assert "Nuclei &lt;NAF&gt;" in html and "COD_NUC=15" in html
    assert "VERIFY" in html and "Piano delle Regole \u2013 art. 3" in html
    assert "Piano delle Regole \u2013 art. 5" in html
    assert "Perche &amp; motivo" in html
    full = " ".join(long_note.split()).replace("<b>fine</b>", "&lt;b&gt;fine&lt;/b&gt;")
    assert full in html  # untruncated and escaped
    assert "<b>fine</b>" not in html
    assert "External rule" in html and "unverified" in html
    assert "layerX" in html and "boom &lt;err&gt;" in html
    d.show_findings([])
    assert "No planning constraint" in d.findings.toHtml()
    for name in ("show_findings", "show_articles", "show_answer", "show_point_result",
                 "set_querying", "set_ask_enabled", "set_asking", "show_error"):
        assert callable(getattr(d, name))


def test_articles_lazy_text_and_readable_title(env):
    from plugin import dock
    d = dock.RulesDock(None)
    rows = [{"id": "PR-art-45", "number": "45", "title": "Classe III - Fattibilita",
             "roles": ["governing"], "text": "FULL TEXT"}]
    d.show_articles(rows, cited=["PR-art-45"])
    item = d.articles.items[0]
    label = item.text(0)
    assert label.startswith("Art. 45") and "Fattibilita" in label
    assert "governing" in label and "cited" in label and "<" not in label
    assert item.widget is None and d._articles_loaded == {}
    d.articles.itemExpanded.emit(item)
    assert d._articles_loaded == {"PR-art-45": True}
    assert item.child(0).widget.text == "FULL TEXT"


# ----------------------------------------------------------------------------- end to end
def test_click_then_ask_end_to_end(env):
    from qgis.core import QgsSettings

    from plugin import settings

    def responder(method, req, data):
        if method == "GET":
            return FakeReply(200, json.dumps({"features": []}).encode())
        user = json.loads(data)["messages"][-1]["content"]
        if "keywords_it" in json.loads(data)["messages"][0]["content"]:
            reply = {"keywords_it": "distanze"}
        else:
            assert "QUESTION:" in user
            reply = {"answer_it": "ciao", "answer_en": "hello",
                     "cited_articles": ["PR-art-1", "PR-art-9999"]}
        return FakeReply(200, json.dumps({"message": {"content": json.dumps(reply)}}).encode())

    FakeNAM.responder = responder
    s = settings.load_settings()
    s["provider"] = "ollama"
    settings.save_settings(s)
    iface = FakeIface()
    p = env.classFactory(iface)
    p.initGui()
    shown = {}
    p.dock.show_point_result = lambda res: shown.setdefault("point", res)
    p.dock.show_answer = lambda ans: shown.setdefault("answer", ans)
    p.dock.show_error = lambda text: shown.setdefault("error", text)

    p.on_ask("hi")  # no point yet
    assert "Click a point" in shown["error"]

    p.on_point(45.4642, 9.19)
    res = shown["point"]
    assert not res["all_failed"] and res["layers_total"] > 20
    p.on_ask("quali distanze?")
    ans = shown["answer"]
    assert ans["answer_en"] == "hello"
    assert "PR-art-9999" in ans["rejected_citations"]
    assert ans["model"] == s["ollama_model"] and ans["keywords"] == "distanze"
    assert "error" in shown and shown["error"].startswith("Click")
    assert QgsSettings.store["norme_milano/provider"] == "ollama"
    p.unload()


def test_all_services_failing_is_reported_not_raised(env):
    FakeNAM.responder = lambda *a: FakeReply(0, b"", error_string="proxy refused")
    iface = FakeIface()
    p = env.classFactory(iface)
    p.initGui()
    shown = {}
    p.dock.show_point_result = lambda res: shown.setdefault("point", res)
    p.on_point(45.0, 9.0)
    assert shown["point"]["all_failed"]
    p.unload()


# ----------------------------------------------------------------------------- static checks
def test_plugin_files_compile_and_parse_py39():
    files = [ROOT / "plugin" / f for f in PLUGIN_FILES]
    files += [ROOT / "core" / "pipeline.py", ROOT / "scripts" / "build_plugin.py",
              ROOT / "tests" / "fake_qgis.py"]
    for f in files:
        py_compile.compile(str(f), doraise=True)
        ast.parse(f.read_text(encoding="utf-8"), filename=str(f), feature_version=(3, 9))


def test_no_forbidden_qt_usage():
    for f in PLUGIN_FILES:
        text = (ROOT / "plugin" / f).read_text(encoding="utf-8")
        assert "exec_(" not in text
        for line in text.splitlines():
            if line.startswith(("import PyQt", "from PyQt", "from qgis.PyQt")):
                assert line.startswith("from qgis.PyQt"), line
            assert not line.startswith(("from PyQt", "import PyQt"))


# ----------------------------------------------------------------------------- packaging
def test_build_zip_and_packaged_import(tmp_path, monkeypatch):
    import zipfile
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_plugin
    folder, archive = build_plugin.build()
    names = zipfile.ZipFile(archive).namelist()
    assert "norme_milano/metadata.txt" in names and "norme_milano/__init__.py" in names
    for needed in ("articles.json", "documents.json", "zone_map.json", "constraint_map.json"):
        assert "norme_milano/data/" + needed in names
    assert not any("raw" in n.split("/") or n.endswith((".yaml", ".pyc")) for n in names)
    assert "norme_milano/core/llm.py" in names and "norme_milano/core/pipeline.py" in names

    # import the PACKAGED layout (relative core import) and run the pipeline on its own data
    zip_dir = tmp_path / "unzipped"
    zipfile.ZipFile(archive).extractall(zip_dir)
    fake_qgis.install()
    monkeypatch.syspath_prepend(str(zip_dir))
    try:
        pkg = importlib.import_module("norme_milano")
        compat = importlib.import_module("norme_milano._compat")
        assert compat.llm.__name__ == "norme_milano.core.llm"
        assert str(zip_dir) in str(compat.retrieval.DATA_DIR)
        res = compat.pipeline.query_point(45.4642, 9.19, fetch=lambda url, t: {"features": []})
        assert res["layers_total"] > 0
        assert callable(pkg.classFactory)
    finally:
        fake_qgis.uninstall()
        for n in [n for n in sys.modules if n.split(".")[0] == "norme_milano"]:
            del sys.modules[n]


# ----------------------------------------------------------------------------- timeouts / progress
def test_transport_sets_transfer_timeout_and_passes_feedback(env):
    from plugin import net
    FakeNAM.responder = lambda m, req, data: FakeReply(200, b"{}")
    net.make_transport()("https://x.test/a", {}, {}, 20)
    method, req, _ = FakeNAM.calls[-1]
    assert req.timeout == 20000


def test_watchdog_aborts_a_hanging_blocking_call(env, monkeypatch):
    import time

    from plugin import net
    monkeypatch.setattr(net, "WATCHDOG_GRACE", 0.0)

    def hang(feedback):  # a blocking call that only returns once its feedback is canceled
        for _ in range(400):
            if feedback.isCanceled():
                return "aborted"
            time.sleep(0.005)
        return "never aborted"

    reply, timed_out = net._blocking(hang, 0.02)
    assert reply == "aborted" and timed_out is True
    reply, timed_out = net._blocking(lambda fb: "fast", 5)
    assert reply == "fast" and timed_out is False


def test_timed_out_request_becomes_transient_llm_error(env, monkeypatch):
    from plugin import net
    monkeypatch.setattr(net, "_blocking",
                        lambda call, timeout: (FakeReply(0, b"", error_string="x"), True))
    with pytest.raises(net.llm.LLMError) as e:
        net.make_transport()("https://x.test/a?key=SECRET", {}, {}, 20)
    assert e.value.transient and "timed out after 20 s" in str(e.value)
    assert "SECRET" not in str(e.value)


def test_task_progress_reaches_dock_status_only_while_busy(env):
    from plugin import dock, tasks
    d = dock.RulesDock(None)
    seen = []
    d.set_status = seen.append
    got = []

    def work(is_canceled, report):
        report("Trying m1...")
        report("m1 busy, trying m2...")
        return "done"

    tasks.start("t", work, lambda res, err: got.append((res, err)), on_progress=d.set_progress)
    assert got == [("done", None)]
    assert seen == []  # not busy: messages are ignored
    d.set_asking(True)
    tasks.start("t", work, lambda res, err: None, on_progress=d.set_progress)
    assert seen[0] == d.ASKING
    assert seen[-1].startswith(d.ASKING) and seen[-1].endswith("m1 busy, trying m2...")
    d.set_asking(False)
    d.set_progress("late")
    assert "late" not in seen[-1]
    # plain tasks (no progress) keep the one-argument work signature
    tasks.start("t", lambda is_canceled: 5, lambda res, err: got.append(res))
    assert got[-1] == 5


def test_dock_renders_markdown_answer_safely(env):
    from plugin import dock
    d = dock.RulesDock(None)
    d.show_answer({"answer_it": "1. **Fattibilità** <script>x</script>\n- voce",
                   "answer_en": "**bold**", "cited_articles": [], "model": "m"})
    html = d.answer.toHtml()
    assert "<ol><li><b>Fattibilità</b>" in html and "<ul><li>voce</li></ul>" in html
    assert "<script" not in html and "&lt;script&gt;" in html and "**" not in html
