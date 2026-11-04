"""QGIS entry point for the Norme Milano plugin."""


def classFactory(iface):  # noqa: N802 (name required by QGIS)
    from .main import NormeMilanoPlugin

    return NormeMilanoPlugin(iface)
