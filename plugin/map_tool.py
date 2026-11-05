"""Map tool: a left click becomes a WGS84 (lat, lon) query with a temporary marker."""

from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject
from qgis.gui import QgsMapToolEmitPoint, QgsVertexMarker
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QColor

from ._compat import enum, log


def to_wgs84(point, source_crs):
    """Transform a QgsPointXY from `source_crs` to EPSG:4326. Returns (lat, lon)."""
    wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
    xform = QgsCoordinateTransform(source_crs, wgs84, QgsProject.instance())
    p = xform.transform(point)
    return p.y(), p.x()


class PointQueryTool(QgsMapToolEmitPoint):
    pointQueried = pyqtSignal(float, float)  # lat, lon (EPSG:4326)

    def __init__(self, canvas):
        super().__init__(canvas)
        self._canvas = canvas
        self._marker = None

    def canvasReleaseEvent(self, event):  # noqa: N802 (Qt override)
        if event.button() != enum(Qt, "MouseButton", "LeftButton"):
            return
        point = self.toMapCoordinates(event.pos())
        self.show_marker(point)
        lat, lon = to_wgs84(point, self._canvas.mapSettings().destinationCrs())
        self.pointQueried.emit(lat, lon)

    def show_marker(self, point):
        self.clear_marker()
        marker = QgsVertexMarker(self._canvas)
        marker.setCenter(point)
        marker.setIconType(enum(QgsVertexMarker, "IconType", "ICON_CROSS"))
        marker.setIconSize(14)
        marker.setPenWidth(3)
        marker.setColor(QColor(220, 30, 30))
        self._marker = marker

    def clear_marker(self):
        if self._marker is not None:
            try:
                self._canvas.scene().removeItem(self._marker)
            except (RuntimeError, AttributeError) as exc:  # marker/scene already deleted
                log("clear_marker: %s" % type(exc).__name__)
            self._marker = None

    def cleanup(self):
        self.clear_marker()
