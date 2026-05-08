"""Tests for SSHBackend (subprocess-based)."""
import base64
import json
import subprocess
from unittest.mock import MagicMock, call, patch

import pytest

from backends.ssh import SSHBackend, _XOCHITL_DIR


def _ok():
    return subprocess.CompletedProcess([], returncode=0, stdout=b'', stderr=b'')


def _fail(msg='error'):
    return subprocess.CompletedProcess([], returncode=1, stdout=b'', stderr=msg.encode())


# ---------------------------------------------------------------------------
# check_connection
# ---------------------------------------------------------------------------

def test_check_connection_ok():
    backend = SSHBackend(host='10.11.99.1', password='secret')
    with patch('backends.ssh.shutil.which', return_value='/usr/bin/ssh'), \
         patch('backends.ssh.subprocess.run', return_value=_ok()):
        result = backend.check_connection()
    assert result.ok


def test_check_connection_failure():
    backend = SSHBackend(host='10.11.99.1', password='wrong')
    with patch('backends.ssh.shutil.which', return_value='/usr/bin/ssh'), \
         patch('backends.ssh.subprocess.run', return_value=_fail('Connection refused')):
        result = backend.check_connection()
    assert not result.ok
    assert 'Connection refused' in result.error


def test_check_connection_no_ssh():
    backend = SSHBackend(host='10.11.99.1', password='secret')
    with patch('backends.ssh.shutil.which', return_value=None):
        result = backend.check_connection()
    assert not result.ok
    assert 'ssh' in result.error.lower()


def test_check_connection_exception():
    backend = SSHBackend(host='10.11.99.1', password='secret')
    with patch('backends.ssh.shutil.which', return_value='/usr/bin/ssh'), \
         patch('backends.ssh.subprocess.run', side_effect=subprocess.TimeoutExpired('ssh', 5)):
        result = backend.check_connection()
    assert not result.ok


# ---------------------------------------------------------------------------
# upload
# ---------------------------------------------------------------------------

def test_upload_epub_calls_scp_then_ssh(tmp_path):
    epub = tmp_path / 'My Book.epub'
    epub.write_bytes(b'EPUB content')

    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return _ok()

    with patch('backends.ssh.shutil.which', return_value='/usr/bin/ssh'), \
         patch('backends.ssh.subprocess.run', side_effect=fake_run), \
         patch('backends.ssh.uuid.uuid4', return_value=MagicMock(__str__=lambda s: 'test-uuid')):
        result = SSHBackend('10.11.99.1', 'pw').upload(str(epub), 'My Book.epub')

    assert result.ok, result.error
    # First call: scp
    assert calls[0][0] == 'scp'
    assert any('test-uuid.epub' in arg for arg in calls[0])
    # Second call: ssh with compound command
    assert calls[1][0] == 'ssh'
    compound = calls[1][-1]
    assert 'test-uuid.metadata' in compound
    assert 'test-uuid.content' in compound
    assert 'systemctl restart xochitl' in compound


def test_upload_metadata_is_valid_json(tmp_path):
    epub = tmp_path / 'Title.epub'
    epub.write_bytes(b'data')

    captured_cmd = {}

    def fake_run(cmd, **kwargs):
        if cmd[0] == 'ssh':
            captured_cmd['compound'] = cmd[-1]
        return _ok()

    with patch('backends.ssh.shutil.which', return_value='/usr/bin/ssh'), \
         patch('backends.ssh.subprocess.run', side_effect=fake_run), \
         patch('backends.ssh.uuid.uuid4', return_value=MagicMock(__str__=lambda s: 'u1')):
        result = SSHBackend('10.11.99.1', 'pw').upload(str(epub), 'Title.epub')

    assert result.ok, result.error
    compound = captured_cmd['compound']

    # Extract and decode the base64-encoded metadata
    import re
    meta_match = re.search(r"echo '?([A-Za-z0-9+/=]+)'? \| base64 -d > [^\s&]+\.metadata", compound)
    assert meta_match, f'Could not find metadata b64 in: {compound}'
    meta = json.loads(base64.b64decode(meta_match.group(1)).decode())
    assert meta['visibleName'] == 'Title'
    assert meta['type'] == 'DocumentType'
    assert meta['parent'] == ''


def test_upload_content_filetype_epub(tmp_path):
    epub = tmp_path / 'Book.epub'
    epub.write_bytes(b'data')

    captured_cmd = {}

    def fake_run(cmd, **kwargs):
        if cmd[0] == 'ssh':
            captured_cmd['compound'] = cmd[-1]
        return _ok()

    with patch('backends.ssh.shutil.which', return_value='/usr/bin/ssh'), \
         patch('backends.ssh.subprocess.run', side_effect=fake_run), \
         patch('backends.ssh.uuid.uuid4', return_value=MagicMock(__str__=lambda s: 'u2')):
        SSHBackend('10.11.99.1', 'pw').upload(str(epub), 'Book.epub')

    import re
    compound = captured_cmd['compound']
    content_match = re.search(r"echo '?([A-Za-z0-9+/=]+)'? \| base64 -d > [^\s&]+\.content", compound)
    assert content_match
    content = json.loads(base64.b64decode(content_match.group(1)).decode())
    assert content['fileType'] == 'epub'


def test_upload_content_filetype_pdf(tmp_path):
    pdf = tmp_path / 'Paper.pdf'
    pdf.write_bytes(b'data')

    captured_cmd = {}

    def fake_run(cmd, **kwargs):
        if cmd[0] == 'ssh':
            captured_cmd['compound'] = cmd[-1]
        return _ok()

    with patch('backends.ssh.shutil.which', return_value='/usr/bin/ssh'), \
         patch('backends.ssh.subprocess.run', side_effect=fake_run), \
         patch('backends.ssh.uuid.uuid4', return_value=MagicMock(__str__=lambda s: 'u3')):
        result = SSHBackend('10.11.99.1', 'pw').upload(str(pdf), 'Paper.pdf')

    assert result.ok
    import re
    compound = captured_cmd['compound']
    content_match = re.search(r"echo '?([A-Za-z0-9+/=]+)'? \| base64 -d > [^\s&]+\.content", compound)
    assert content_match
    content = json.loads(base64.b64decode(content_match.group(1)).decode())
    assert content['fileType'] == 'pdf'


def test_upload_fails_on_scp_error(tmp_path):
    epub = tmp_path / 'book.epub'
    epub.write_bytes(b'data')

    def fake_run(cmd, **kwargs):
        if cmd[0] == 'scp':
            return _fail('Permission denied')
        return _ok()

    with patch('backends.ssh.shutil.which', return_value='/usr/bin/ssh'), \
         patch('backends.ssh.subprocess.run', side_effect=fake_run):
        result = SSHBackend('10.11.99.1', 'pw').upload(str(epub), 'book.epub')

    assert not result.ok
    assert 'scp' in result.error


def test_upload_unsupported_format(tmp_path):
    txt = tmp_path / 'note.txt'
    txt.write_bytes(b'text')

    with patch('backends.ssh.shutil.which', return_value='/usr/bin/ssh'):
        result = SSHBackend('10.11.99.1', 'pw').upload(str(txt), 'note.txt')

    assert not result.ok
    assert 'txt' in result.error


def test_upload_no_ssh_binary(tmp_path):
    epub = tmp_path / 'book.epub'
    epub.write_bytes(b'data')

    with patch('backends.ssh.shutil.which', return_value=None):
        result = SSHBackend('10.11.99.1', 'pw').upload(str(epub), 'book.epub')

    assert not result.ok
    assert 'ssh' in result.error.lower()
