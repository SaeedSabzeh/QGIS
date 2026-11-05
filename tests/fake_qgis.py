"""Minimal fake `qgis` package so the plugin imports and runs without QGIS.

Unknown Qt/QGIS names resolve to permissive stub classes; the pieces whose behaviour the tests
rely on (settings, auth manager, task manager, network manager, signals) are small real fakes.
"""

import sys
import types


class _Meta(type):
    def __getattr__(cls, name):
        if name.startswith("__"):
            raise AttributeError(name)
        value = _Meta(name, (Stub,), {})  # nested "enum" or class
        setattr(cls, name, value)
        return value

    def __or__(cls, other):
        return Stub()


class Stub(metaclass=_Meta):
    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return Stub()

    def __call__(self, *args, **kwargs):
        return Stub()

    def __or__(self, other):
        return Stub()

    def __lt__(self, other):
        return False

    __gt__ = __le__ = __ge__ = __lt__

    def __iter__(self):
        return iter(())


class _BoundSignal:
    def __init__(self):
        self.slots = []

    def connect(self, slot):
        self.slots.append(slot)

    def emit(self, *args):
        for slot in list(self.slots):
            slot(*args)


class pyqtSignal:  # noqa: N801
    def __init__(self, *types_):
        self.name = None

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, owner=None):
        if obj is None:
            return self
        return obj.__dict__.setdefault("_sig_" + self.name, _BoundSignal())


class QByteArray(bytes):
    def __new__(cls, data=b""):
        return bytes.__new__(cls, data)


class QUrl(str):
    pass


class QNetworkRequest:
    class Attribute:
        HttpStatusCodeAttribute = 0

    def __init__(self, url=None):
        self.url = url
        self.headers = {}
        self.timeout = None

    def setRawHeader(self, name, value):  # noqa: N802
        self.headers[bytes(name).decode()] = bytes(value).decode()

    def setTransferTimeout(self, ms):  # noqa: N802
        self.timeout = ms


class QNetworkReply:
    class NetworkError:
        NoError = 0


class FakeReply:
    def __init__(self, status=200, body=b"{}", headers=None, error_string=""):
        self.status, self.body = status, body
        self.headers = headers or {}
        self.error_string = error_string

    def attribute(self, attr):
        return self.status

    def content(self):
        return QByteArray(self.body)

    def rawHeader(self, name):  # noqa: N802
        return QByteArray(self.headers.get(bytes(name).decode(), "").encode())

    def error(self):
        return 0 if self.status else 99

    def errorString(self):  # noqa: N802
        return self.error_string


class FakeNAM:
    """FakeNAM.responder(method, request, data_bytes) -> FakeReply."""
    responder = None
    calls = []

    def blockingGet(self, request, *a, **k):  # noqa: N802
        FakeNAM.calls.append(("GET", request, None))
        return FakeNAM.responder("GET", request, None)

    def blockingPost(self, request, data, *a, **k):  # noqa: N802
        FakeNAM.calls.append(("POST", request, bytes(data)))
        return FakeNAM.responder("POST", request, bytes(data))


class QgsNetworkAccessManager:
    @staticmethod
    def instance():
        return FakeNAM()


class QgsSettings:
    store = {}

    def value(self, key, default=None):
        return QgsSettings.store.get(key, default)

    def setValue(self, key, value):  # noqa: N802
        QgsSettings.store[key] = value


class QgsAuthMethodConfig:
    def __init__(self):
        self._id, self._name, self._method, self._cfg = "", "", "", {}

    def setId(self, v):  # noqa: N802
        self._id = v

    def id(self):
        return self._id

    def setName(self, v):  # noqa: N802
        self._name = v

    def setMethod(self, v):  # noqa: N802
        self._method = v

    def method(self):
        return self._method

    def setConfig(self, k, v):  # noqa: N802
        self._cfg[k] = v

    def config(self, k, default=""):
        return self._cfg.get(k, default)


class FakeAuthManager:
    def __init__(self):
        self.disabled = False
        self.master_set = True
        self.configs = {}

    def isDisabled(self):  # noqa: N802
        return self.disabled

    def masterPasswordIsSet(self):  # noqa: N802
        return self.master_set

    def setMasterPassword(self, verify=False):  # noqa: N802
        return self.master_set

    def storeAuthenticationConfig(self, cfg, overwrite=False):  # noqa: N802
        cfg.setId("abc%04d" % (len(self.configs) + 1))
        self.configs[cfg.id()] = dict(cfg._cfg, method=cfg.method())
        return True

    def updateAuthenticationConfig(self, cfg):  # noqa: N802
        if cfg.id() not in self.configs:
            return False
        self.configs[cfg.id()] = dict(cfg._cfg, method=cfg.method())
        return True

    def loadAuthenticationConfig(self, authcfg, cfg, full=False):  # noqa: N802
        if authcfg not in self.configs:
            return False
        for k, v in self.configs[authcfg].items():
            if k != "method":
                cfg.setConfig(k, v)
        return True

    def removeAuthenticationConfig(self, authcfg):  # noqa: N802
        return self.configs.pop(authcfg, None) is not None


