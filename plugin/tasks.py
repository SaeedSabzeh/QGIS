"""Run work off the UI thread with QgsTask; results return through the finished callback."""

from qgis.core import QgsApplication, QgsTask

from ._compat import enum, log

_ACTIVE = set()  # keeps Python references alive while QGIS runs the tasks


class _FnTask(QgsTask):
    def __init__(self, description, work, on_done):
        super().__init__(description, enum(QgsTask, "Flag", "CanCancel"))
        self._work = work
        self._on_done = on_done
        self.result = None
        self.error = None

    def run(self):  # worker thread: no GUI access here
        try:
            self.result = self._work(self.isCanceled)
            return True
        except Exception as exc:  # reported to the UI, never raised into QGIS
            self.error = str(exc) or type(exc).__name__
            return False

    def finished(self, ok):  # main thread
        _ACTIVE.discard(self)
        if self.isCanceled():
            return
        self._on_done(self.result if ok else None, None if ok else (self.error or "failed"))


def start(description, work, on_done):
    """Run `work(is_canceled) -> result` in a QgsTask, then `on_done(result, error)` on the
    main thread (exactly one of them is None). Returns the task."""
    task = _FnTask(description, work, on_done)
    _ACTIVE.add(task)
    QgsApplication.taskManager().addTask(task)
    return task


def cancel_all():
    for task in list(_ACTIVE):
        try:
            task.cancel()
        except RuntimeError as exc:  # underlying C++ task already deleted
            log("cancel_all: task already gone (%s)" % type(exc).__name__)
    _ACTIVE.clear()
