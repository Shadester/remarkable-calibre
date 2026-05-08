"""Tests for USBWebBackend using a local stub HTTP server."""
import io
import os
import sys
import email
import socket
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from backends.usb_web import USBWebBackend


class _Handler(BaseHTTPRequestHandler):
    """Stub that records received uploads and returns configured status codes."""

    uploads = []
    response_code = 201

    def log_message(self, *args):
        pass  # silence server logs during tests

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'reMarkable')

    def do_POST(self):
        if self.path != '/upload':
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)

        content_type = self.headers.get('Content-Type', '')
        msg = email.message_from_bytes(
            b'Content-Type: ' + content_type.encode() + b'\r\n\r\n' + body
        )
        for part in msg.walk():
            disposition = part.get('Content-Disposition', '')
            if 'filename' in disposition:
                _Handler.uploads.append({
                    'filename': part.get_filename(),
                    'content': part.get_payload(decode=True),
                })

        self.send_response(_Handler.response_code)
        self.end_headers()


def _free_port():
    with socket.socket() as s:
        s.bind(('', 0))
        return s.getsockname()[1]


class TestUSBWebBackendCheckConnection(unittest.TestCase):

    def setUp(self):
        port = _free_port()
        self.server = HTTPServer(('127.0.0.1', port), _Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.backend = USBWebBackend(host=f'127.0.0.1:{port}', timeout=2)

    def tearDown(self):
        self.server.shutdown()

    def test_connection_ok_when_server_running(self):
        result = self.backend.check_connection()
        self.assertTrue(result.ok)
        self.assertIsNone(result.error)

    def test_connection_fails_when_server_not_running(self):
        port = _free_port()
        backend = USBWebBackend(host=f'127.0.0.1:{port}', timeout=1)
        result = backend.check_connection()
        self.assertFalse(result.ok)
        self.assertIsNotNone(result.error)

    def test_connection_fails_on_timeout(self):
        # Port 9 (discard) typically stalls; use a non-routable IP to force timeout
        backend = USBWebBackend(host='192.0.2.1', timeout=1)
        result = backend.check_connection()
        self.assertFalse(result.ok)


class TestUSBWebBackendUpload(unittest.TestCase):

    def setUp(self):
        _Handler.uploads = []
        _Handler.response_code = 201
        port = _free_port()
        self.server = HTTPServer(('127.0.0.1', port), _Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.backend = USBWebBackend(host=f'127.0.0.1:{port}', timeout=2)
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.epub')
        self.tmp.write(b'EPUB content here')
        self.tmp.flush()

    def tearDown(self):
        self.server.shutdown()
        os.unlink(self.tmp.name)

    def test_upload_success(self):
        result = self.backend.upload(self.tmp.name, 'Author - Title.epub')
        self.assertTrue(result.ok, result.error)

    def test_upload_sends_correct_filename(self):
        self.backend.upload(self.tmp.name, 'Author - Title.epub')
        self.assertEqual(len(_Handler.uploads), 1)
        self.assertEqual(_Handler.uploads[0]['filename'], 'Author - Title.epub')

    def test_upload_sends_correct_content(self):
        self.backend.upload(self.tmp.name, 'Author - Title.epub')
        self.assertEqual(_Handler.uploads[0]['content'], b'EPUB content here')

    def test_upload_uses_file_field_name(self):
        # The multipart field name must be 'file' (rM web interface requirement)
        port = _free_port()

        field_names_seen = []

        class _FieldCapture(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(length)
                content_type = self.headers.get('Content-Type', '')
                msg = email.message_from_bytes(
                    b'Content-Type: ' + content_type.encode() + b'\r\n\r\n' + body
                )
                for part in msg.walk():
                    disp = part.get('Content-Disposition', '')
                    if 'name=' in disp:
                        import re
                        m = re.search(r'name="([^"]+)"', disp)
                        if m:
                            field_names_seen.append(m.group(1))
                self.send_response(201)
                self.end_headers()

        srv = HTTPServer(('127.0.0.1', port), _FieldCapture)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            b = USBWebBackend(host=f'127.0.0.1:{port}', timeout=2)
            b.upload(self.tmp.name, 'test.epub')
            self.assertIn('file', field_names_seen)
        finally:
            srv.shutdown()

    def test_upload_non_201_is_failure(self):
        _Handler.response_code = 400
        result = self.backend.upload(self.tmp.name, 'Author - Title.epub')
        self.assertFalse(result.ok)
        self.assertIsNotNone(result.error)

    def test_upload_file_not_found(self):
        result = self.backend.upload('/nonexistent/path/book.epub', 'book.epub')
        self.assertFalse(result.ok)


class TestUSBWebBackendUploadUUID(unittest.TestCase):
    """Upload UUID discovery via GET /documents/ diff."""

    def setUp(self):
        import json as _json
        self._before = [{'ID': 'existing-id', 'Type': 'DocumentType', 'VissibleName': 'Old'}]
        self._after = [
            {'ID': 'existing-id', 'Type': 'DocumentType', 'VissibleName': 'Old'},
            {'ID': 'new-id-abc', 'Type': 'DocumentType', 'VissibleName': 'New Book'},
        ]
        call_count = [0]

        class _UUIDHandler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(handler):
                if handler.path.startswith('/documents'):
                    data = self._before if call_count[0] == 0 else self._after
                    body = _json.dumps(data).encode()
                    handler.send_response(200)
                    handler.send_header('Content-Type', 'application/json')
                    handler.send_header('Content-Length', str(len(body)))
                    handler.end_headers()
                    handler.wfile.write(body)
                else:
                    handler.send_response(200)
                    handler.end_headers()

            def do_POST(handler):
                call_count[0] += 1
                length = int(handler.headers.get('Content-Length', 0))
                handler.rfile.read(length)
                handler.send_response(201)
                handler.end_headers()

        port = _free_port()
        self.server = HTTPServer(('127.0.0.1', port), _UUIDHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.backend = USBWebBackend(host=f'127.0.0.1:{port}', timeout=2)
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.epub')
        self.tmp.write(b'data')
        self.tmp.flush()

    def tearDown(self):
        self.server.shutdown()
        os.unlink(self.tmp.name)

    def test_upload_returns_new_uuid(self):
        result = self.backend.upload(self.tmp.name, 'New Book.epub')
        self.assertTrue(result.ok, result.error)
        self.assertEqual(result.uuid, 'new-id-abc')

    def test_upload_uuid_none_when_no_new_entry(self):
        self._after[:] = self._before  # no new entry appears
        result = self.backend.upload(self.tmp.name, 'New Book.epub')
        self.assertTrue(result.ok)
        self.assertIsNone(result.uuid)


if __name__ == '__main__':
    unittest.main()
