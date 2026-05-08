import json
import os
import shlex
import shutil
import stat
import subprocess
import tempfile
import time
import uuid

from .base import Backend, Result

_XOCHITL_DIR = '/home/root/.local/share/remarkable/xochitl'
_SSH_OPTS = [
    '-o', 'StrictHostKeyChecking=no',
    '-o', 'NumberOfPasswordPrompts=1',
    '-o', 'BatchMode=no',
    '-o', 'ConnectTimeout=5',
]


def _askpass_ctx(password: str):
    """Context manager that writes a temp askpass script and returns the augmented env."""
    f = tempfile.NamedTemporaryFile('w', suffix='.sh', delete=False)
    f.write(f'#!/bin/sh\nprintf "%s" {shlex.quote(password)}\n')
    f.close()
    os.chmod(f.name, stat.S_IRWXU)
    env = os.environ.copy()
    env['SSH_ASKPASS'] = f.name
    env['SSH_ASKPASS_REQUIRE'] = 'force'
    return env, f.name


def _run_ssh_capture(host: str, password: str, command: str, timeout: int = 30) -> tuple[bool, str, str]:
    """Run an SSH command and return (ok, stdout, stderr)."""
    env, askpass = _askpass_ctx(password)
    try:
        r = subprocess.run(
            ['ssh'] + _SSH_OPTS + [f'root@{host}', command],
            env=env, capture_output=True, timeout=timeout,
        )
        return r.returncode == 0, r.stdout.decode(errors='replace'), r.stderr.decode(errors='replace')
    finally:
        os.unlink(askpass)


def _run_ssh(host: str, password: str, command: str, timeout: int = 30) -> tuple[bool, str]:
    env, askpass = _askpass_ctx(password)
    try:
        r = subprocess.run(
            ['ssh'] + _SSH_OPTS + [f'root@{host}', command],
            env=env, capture_output=True, timeout=timeout,
        )
        return r.returncode == 0, r.stderr.decode(errors='replace')
    finally:
        os.unlink(askpass)


def _run_scp(host: str, password: str, local_path: str, remote_path: str, timeout: int = 120) -> tuple[bool, str]:
    env, askpass = _askpass_ctx(password)
    try:
        r = subprocess.run(
            ['scp'] + _SSH_OPTS + [local_path, f'root@{host}:{remote_path}'],
            env=env, capture_output=True, timeout=timeout,
        )
        return r.returncode == 0, r.stderr.decode(errors='replace')
    finally:
        os.unlink(askpass)


class SSHBackend(Backend):
    def __init__(self, host: str = '10.11.99.1', password: str = '', timeout: int = 2):
        self.host = host
        self.password = password
        self.timeout = timeout

    def _ssh_available(self) -> bool:
        return shutil.which('ssh') is not None

    def list_books(self) -> list[dict]:
        """Return a list of dicts with uuid/visibleName for all non-deleted DocumentType entries."""
        if not self._ssh_available():
            return []
        try:
            cmd = (
                'grep -rl "DocumentType" /home/root/.local/share/remarkable/xochitl/ | '
                'while read f; do '
                '  grep -q \'"deleted": true\' "$f" && continue; '
                '  uuid=$(basename "$f" .metadata); '
                '  name=$(grep "visibleName" "$f" | sed \'s/.*visibleName.*: *"//;s/".*//\'); '
                '  printf "%s\\t%s\\n" "$uuid" "$name"; '
                'done'
            )
            ok, out, err = _run_ssh_capture(self.host, self.password, cmd, timeout=15)
            if not out.strip():
                raise RuntimeError(f'SSH list_books got no output. ok={ok}, stderr={err!r}')
            books = []
            for line in out.splitlines():
                parts = line.split('\t', 1)
                if len(parts) == 2:
                    books.append({'uuid': parts[0], 'visibleName': parts[1]})
            return books
        except Exception as e:
            raise RuntimeError(f'list_books failed: {e}') from e

    def check_connection(self) -> Result:
        if not self._ssh_available():
            return Result(ok=False, error='ssh not found in PATH')
        try:
            ok, err = _run_ssh(self.host, self.password, 'true', timeout=self.timeout + 3)
            return Result(ok=ok, error=err if not ok else None)
        except Exception as e:
            return Result(ok=False, error=str(e))

    def upload(self, file_path: str, filename: str, title: str = None) -> Result:
        if not self._ssh_available():
            return Result(ok=False, error='ssh not found in PATH')
        try:
            ext = os.path.splitext(filename)[1].lstrip('.').lower()
            if ext not in ('epub', 'pdf'):
                return Result(ok=False, error=f'SSH backend only supports epub and pdf, got {ext!r}')

            doc_uuid = str(uuid.uuid4())
            remote_base = f'{_XOCHITL_DIR}/{doc_uuid}'
            visible_name = title or os.path.splitext(filename)[0]

            metadata_bytes = json.dumps({
                'visibleName': visible_name,
                'type': 'DocumentType',
                'parent': '',
                'lastModified': str(int(time.time() * 1000)),
                'version': 0,
                'deleted': False,
                'pinned': False,
                'synced': False,
                'modified': False,
                'metadatamodified': False,
                'lastOpened': '0',
                'lastOpenedPage': 0,
            }, indent=2).encode()

            content_bytes = json.dumps({
                'fileType': ext,
                'pageCount': 0,
                'pages': [],
                'coverPageNumber': 0,
                'extraMetadata': {},
                'transform': {},
                'margins': 180,
                'textScale': 1,
                'lineHeight': -1,
                'orientation': 'portrait',
                'textAlignment': 'justify',
                'formatVersion': 1,
            }, indent=2).encode()

            meta_tmp = tempfile.NamedTemporaryFile('wb', suffix='.metadata', delete=False)
            meta_tmp.write(metadata_bytes)
            meta_tmp.close()
            content_tmp = tempfile.NamedTemporaryFile('wb', suffix='.content', delete=False)
            content_tmp.write(content_bytes)
            content_tmp.close()
            try:
                ok, err = _run_scp(self.host, self.password, file_path, f'{remote_base}.{ext}')
                if not ok:
                    return Result(ok=False, error=f'scp failed: {err}')

                ok, err = _run_scp(self.host, self.password, meta_tmp.name, f'{remote_base}.metadata')
                if not ok:
                    return Result(ok=False, error=f'metadata upload failed: {err}')

                ok, err = _run_scp(self.host, self.password, content_tmp.name, f'{remote_base}.content')
                if not ok:
                    return Result(ok=False, error=f'content upload failed: {err}')
            finally:
                os.unlink(meta_tmp.name)
                os.unlink(content_tmp.name)

            # Ensure files are readable, then restart xochitl asynchronously.
            # --no-block returns immediately; xochitl restarts in the background.
            restart_cmd = (
                f'sync && chmod 644 {shlex.quote(remote_base)}.epub '
                f'{shlex.quote(remote_base)}.pdf '
                f'{shlex.quote(remote_base)}.metadata '
                f'{shlex.quote(remote_base)}.content 2>/dev/null; '
                f'systemctl --no-block restart xochitl'
            )
            ok, err = _run_ssh(self.host, self.password, restart_cmd, timeout=10)
            if not ok:
                return Result(ok=False, error=f'xochitl restart failed: {err}')
            return Result(ok=True)
        except Exception as e:
            return Result(ok=False, error=str(e))
