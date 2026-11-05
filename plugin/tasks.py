"""Run work off the UI thread with QgsTask; results return through the finished callback."""

from qgis.core import QgsApplication, QgsTask
from qgis.PyQt.QtCore import pyqtSignal

from ._compat import enum, log

_ACTIVE = set()  # keeps Python references alive while QGIS runs the tasks


class _FnTask(QgsTask):
    progressMessage = pyqtSignal(str)  # emitted from the worker thread, delivered queued

    def __init__(self, description, work, on_done, with_progress=False):
        super().__init__(description, enum(QgsTask, "Flag", "CanCancel"))
        self._work = work
        self._on_done = on_done
        self._with_progress = with_progress
        self.result = None
        self.error = None

    def run(self):  # worker thread: no GUI access here
        try:
            if self._with_progress:
                self.result = self._work(self.isCanceled, self.progressMessage.emit)
            else:
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


def start(description, work, on_done, on_progress=None):
    """Run `work(is_canceled) -> result` in a QgsTask, then `on_done(result, error)` on the
    main thread (exactly one of them is None). Returns the task.

    With `on_progress`, `work(is_canceled, report)` also gets a `report(text)` function it may
    call from the worker thread; `on_progress(text)` then runs on the main thread (connect a
    bound method of a QObject such as the dock: Qt queues the call across threads)."""
    task = _FnTask(description, work, on_done, with_progress=on_progress is not None)
    if on_progress is not None:
        task.progressMessage.connect(on_progress)
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
