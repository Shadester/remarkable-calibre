"""Tests for SSHBackend."""
import json
import sys
from unittest.mock import MagicMock, call, patch

import pytest

from backends.ssh import SSHBackend, _XOCHITL_DIR


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_sftp_mock():
    sftp = MagicMock()
    file_handle = MagicMock()
    file_handle.__enter__ = lambda s: s
    file_handle.__exit__ = MagicMock(return_value=False)
    sftp.open.return_value = file_handle
    return sftp, file_handle


def _make_client_mock(sftp):
    client = MagicMock()
    client.open_sftp.return_value = sftp
    return client


# ---------------------------------------------------------------------------
# check_connection
# ---------------------------------------------------------------------------

def test_check_connection_ok():
    backend = SSHBackend(host='10.11.99.1', password='secret')
    with patch('backends.ssh._PARAMIKO_AVAILABLE', True), \
         patch('backends.ssh.SSHBackend._connect') as mock_connect:
        mock_connect.return_value = MagicMock()
        result = backend.check_connection()
    assert result.ok


def test_check_connection_failure():
    backend = SSHBackend(host='10.11.99.1', password='wrong')
    with patch('backends.ssh._PARAMIKO_AVAILABLE', True), \
         patch('backends.ssh.SSHBackend._connect', side_effect=Exception('Connection refused')):
        result = backend.check_connection()
    assert not result.ok
    assert 'Connection refused' in result.error


def test_check_connection_no_paramiko():
    backend = SSHBackend(host='10.11.99.1', password='secret')
    with patch('backends.ssh._PARAMIKO_AVAILABLE', False):
        result = backend.check_connection()
    assert not result.ok
    assert 'paramiko' in result.error.lower()


# ---------------------------------------------------------------------------
# upload
# ---------------------------------------------------------------------------

def test_upload_epub_puts_three_files_and_restarts(tmp_path):
    epub = tmp_path / 'My Book.epub'
    epub.write_bytes(b'EPUB content')

    sftp, file_handle = _make_sftp_mock()
    client = _make_client_mock(sftp)

    backend = SSHBackend(host='10.11.99.1', password='secret')
    with patch('backends.ssh._PARAMIKO_AVAILABLE', True), \
         patch('backends.ssh.SSHBackend._connect', return_value=client), \
         patch('backends.ssh.uuid.uuid4', return_value=MagicMock(hex='abc', __str__=lambda s: 'test-uuid-1234')):
        result = backend.upload(str(epub), 'My Book.epub')

    assert result.ok, result.error

    # Binary file uploaded via sftp.put
    sftp.put.assert_called_once_with(str(epub), f'{_XOCHITL_DIR}/test-uuid-1234.epub')

    # Two JSON sidecars written via sftp.open
    open_calls = [c.args[0] for c in sftp.open.call_args_list]
    assert any('.metadata' in p for p in open_calls)
    assert any('.content' in p for p in open_calls)

    # xochitl restarted
    client.exec_command.assert_called_once_with('systemctl restart xochitl')


def test_upload_pdf_uses_pdf_filetype(tmp_path):
    pdf = tmp_path / 'Paper.pdf'
    pdf.write_bytes(b'PDF content')

    sftp, file_handle = _make_sftp_mock()
    client = _make_client_mock(sftp)

    written_data = {}

    def fake_open(path, mode):
        fh = MagicMock()
        fh.__enter__ = lambda s: s
        fh.__exit__ = MagicMock(return_value=False)
        def write(data):
            written_data[path] = data
        fh.write = write
        return fh

    sftp.open.side_effect = fake_open

    backend = SSHBackend(host='10.11.99.1', password='secret')
    with patch('backends.ssh._PARAMIKO_AVAILABLE', True), \
         patch('backends.ssh.SSHBackend._connect', return_value=client), \
         patch('backends.ssh.uuid.uuid4', return_value=MagicMock(__str__=lambda s: 'test-uuid-pdf')):
        result = backend.upload(str(pdf), 'Paper.pdf')

    assert result.ok, result.error

    content_path = next(p for p in written_data if '.content' in p)
    parsed = json.loads(written_data[content_path].decode())
    assert parsed['fileType'] == 'pdf'


def test_upload_metadata_has_required_keys(tmp_path):
    epub = tmp_path / 'Title.epub'
    epub.write_bytes(b'data')

    sftp, file_handle = _make_sftp_mock()
    client = _make_client_mock(sftp)

    written_data = {}

    def fake_open(path, mode):
        fh = MagicMock()
        fh.__enter__ = lambda s: s
        fh.__exit__ = MagicMock(return_value=False)
        def write(data):
            written_data[path] = data
        fh.write = write
        return fh

    sftp.open.side_effect = fake_open

    backend = SSHBackend(host='10.11.99.1', password='secret')
    with patch('backends.ssh._PARAMIKO_AVAILABLE', True), \
         patch('backends.ssh.SSHBackend._connect', return_value=client), \
         patch('backends.ssh.uuid.uuid4', return_value=MagicMock(__str__=lambda s: 'test-uuid-meta')):
        result = backend.upload(str(epub), 'Title.epub')

    assert result.ok, result.error

    meta_path = next(p for p in written_data if '.metadata' in p)
    meta = json.loads(written_data[meta_path].decode())
    for key in ('visibleName', 'type', 'parent', 'lastModified', 'version', 'deleted'):
        assert key in meta, f'Missing key: {key}'
    assert meta['visibleName'] == 'Title'
    assert meta['type'] == 'DocumentType'


def test_upload_unsupported_format(tmp_path):
    txt = tmp_path / 'note.txt'
    txt.write_bytes(b'text')

    backend = SSHBackend(host='10.11.99.1', password='secret')
    with patch('backends.ssh._PARAMIKO_AVAILABLE', True), \
         patch('backends.ssh.SSHBackend._connect', return_value=MagicMock()):
        result = backend.upload(str(txt), 'note.txt')

    assert not result.ok
    assert 'txt' in result.error


def test_upload_no_paramiko(tmp_path):
    epub = tmp_path / 'book.epub'
    epub.write_bytes(b'data')

    backend = SSHBackend(host='10.11.99.1', password='secret')
    with patch('backends.ssh._PARAMIKO_AVAILABLE', False):
        result = backend.upload(str(epub), 'book.epub')

    assert not result.ok
    assert 'paramiko' in result.error.lower()
