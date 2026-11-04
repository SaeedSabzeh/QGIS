"""Plugin class: registers the toolbar action, map tool and dock panel."""

from qgis.PyQt.QtWidgets import QAction

MENU = "&Norme Milano"


class NormeMilanoPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None

    def initGui(self):  # noqa: N802
        self.action = QAction("Norme Milano", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(MENU, self.action)

    def unload(self):
        self.iface.removePluginMenu(MENU, self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        # TODO (Phase 3): activate map_tool.PointQueryTool and show dock.RulesDock
        self.iface.messageBar().pushInfo("Norme Milano", "Not implemented yet.")