class FakeTaskManager:
    """Runs a task synchronously: run() then finished(ok)."""

    def addTask(self, task):  # noqa: N802
        ok = task.run()
        task.finished(ok)
        return 1


class QgsApplication:
    _auth = FakeAuthManager()
    _tm = FakeTaskManager()

    @staticmethod
    def authManager():  # noqa: N802
        return QgsApplication._auth

    @staticmethod
    def taskManager():  # noqa: N802
        return QgsApplication._tm


class QgsTask:
    class Flag:
        CanCancel = 1

    def __init__(self, description="", flags=None):
        self._canceled = False

    def isCanceled(self):  # noqa: N802
        return self._canceled

    def cancel(self):
        self._canceled = True


class FakePoint:
    def __init__(self, x, y):
        self._x, self._y = x, y

    def x(self):
        return self._x

    def y(self):
        return self._y


class QgsCoordinateTransform:
    result = FakePoint(9.19, 45.4642)  # lon, lat

    def __init__(self, *args):
        pass

    def transform(self, point):
        return QgsCoordinateTransform.result


class QgsProject:
    @staticmethod
    def instance():
        return Stub()


class FakeTextBrowser:
    def __init__(self, *a, **k):
        self.html = ""

    def setHtml(self, html):  # noqa: N802
        self.html = html

    def toHtml(self):  # noqa: N802
        return self.html

    def clear(self):
        self.html = ""

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return Stub()


class FakePlainTextEdit(FakeTextBrowser):
    def __init__(self, text="", *a, **k):
        super().__init__()
        self.text = text


class FakeTreeItem:
    def __init__(self, texts=None):
        self.texts = list(texts or [""])
        self.children, self.data_ = [], {}
        self.widget = None

    def addChild(self, c):  # noqa: N802
        self.children.append(c)

    def child(self, i):
        return self.children[i]

    def setData(self, col, role, value):  # noqa: N802
        self.data_[col] = value

    def data(self, col, role=None):
        return self.data_.get(col)

    def text(self, col=0):
        return self.texts[col]

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return Stub()


class FakeTree:
    def __init__(self, *a, **k):
        self.items = []
        self.itemExpanded = _BoundSignal()

    def clear(self):
        self.items = []

    def addTopLevelItem(self, item):  # noqa: N802
        self.items.append(item)

    def setItemWidget(self, item, col, w):  # noqa: N802
        item.widget = w

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return Stub()


class _AutoModule(types.ModuleType):
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        value = _Meta(name, (Stub,), {})
        setattr(self, name, value)
        return value


def install():
    """Create the fake package in sys.modules."""
    QgsSettings.store = {}
    QgsApplication._auth = FakeAuthManager()
    FakeNAM.responder, FakeNAM.calls = None, []
    mods = {name: _AutoModule(name) for name in (
        "qgis", "qgis.core", "qgis.gui", "qgis.PyQt", "qgis.PyQt.QtCore", "qgis.PyQt.QtGui",
        "qgis.PyQt.QtWidgets", "qgis.PyQt.QtNetwork")}
    for name, mod in mods.items():
        if "." in name:
            setattr(mods[name.rsplit(".", 1)[0]], name.rsplit(".", 1)[1], mod)
    core = mods["qgis.core"]
    for obj in (QgsNetworkAccessManager, QgsSettings, QgsAuthMethodConfig, QgsApplication,
                QgsTask, QgsCoordinateTransform, QgsProject):
        setattr(core, obj.__name__, obj)
    mods["qgis.PyQt.QtCore"].pyqtSignal = pyqtSignal
    mods["qgis.PyQt.QtCore"].QByteArray = QByteArray
    mods["qgis.PyQt.QtCore"].QUrl = QUrl
    widgets = mods["qgis.PyQt.QtWidgets"]
    widgets.QTextBrowser = FakeTextBrowser
    widgets.QPlainTextEdit = FakePlainTextEdit
    widgets.QTreeWidget = FakeTree
    widgets.QTreeWidgetItem = FakeTreeItem
    mods["qgis.PyQt.QtNetwork"].QNetworkRequest = QNetworkRequest
    mods["qgis.PyQt.QtNetwork"].QNetworkReply = QNetworkReply
    sys.modules.update(mods)


def uninstall():
    prefixes = ("qgis", "plugin", "norme_milano")
    for name in [n for n in sys.modules if n.split(".")[0] in prefixes]:
        del sys.modules[name]
