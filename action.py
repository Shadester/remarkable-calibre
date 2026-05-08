import os
import re

from calibre.gui2.actions import InterfaceAction

from calibre_plugins.remarkable.format_selection import pick_format


def _friendly_filename(title: str, authors: list, ext: str) -> str:
    author = authors[0] if authors else 'Unknown'
    raw = f'{author} - {title}.{ext.lower()}'
    return re.sub(r'[\\/:*?"<>|]', '_', raw)


class SendToRemarkableAction(InterfaceAction):
    name = 'Send to reMarkable'
    action_spec = ('Send to reMarkable', None, 'Send selected books to a reMarkable tablet via USB', None)
    action_type = 'current'

    def genesis(self):
        self.qaction.triggered.connect(self.send_to_remarkable)

    def send_to_remarkable(self):
        from calibre.gui2 import info_dialog
        from calibre_plugins.remarkable.config import prefs
        from calibre_plugins.remarkable.backends.usb_web import USBWebBackend

        db = self.gui.current_db.new_api
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows:
            info_dialog(self.gui, 'No books selected',
                        'Select one or more books in the library before clicking Send to reMarkable.',
                        show=True)
            return

        book_ids = [self.gui.library_view.model().id(r) for r in rows]
        backend = USBWebBackend(
            host=prefs['host'],
            timeout=prefs['connect_timeout_seconds'],
        )

        conn = backend.check_connection()
        if not conn.ok:
            info_dialog(
                self.gui,
                'Tablet not reachable',
                f'Could not connect to the reMarkable at {prefs["host"]}.\n\n'
                'Is the USB cable connected and "USB web interface" enabled in\n'
                'Settings → Storage on the tablet?\n\n'
                f'Error: {conn.error}',
                show=True,
            )
            return

        jobs = []
        skipped = []
        for book_id in book_ids:
            title = db.field_for('title', book_id) or 'Unknown'
            authors = db.field_for('authors', book_id) or ['Unknown']
            available = set(db.formats(book_id))
            fmt, reason = pick_format(available, prefs['format_priority'])
            if fmt is None:
                skipped.append((title, reason))
                continue
            file_path = db.format_abspath(book_id, fmt)
            filename = _friendly_filename(title, authors, fmt)
            jobs.append((title, file_path, filename))

        from calibre_plugins.remarkable.send_dialog import SendDialog
        dlg = SendDialog(self.gui, backend, jobs, skipped)
        dlg.exec()
