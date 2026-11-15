"""Exercise the built ZIP in an isolated QGIS profile with live point requests."""

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic
from zipfile import ZipFile

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsPointXY,
    QgsProject,
    QgsRectangle,
)
from qgis.gui import QgsMapCanvas
from qgis.PyQt.QtCore import QPoint, Qt
from qgis.PyQt.QtTest import QTest
from qgis.PyQt.QtWidgets import QMainWindow

CONTROLS = (
    ("Duomo", 45.46414, 9.19192, "NAF - Nuclei", "milano_naf"),
    ("ADR", 45.5281, 9.205, "ADR - Ambiti", "milano_adr"),
    ("Niguarda", 45.52, 9.185, "ARU - Ambiti", "milano_aru"),
    ("Parco Nord", 45.52937179, 9.21261924, "Parco Nord Milano", "milano_park_north"),
    ("Chiaravalle", 45.417, 9.235, "Art. 26", "milano_park_south"),
    ("Lambro", 45.465, 9.256, "R3", "pgra_R3"),
    ("Vanzago", 45.5197, 8.9736, "outside the Comune di Milano", None),
)


class Interface:
    def __init__(self):
        self.window = QMainWindow()
        self.window.resize(1140, 756)
        self.canvas = QgsMapCanvas()
        self.window.setCentralWidget(self.canvas)
        self.toolbar = self.window.addToolBar("Norme Milano")

    def mainWindow(self):
        return self.window

    def mapCanvas(self):
        return self.canvas

    def addDockWidget(self, area, widget):
        self.window.addDockWidget(area, widget)

    def removeDockWidget(self, widget):
        self.window.removeDockWidget(widget)

    def addToolBarIcon(self, action):
        self.toolbar.addAction(action)

    def removeToolBarIcon(self, action):
        self.toolbar.removeAction(action)

    def addPluginToMenu(self, menu, action):
        pass

    def removePluginMenu(self, menu, action):
        pass


def click(app, plugin, canvas, lat, lon):
    transform = QgsCoordinateTransform(
        QgsCoordinateReferenceSystem("EPSG:4326"), canvas.mapSettings().destinationCrs(), QgsProject.instance())
    target = transform.transform(QgsPointXY(lon, lat))
    canvas.setExtent(QgsRectangle(target.x() - 85, target.y() - 85, target.x() + 85, target.y() + 85))
    app.processEvents()
    pixel = canvas.getCoordinateTransform().transform(target)
    QTest.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(round(pixel.x()), round(pixel.y())))
    deadline = monotonic() + 90
    while plugin._query_task is not None:
        if monotonic() >= deadline:
            raise TimeoutError("Map query did not finish")
        QTest.qWait(25)


def run(archive):
    original = Path.cwd()
    with TemporaryDirectory(prefix="milano-qgis-", dir=archive.parent, ignore_cleanup_errors=True) as work:
        root = Path(work)
        os.chdir(root)
        with ZipFile(archive) as bundle:
            bundle.extractall(root / "plugins")
        sys.path.insert(0, str(root / "plugins"))
        app = QgsApplication([], True, str(root))
        app.initQgis()
        import norme_milano
        from norme_milano import settings

        assert root in Path(norme_milano.__file__).parents
        settings.load_settings = lambda: {"first_run_done": True, "provider": "none"}
        interface = Interface()
        interface.canvas.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:32632"))
        interface.window.show()
        plugin = norme_milano.classFactory(interface)
        plugin.initGui()
        plugin.action.trigger()
        app.processEvents()
        print(Qgis.QGIS_VERSION, archive.name, flush=True)
        try:
            for name, lat, lon, label, layer in CONTROLS:
                click(app, plugin, interface.canvas, lat, lon)
                findings = plugin.dock.findings.toPlainText()
                assert label in findings, (name, findings)
                if layer:
                    assert any(f["layer"] == layer for f in plugin._last["findings"]), name
                    assert "Official map layer" in findings
                    item = plugin.dock.articles.topLevelItem(0)
                    plugin.dock.articles.expandItem(item)
                    article = plugin.dock.articles.itemWidget(item.child(0), 0)
                    assert "Open official publication" in article.toPlainText(), name
                else:
                    assert plugin._last is None and not plugin.dock._ask_allowed
                print(f"PASS {name}", flush=True)
            official = "https://pgt.comune.milano.it/"
            plugin.dock.show_answer({
                "answer_it": "Risposta di prova", "answer_en": "Test reply", "model": "fixture",
                "cited_articles": ["PR-art-6"],
                "articles": [{"id": "PR-art-6", "title": "Indice", "roles": ["governing"],
                              "cite": "Piano delle Regole art. 6", "source_url": official}],
                "evidence": [{"article_id": "PR-art-6", "quote": "Quoted fixture"}],
            })
            assert plugin.dock.answer.openExternalLinks() and official in plugin.dock.answer.toHtml()
            print("PASS answer links open externally", flush=True)
        finally:
            plugin.unload()
            interface.window.close()
            app.processEvents()
            os.chdir(original)


if __name__ == "__main__":
    run(Path(sys.argv[1]).resolve())
