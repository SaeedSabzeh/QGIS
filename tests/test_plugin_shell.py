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
                              sleep=sleeps.append)
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
def test_key_stored_in_auth_manager_only(env):
    from qgis.core import QgsApplication, QgsSettings
    from plugin import settings
    s = settings.load_settings()
    assert s["provider"] == "none" and not settings.is_ask_available(s)
    authcfg = settings.store_gemini_key(SECRET)
    s.update(provider="gemini", authcfg=authcfg)
    settings.save_settings(s)
    assert settings.is_ask_available(settings.load_settings())
    assert settings.read_gemini_key(authcfg) == SECRET
    assert all(SECRET not in str(v) for v in QgsSettings.store.values())
    assert all(k.startswith("norme_milano/") for k in QgsSettings.store)
    assert QgsApplication.authManager().configs[authcfg]["password"] == SECRET
    # updating keeps the same auth config id
    assert settings.store_gemini_key("other", authcfg) == authcfg
    settings.remove_gemini_key(authcfg)
    with pytest.raises(settings.KeyStoreError):
        settings.read_gemini_key(authcfg)


def test_master_password_not_set_gives_clear_error(env):
    from qgis.core import QgsApplication
    from plugin import settings
    QgsApplication.authManager().master_set = False
    with pytest.raises(settings.KeyStoreError) as ei:
        settings.store_gemini_key(SECRET)
    assert "master password" in str(ei.value)
    assert SECRET not in str(ei.value)
    QgsApplication.authManager().disabled = True
    with pytest.raises(settings.KeyStoreError):
        settings.store_gemini_key(SECRET)


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
    for needed in ("articles.json", "zone_map.json", "constraint_map.json"):
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
