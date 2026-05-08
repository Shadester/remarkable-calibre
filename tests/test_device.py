"""Driver-level tests for RemarkableDevice (calibre stubbed, HTTP backend stubbed)."""
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import socket
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from device import RemarkableDevice


def _free_port():
    with socket.socket() as s:
        s.bind(('', 0))
        return s.getsockname()[1]


class _SimpleHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'reMarkable')

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        self.rfile.read(length)
        self.send_response(201)
        self.end_headers()


def _start_server(port):
    server = HTTPServer(('127.0.0.1', port), _SimpleHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


class TestDetectManagedDevices(unittest.TestCase):

    def setUp(self):
        self.driver = RemarkableDevice()
        self.driver._last_probe_time = 0.0  # force fresh probe each test

    def test_returns_self_when_reachable(self):
        port = _free_port()
        server = _start_server(port)
        try:
            self.driver._last_probe_time = 0.0
            import config
            config.prefs['host'] = f'127.0.0.1:{port}'
            config.prefs['connect_timeout_seconds'] = 2
            result = self.driver.detect_managed_devices([])
            self.assertIs(result, self.driver)
        finally:
            server.shutdown()

    def test_returns_none_when_unreachable(self):
        port = _free_port()  # nothing listening here
        import config
        config.prefs['host'] = f'127.0.0.1:{port}'
        config.prefs['connect_timeout_seconds'] = 1
        self.driver._last_probe_time = 0.0
        result = self.driver.detect_managed_devices([])
        self.assertIsNone(result)

    def test_force_refresh_bypasses_cache(self):
        port = _free_port()
        server = _start_server(port)
        try:
            import config
            config.prefs['host'] = f'127.0.0.1:{port}'
            config.prefs['connect_timeout_seconds'] = 2
            # seed a cached negative result
            self.driver._last_probe_time = 1e18
            self.driver._last_probe_ok = False
            result = self.driver.detect_managed_devices([], force_refresh=True)
            self.assertIs(result, self.driver)
        finally:
            server.shutdown()


class TestUploadBooks(unittest.TestCase):

    def setUp(self):
        self.driver = RemarkableDevice()
        self.port = _free_port()
        self.server = _start_server(self.port)
        import config
        config.prefs['host'] = f'127.0.0.1:{self.port}'
        config.prefs['connect_timeout_seconds'] = 2

    def tearDown(self):
        self.server.shutdown()

    def _tmp_file(self, content=b'data'):
        f = tempfile.NamedTemporaryFile(delete=False, suffix='.epub')
        f.write(content)
        f.flush()
        return f.name

    def test_returns_one_location_per_file(self):
        f1 = self._tmp_file()
        f2 = self._tmp_file()
        try:
            locations = self.driver.upload_books(
                [f1, f2],
                ['Book One.epub', 'Book Two.epub'],
            )
            self.assertEqual(len(locations), 2)
        finally:
            os.unlink(f1)
            os.unlink(f2)

    def test_location_contains_filename(self):
        f = self._tmp_file()
        try:
            locations = self.driver.upload_books([f], ['Author - Title.epub'])
            self.assertEqual(locations[0][0], 'Author - Title.epub')
        finally:
            os.unlink(f)

    def test_raises_on_upload_failure(self):
        port = _free_port()  # nothing listening
        import config
        config.prefs['host'] = f'127.0.0.1:{port}'
        f = self._tmp_file()
        try:
            with self.assertRaises(OSError):
                self.driver.upload_books([f], ['book.epub'])
        finally:
            os.unlink(f)


class TestBackendSelection(unittest.TestCase):

    def setUp(self):
        self.driver = RemarkableDevice()

    def test_backend_is_usb_web_by_default(self):
        import config
        config.prefs['connection_type'] = 'usb_web'
        from backends.usb_web import USBWebBackend
        self.assertIsInstance(self.driver._backend(), USBWebBackend)

    def test_backend_is_ssh_when_configured(self):
        import config
        config.prefs['connection_type'] = 'ssh'
        config.prefs['ssh_password'] = 'pw'
        from backends.ssh import SSHBackend
        self.assertIsInstance(self.driver._backend(), SSHBackend)
        config.prefs['connection_type'] = 'usb_web'  # restore

    def test_set_progress_reporter_stores_callback(self):
        sentinel = object()
        self.driver.set_progress_reporter(sentinel)
        self.assertIs(self.driver.report_progress, sentinel)

    def test_set_progress_reporter_does_not_raise(self):
        self.driver.set_progress_reporter(None)  # should not raise


class TestMiscMethods(unittest.TestCase):

    def setUp(self):
        self.driver = RemarkableDevice()

    def test_books_returns_empty(self):
        result = self.driver.books()
        self.assertEqual(list(result), [])

    def test_total_space_is_nonzero(self):
        space = self.driver.total_space()
        self.assertGreater(space[0], 0)

    def test_free_space_is_nonzero(self):
        space = self.driver.free_space()
        self.assertGreater(space[0], 0)

    def test_get_device_information_returns_tuple(self):
        info = self.driver.get_device_information()
        self.assertIsInstance(info, tuple)
        self.assertEqual(info[0], 'reMarkable')

    def test_card_prefix_returns_none_tuple(self):
        self.assertEqual(self.driver.card_prefix(), (None, None))

    def test_eject_clears_probe_cache(self):
        self.driver._last_probe_ok = True
        self.driver._last_probe_time = 1e18
        self.driver.eject()
        self.assertEqual(self.driver._last_probe_time, 0.0)


if __name__ == '__main__':
    unittest.main()
