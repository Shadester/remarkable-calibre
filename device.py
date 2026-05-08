import os
import sys
import time
import types

# Make intra-plugin imports work both inside Calibre and in tests
_plugin_dir = os.path.dirname(os.path.abspath(__file__))
if _plugin_dir not in sys.path:
    sys.path.insert(0, _plugin_dir)

from calibre.devices.interface import DevicePlugin


class RemarkableDevice(DevicePlugin):
    name = 'reMarkable'
    gui_name = 'reMarkable'
    description = 'Manage books on a reMarkable tablet from Calibre via SSH or USB web interface'
    author = 'remarkablecalibre'
    version = (2, 0, 0)
    minimum_calibre_version = (6, 0, 0)
    supported_platforms = ['windows', 'osx', 'linux']

    # Tell Calibre we manage our own device presence (network, not USB mass-storage)
    MANAGES_DEVICE_PRESENCE = True

    # Calibre will auto-convert books to one of these before calling upload_books
    FORMATS = ['epub', 'pdf']

    # Disable unused UI elements
    CAN_SET_METADATA = []
    HIDE_FORMATS_CONFIG_BOX = True
    SUPPORTS_SUB_DIRS = False

    # Invalid USB IDs so Calibre's USB scanner never matches this driver
    VENDOR_ID = [0xffff]
    PRODUCT_ID = [0xffff]
    BCD = [0xffff]

    # Internal state
    _last_probe_time = 0.0
    _last_probe_ok = False
    _PROBE_INTERVAL = 8  # seconds between active connection checks

    # ------------------------------------------------------------------ #
    # Detection                                                            #
    # ------------------------------------------------------------------ #

    def _backend(self):
        from backends.usb_web import USBWebBackend
        from backends.ssh import SSHBackend
        from config import prefs
        if prefs.get('connection_type', 'usb_web') == 'ssh':
            return SSHBackend(
                host=prefs['host'],
                password=prefs.get('ssh_password', ''),
                timeout=prefs['connect_timeout_seconds'],
            )
        return USBWebBackend(
            host=prefs['host'],
            timeout=prefs['connect_timeout_seconds'],
        )

    def _probe(self):
        now = time.monotonic()
        if now - self._last_probe_time < self._PROBE_INTERVAL:
            return self._last_probe_ok
        result = self._backend().check_connection()
        self._last_probe_time = now
        self._last_probe_ok = result.ok
        return result.ok

    def detect_managed_devices(self, devices_on_system, force_refresh=False):
        if force_refresh:
            self._last_probe_time = 0.0
        return self if self._probe() else None

    def debug_managed_device_detection(self, devices_on_system, output):
        from config import prefs
        reachable = self._probe()
        output.write(
            f'reMarkable: probing http://{prefs["host"]}/ ... '
            f'{"reachable" if reachable else "not reachable"}\n'
        )

    # ------------------------------------------------------------------ #
    # Connection lifecycle                                                 #
    # ------------------------------------------------------------------ #

    def reset(self, key='-1', log_packets=False, report_progress=None, detected_device=None):
        self.report_progress = report_progress if report_progress else lambda x, y: x

    def set_progress_reporter(self, report_progress):
        self.report_progress = report_progress

    def open(self, connected_device, library_uuid):
        pass

    def eject(self):
        self._last_probe_time = 0.0
        self._last_probe_ok = False

    def post_yank_cleanup(self):
        self._last_probe_time = 0.0
        self._last_probe_ok = False

    # ------------------------------------------------------------------ #
    # Device information                                                   #
    # ------------------------------------------------------------------ #

    def get_device_information(self, end_session=True):
        backend = self._backend()
        version = ''
        if hasattr(backend, 'get_firmware_version'):
            try:
                version = backend.get_firmware_version()
            except Exception:
                pass
        label = f'reMarkable {version}'.strip() if version else 'reMarkable'
        return (label, '', '', 'application/octet-stream')

    def card_prefix(self, end_session=True):
        return (None, None)

    def total_space(self, end_session=True):
        backend = self._backend()
        if hasattr(backend, 'get_storage_info'):
            try:
                total, _ = backend.get_storage_info()
                if total > 0:
                    return (total, 0, 0)
            except Exception:
                pass
        return (2 ** 40, 0, 0)

    def free_space(self, end_session=True):
        backend = self._backend()
        if hasattr(backend, 'get_storage_info'):
            try:
                _, free = backend.get_storage_info()
                if free > 0:
                    return (free, 0, 0)
            except Exception:
                pass
        return (2 ** 40, 0, 0)

    # ------------------------------------------------------------------ #
    # Book management                                                      #
    # ------------------------------------------------------------------ #

    def _cache_path(self) -> str:
        from calibre.utils.config import config_dir
        return os.path.join(config_dir, 'plugins', 'remarkable_books.json')

    def books(self, oncard=None, end_session=True):
        import json as _json
        from calibre.devices.usbms.books import Book, BookList
        bl = BookList(oncard, None, self.settings())
        if oncard is not None:
            return bl

        # Load cached booklist keyed by reMarkable UUID.
        cached = {}
        try:
            cache_path = self._cache_path()
            if os.path.exists(cache_path):
                with open(cache_path, 'rb') as f:
                    for item in _json.loads(f.read()):
                        b = Book('', item['lpath'])
                        b.uuid = item.get('uuid')
                        b.title = item.get('title', '')
                        b.authors = item.get('authors', [])
                        cached[b.lpath] = b
        except Exception:
            pass

        backend = self._backend()
        if not hasattr(backend, 'list_books'):
            for b in cached.values():
                bl.append(b)
            return bl

        for entry in backend.list_books():
            rm_uuid = entry.get('uuid', '')
            calibre_uuid = entry.get('calibreUuid')

            if rm_uuid in cached:
                book = cached[rm_uuid]
                device_title = entry.get('visibleName', '')
                if device_title:
                    book.title = device_title
            elif calibre_uuid:
                book = Book('', rm_uuid)
                book.uuid = calibre_uuid
                book.title = entry.get('visibleName', 'Unknown')
                book.authors = ['Unknown']
            else:
                book = Book('', rm_uuid)
                book.title = entry.get('visibleName', 'Unknown')
                book.authors = ['Unknown']

            if calibre_uuid and not getattr(book, 'uuid', None):
                book.uuid = calibre_uuid
            book.path = rm_uuid
            bl.append(book)

        return bl

    def upload_books(self, files, names, on_card=None, end_session=True, metadata=None):
        backend = self._backend()
        locations = []
        for i, (file_path, name) in enumerate(zip(files, names)):
            title = metadata[i].title if metadata and i < len(metadata) else None
            calibre_uuid = metadata[i].uuid if metadata and i < len(metadata) else None
            result = backend.upload(file_path, name, title=title, calibre_uuid=calibre_uuid)
            if not result.ok:
                raise OSError(f'Upload of {name!r} failed: {result.error}')
            locations.append((name, result.uuid, None))
        return locations

    def add_books_to_metadata(self, locations, metadata, booklists):
        from calibre.devices.usbms.books import Book
        for i, (name, rm_uuid, _) in enumerate(locations):
            if not rm_uuid:
                continue
            meta = metadata[i] if metadata and i < len(metadata) else None
            book = Book('', rm_uuid, other=meta)
            book._new_book = True
            booklists[0].add_book(book, replace_metadata=True)

    def delete_books(self, paths, end_session=True):
        backend = self._backend()
        if not hasattr(backend, 'delete'):
            raise OSError('Deleting books is not supported over the USB web interface')
        for path in paths:
            result = backend.delete(path)
            if not result.ok:
                raise OSError(f'Delete of {path!r} failed: {result.error}')

    def remove_books_from_metadata(self, paths, booklists):
        pass

    def sync_booklists(self, booklists, end_session=True):
        import json as _json
        try:
            cache_path = self._cache_path()
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            data = [
                {'lpath': b.lpath, 'uuid': getattr(b, 'uuid', None),
                 'title': getattr(b, 'title', ''), 'authors': getattr(b, 'authors', [])}
                for b in booklists[0]
            ]
            with open(cache_path, 'wb') as f:
                f.write(_json.dumps(data).encode())
        except Exception:
            pass

    def get_file(self, path, outfile, end_session=True):
        backend = self._backend()
        if not hasattr(backend, 'download'):
            raise OSError('Downloading books is not supported over the USB web interface')
        result = backend.download(path, outfile)
        if not result.ok:
            raise OSError(f'Download failed: {result.error}')

    # ------------------------------------------------------------------ #
    # Configuration                                                        #
    # ------------------------------------------------------------------ #

    def settings(self):
        return types.SimpleNamespace(format_map=list(self.FORMATS))

    def is_customizable(self):
        return True

    def config_widget(self):
        from config import ConfigWidget
        return ConfigWidget()

    def save_settings(self, config_widget):
        config_widget.commit()
