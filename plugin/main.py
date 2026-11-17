"""Plugin class: toolbar action, map tool, dock panel, settings, background tasks."""

import os

from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtGui import QIcon

try:  # Qt6 moved QAction to QtGui
    from qgis.PyQt.QtGui import QAction
except ImportError:
    from qgis.PyQt.QtWidgets import QAction

from . import early_access, i18n, net, settings, tasks
from ._compat import enum, pipeline
from .dock import RulesDock
from .map_tool import PointQueryTool

MENU = "&Norme Milano"
TITLE = "Norme Milano"
ICON_PATH = os.path.join(os.path.dirname(__file__), "icon.png")


class NormeMilanoPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.settings_action = None
        self.tool = None
        self.dock = None
        self._last = None        # last query_point result (kept for questions)
        self._query_task = None
        self._ask_task = None
        self._query_token = None
        self._ask_token = None
        self._unloaded = False

    # ------------------------------------------------------------------ QGIS lifecycle
    def initGui(self):  # noqa: N802 (name required by QGIS)
        self._unloaded = False
        canvas = self.iface.mapCanvas()
        win = self.iface.mainWindow()

        self.action = QAction(QIcon(ICON_PATH), "Norme Milano", win)
        self.action.setToolTip("Norme Milano: click a point to see the planning rules "
                               "/ clic su un punto per le norme")
        self.action.setCheckable(True)
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(MENU, self.action)

        self.settings_action = QAction("Impostazioni / Settings...", win)
        self.settings_action.triggered.connect(self.open_settings)
        self.iface.addPluginToMenu(MENU, self.settings_action)

        self.tool = PointQueryTool(canvas)
        self.tool.setAction(self.action)  # QGIS keeps the button checked while the tool is active
        self.tool.pointQueried.connect(self.on_point)

        self.dock = RulesDock(win, lang=self._lang())
        self.dock.setWindowIcon(QIcon(ICON_PATH))
        self.dock.askRequested.connect(self.on_ask)
        self.dock.settingsRequested.connect(self.open_settings)
        self.dock.earlyAccessRequested.connect(self._early_access_open)
        self.dock.earlyAccessDismissed.connect(self._resolve_early_access)
        if (early_access.enabled() and not settings.read_value("early_access_resolved")
                and settings.read_value("lookup_count") >= early_access.SHOW_AFTER):
            self.dock.show_early_access(True)
        self.iface.addDockWidget(enum(Qt, "DockWidgetArea", "RightDockWidgetArea"), self.dock)
        self.dock.hide()
        self._refresh_ask_state()

        if not settings.load_settings()["first_run_done"]:
            QTimer.singleShot(800, self._first_run)

    def unload(self):
        self._unloaded = True
        self._query_token = self._ask_token = None
        tasks.cancel_all()
        self._query_task = self._ask_task = None
        canvas = self.iface.mapCanvas()
        if self.tool is not None:
            self.tool.cleanup()
            if canvas.mapTool() is self.tool:
                canvas.unsetMapTool(self.tool)
            self.tool = None
        if self.action is not None:
            self.iface.removePluginMenu(MENU, self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action.deleteLater()
            self.action = None
        if self.settings_action is not None:
            self.iface.removePluginMenu(MENU, self.settings_action)
            self.settings_action.deleteLater()
            self.settings_action = None
        if self.dock is not None:
            self.iface.removeDockWidget(self.dock)
            self.dock.deleteLater()
            self.dock = None

    # ------------------------------------------------------------------ actions
    def run(self, checked=True):
        canvas = self.iface.mapCanvas()
        if checked:
            canvas.setMapTool(self.tool)
            self.dock.show()
            self.dock.raise_()
        else:
            canvas.unsetMapTool(self.tool)

    def _lang(self):
        return i18n.resolve(settings.load_settings().get("ui_language", "auto"))

    def open_settings(self, first_run=False):
        dlg = settings.SettingsDialog(self.iface.mainWindow(), first_run=bool(first_run))
        dlg.exec()
        if self.dock is not None and self.dock.lang != self._lang():
            self.dock.retranslate(self._lang())
        self._refresh_ask_state()

    def _first_run(self):
        if self._unloaded or settings.load_settings()["first_run_done"]:
            return
        self.open_settings(first_run=True)
        # mark done even if the user cancelled, so the prompt appears only once
        s = settings.load_settings()
        s["first_run_done"] = True
        settings.save_settings(s)

    def _refresh_ask_state(self):
        if self.dock is not None:
            provider = settings.is_ask_available(settings.load_settings())
            self.dock.set_ask_state(provider, self._last is not None)

    # ------------------------------------------------------------------ point query
    def on_point(self, lat, lon):
        if self._unloaded:
            return
        token = self._query_token = object()
        self._ask_token = None
        if self._query_task is not None:
            self._query_task.cancel()
        if self._ask_task is not None:
            self._ask_task.cancel()
            self._ask_task = None
        self._last = None
        self.dock.set_asking(False)
        self._refresh_ask_state()
        self.dock.show()
        self.dock.set_querying(lat, lon)

        def work(is_canceled):
            return pipeline.query_point(lat, lon, fetch=net.make_fetch(is_canceled))

        def done(res, error):
            if self._query_token is not token or self._unloaded:
                return
            self._query_task = self._query_token = None
            if error is not None:
                self.dock.show_error(self.dock.t("query_failed") % error)
                return
            if not res.get("scope_note") and not res.get("all_failed"):
                self._last = res
            self._refresh_ask_state()
            self.dock.show_point_result(res)
            if self._last is res:
                self._count_lookup()

        task = tasks.start("Norme Milano: query point", work, done)
        if self._query_token is token:
            self._query_task = task

    def _count_lookup(self):
        count, show = early_access.next_state(settings.read_value("lookup_count"),
                                              settings.read_value("early_access_resolved"))
        settings.write_value("lookup_count", count)
        if show:
            self.dock.show_early_access(True)

    def _early_access_open(self):
        if early_access.open_signup(self._lang()):
            self._resolve_early_access()
        else:  # keep the strip so the user can try again
            key = "ea_mail_failed" if early_access.SIGNUP_EMAIL else "ea_open_failed"
            self.dock.show_error(self.dock.t(key) % early_access.signup_address())

    def _resolve_early_access(self):
        settings.write_value("early_access_resolved", True)
        if self.dock is not None:
            self.dock.show_early_access(False)

    # ------------------------------------------------------------------ question
    def on_ask(self, question):
        if self._unloaded:
            return
        if self._last is None:
            self.dock.show_error(self.dock.t("click_first"))
            return
        s = settings.load_settings()
        if not settings.is_ask_available(s):
            self._refresh_ask_state()
            return
        key = None
        if s["provider"] == "gemini":
            try:
                key = settings.read_gemini_key(s["authcfg"])  # main thread; never prompts
            except settings.KeyStoreError as exc:
                self.dock.show_error(str(exc))
                return
        point_result = self._last
        token = self._ask_token = object()
        if self._ask_task is not None:
            self._ask_task.cancel()

        def work(is_canceled, report):
            client = settings.build_client(s, key, net.make_transport(is_canceled))
            return pipeline.ask(question, point_result, client, on_progress=report)

        def done(ans, error):
            if self._ask_token is not token or self._unloaded:
                return
            self._ask_task = self._ask_token = None
            self.dock.set_asking(False)
            if error is not None:
                self.dock.show_error(self.dock.t("ask_failed") % error)
                return
            self.dock.show_answer(ans)

        self.dock.set_asking(True)
        task = tasks.start("Norme Milano: ask", work, done, on_progress=self.dock.set_progress)
        if self._ask_token is token:
            self._ask_task = task

