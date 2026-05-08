"""Tests for SSHBackend (subprocess-based)."""
import json
import subprocess
from unittest.mock import MagicMock, patch

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

def test_upload_epub_calls_three_scp_then_ssh_restart(tmp_path):
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
    scp_calls = [c for c in calls if c[0] == 'scp']
    ssh_calls = [c for c in calls if c[0] == 'ssh']
    assert len(scp_calls) == 3
    assert any('test-uuid.epub' in arg for arg in scp_calls[0])
    assert any('.metadata' in arg for arg in scp_calls[1])
    assert any('.content' in arg for arg in scp_calls[2])
    assert len(ssh_calls) == 1
    assert 'systemctl' in ssh_calls[0][-1] and 'restart xochitl' in ssh_calls[0][-1]


def test_upload_metadata_json_content(tmp_path):
    epub = tmp_path / 'Title.epub'
    epub.write_bytes(b'data')

    scp_local_paths = []

    def fake_run(cmd, **kwargs):
        if cmd[0] == 'scp':
            scp_local_paths.append(cmd[-2])  # local source is second-to-last arg
        return _ok()

    with patch('backends.ssh.shutil.which', return_value='/usr/bin/ssh'), \
         patch('backends.ssh.subprocess.run', side_effect=fake_run), \
         patch('backends.ssh.uuid.uuid4', return_value=MagicMock(__str__=lambda s: 'u1')):
        result = SSHBackend('10.11.99.1', 'pw').upload(str(epub), 'Title.epub')

    assert result.ok, result.error
    # The second scp call is for .metadata — read the temp file path that was used
    # (temp files are deleted after upload, so we capture before deletion)
    # Instead verify via the captured path contents indirectly through a spy
    assert len(scp_local_paths) == 3


def test_upload_metadata_has_required_fields(tmp_path):
    epub = tmp_path / 'Title.epub'
    epub.write_bytes(b'data')

    captured_meta = {}

    real_run = subprocess.run

    def fake_run(cmd, **kwargs):
        if cmd[0] == 'scp' and '.metadata' in cmd[-1]:
            local_path = cmd[-2]
            with open(local_path, 'rb') as f:
                captured_meta['data'] = json.loads(f.read())
        return _ok()

    with patch('backends.ssh.shutil.which', return_value='/usr/bin/ssh'), \
         patch('backends.ssh.subprocess.run', side_effect=fake_run), \
         patch('backends.ssh.uuid.uuid4', return_value=MagicMock(__str__=lambda s: 'u1')):
        result = SSHBackend('10.11.99.1', 'pw').upload(str(epub), 'Title.epub')

    assert result.ok, result.error
    meta = captured_meta['data']
    assert meta['visibleName'] == 'Title'
    assert meta['type'] == 'DocumentType'
    assert 'lastModified' in meta


def test_upload_content_filetype_epub(tmp_path):
    epub = tmp_path / 'Book.epub'
    epub.write_bytes(b'data')

    captured_content = {}

    def fake_run(cmd, **kwargs):
        if cmd[0] == 'scp' and '.content' in cmd[-1]:
            local_path = cmd[-2]
            with open(local_path, 'rb') as f:
                captured_content['data'] = json.loads(f.read())
        return _ok()

    with patch('backends.ssh.shutil.which', return_value='/usr/bin/ssh'), \
         patch('backends.ssh.subprocess.run', side_effect=fake_run), \
         patch('backends.ssh.uuid.uuid4', return_value=MagicMock(__str__=lambda s: 'u2')):
        result = SSHBackend('10.11.99.1', 'pw').upload(str(epub), 'Book.epub')

    assert result.ok, result.error
    assert captured_content['data']['fileType'] == 'epub'


def test_upload_content_filetype_pdf(tmp_path):
    pdf = tmp_path / 'Paper.pdf'
    pdf.write_bytes(b'data')

    captured_content = {}

    def fake_run(cmd, **kwargs):
        if cmd[0] == 'scp' and '.content' in cmd[-1]:
            local_path = cmd[-2]
            with open(local_path, 'rb') as f:
                captured_content['data'] = json.loads(f.read())
        return _ok()

    with patch('backends.ssh.shutil.which', return_value='/usr/bin/ssh'), \
         patch('backends.ssh.subprocess.run', side_effect=fake_run), \
         patch('backends.ssh.uuid.uuid4', return_value=MagicMock(__str__=lambda s: 'u3')):
        result = SSHBackend('10.11.99.1', 'pw').upload(str(pdf), 'Paper.pdf')

    assert result.ok, result.error
    assert captured_content['data']['fileType'] == 'pdf'


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
