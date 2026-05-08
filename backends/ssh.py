import io
import json
import os
import time
import uuid

from .base import Backend, Result

_XOCHITL_DIR = '/home/root/.local/share/remarkable/xochitl'

try:
    import paramiko
    _PARAMIKO_AVAILABLE = True
except ImportError:
    _PARAMIKO_AVAILABLE = False


class SSHBackend(Backend):
    def __init__(self, host: str = '10.11.99.1', password: str = '', timeout: int = 2, username: str = 'root'):
        self.host = host
        self.password = password
        self.timeout = timeout
        self.username = username

    def _connect(self):
        if not _PARAMIKO_AVAILABLE:
            raise RuntimeError('paramiko is required for SSH backend but is not installed')
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            self.host,
            username=self.username,
            password=self.password,
            timeout=self.timeout,
            banner_timeout=self.timeout,
            auth_timeout=self.timeout,
            look_for_keys=False,
            allow_agent=False,
        )
        return client

    def check_connection(self) -> Result:
        if not _PARAMIKO_AVAILABLE:
            return Result(ok=False, error='paramiko is required for SSH backend but is not installed')
        try:
            client = self._connect()
            client.close()
            return Result(ok=True)
        except Exception as e:
            return Result(ok=False, error=str(e))

    def upload(self, file_path: str, filename: str) -> Result:
        if not _PARAMIKO_AVAILABLE:
            return Result(ok=False, error='paramiko is required for SSH backend but is not installed')
        try:
            doc_uuid = str(uuid.uuid4())
            ext = os.path.splitext(filename)[1].lstrip('.').lower()
            if ext not in ('epub', 'pdf'):
                return Result(ok=False, error=f'SSH backend only supports epub and pdf, got {ext!r}')

            visible_name = os.path.splitext(filename)[0]
            last_modified = str(int(time.time() * 1000))

            metadata = {
                'visibleName': visible_name,
                'type': 'DocumentType',
                'parent': '',
                'lastModified': last_modified,
                'version': 0,
                'deleted': False,
                'pinned': False,
                'synced': False,
                'modified': False,
                'metadatamodified': False,
                'lastOpened': '0',
                'lastOpenedPage': 0,
            }
            content = {
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
            }

            client = self._connect()
            try:
                sftp = client.open_sftp()
                sftp.put(file_path, f'{_XOCHITL_DIR}/{doc_uuid}.{ext}')
                _sftp_write_json(sftp, f'{_XOCHITL_DIR}/{doc_uuid}.metadata', metadata)
                _sftp_write_json(sftp, f'{_XOCHITL_DIR}/{doc_uuid}.content', content)
                sftp.close()
                client.exec_command('systemctl restart xochitl')
            finally:
                client.close()

            return Result(ok=True)
        except Exception as e:
            return Result(ok=False, error=str(e))


def _sftp_write_json(sftp, remote_path: str, data: dict):
    payload = json.dumps(data, indent=2).encode()
    with sftp.open(remote_path, 'wb') as f:
        f.write(payload)
