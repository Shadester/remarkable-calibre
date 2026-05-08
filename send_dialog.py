from qt.core import (
    QDialog, QDialogButtonBox, QLabel, QProgressBar,
    QTextEdit, QVBoxLayout, Qt, QThread, pyqtSignal,
)


class _UploadWorker(QThread):
    progress = pyqtSignal(int, str)   # (current_index, book_title)
    finished = pyqtSignal(list)       # list of (title, ok, message)

    def __init__(self, backend, jobs):
        super().__init__()
        self.backend = backend
        self.jobs = jobs

    def run(self):
        results = []
        for i, (title, file_path, filename) in enumerate(self.jobs):
            self.progress.emit(i, title)
            result = self.backend.upload(file_path, filename)
            results.append((title, result.ok, result.error or ''))
        self.finished.emit(results)


class SendDialog(QDialog):
    def __init__(self, parent, backend, jobs, skipped):
        super().__init__(parent)
        self.setWindowTitle('Send to reMarkable')
        self.setMinimumWidth(420)

        self._jobs = jobs
        self._skipped = skipped
        self._backend = backend

        layout = QVBoxLayout(self)

        self._status = QLabel(f'Uploading 0 of {len(jobs)}...')
        layout.addWidget(self._status)

        self._progress = QProgressBar()
        self._progress.setRange(0, max(len(jobs), 1))
        self._progress.setValue(0)
        layout.addWidget(self._progress)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setVisible(False)
        layout.addWidget(self._log)

        self._buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self._buttons.setEnabled(False)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self._worker = _UploadWorker(backend, jobs)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_progress(self, index: int, title: str):
        self._progress.setValue(index)
        self._status.setText(f'Uploading {index + 1} of {len(self._jobs)}: {title}')

    def _on_finished(self, results: list):
        self._progress.setValue(len(self._jobs))

        successes = [t for t, ok, _ in results if ok]
        failures = [(t, msg) for t, ok, msg in results if not ok]

        lines = []
        if successes:
            lines.append(f'Sent {len(successes)} book(s) successfully.')
        for title, msg in failures:
            lines.append(f'FAILED: {title} — {msg}')
        for title, reason in self._skipped:
            lines.append(f'Skipped: {title} — {reason}')

        summary = '\n'.join(lines) if lines else 'Done.'
        self._status.setText(summary if len(lines) <= 2 else f'Done: {len(successes)} sent, {len(failures)} failed, {len(self._skipped)} skipped.')

        if len(lines) > 2 or failures or self._skipped:
            self._log.setPlainText('\n'.join(lines))
            self._log.setVisible(True)

        self._buttons.setEnabled(True)
