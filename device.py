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
    description = 'Send books to a USB-tethered reMarkable tablet via its USB web interface'
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
        return ('reMarkable', '', '', 'application/octet-stream')

    def card_prefix(self, end_session=True):
        return (None, None)

    def total_space(self, end_session=True):
        return (2 ** 40, 0, 0)

    def free_space(self, end_session=True):
        return (2 ** 40, 0, 0)

    # ------------------------------------------------------------------ #
    # Book management                                                      #
    # ------------------------------------------------------------------ #

    def books(self, oncard=None, end_session=True):
        from calibre.devices.usbms.books import BookList
        return BookList(oncard, None, self.settings())

    def upload_books(self, files, names, on_card=None, end_session=True, metadata=None):
        backend = self._backend()
        locations = []
        for file_path, name in zip(files, names):
            result = backend.upload(file_path, name)
            if not result.ok:
                raise OSError(f'Upload of {name!r} failed: {result.error}')
            locations.append((name, None, None))
        return locations

    def add_books_to_metadata(self, locations, metadata, booklists):
        pass

    def delete_books(self, paths, end_session=True):
        raise NotImplementedError('Deleting books from the reMarkable is not supported in this version')

    def remove_books_from_metadata(self, paths, booklists):
        pass

    def sync_booklists(self, booklists, end_session=True):
        pass

    def get_file(self, path, outfile, end_session=True):
        raise NotImplementedError('Downloading books from the reMarkable is not supported in this version')

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
