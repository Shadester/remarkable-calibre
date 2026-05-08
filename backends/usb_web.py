import os
import uuid
import urllib.request
import urllib.error

from .base import Backend, Result


class USBWebBackend(Backend):
    def __init__(self, host: str = '10.11.99.1', timeout: int = 2, upload_timeout: int = 300):
        self.host = host
        self.timeout = timeout
        self.upload_timeout = upload_timeout

    def _base_url(self) -> str:
        if self.host.startswith('http://') or self.host.startswith('https://'):
            return self.host.rstrip('/')
        return f'http://{self.host}'

    def check_connection(self) -> Result:
        try:
            urllib.request.urlopen(self._base_url() + '/', timeout=self.timeout)
            return Result(ok=True)
        except urllib.error.URLError as e:
            return Result(ok=False, error=str(e.reason))
        except Exception as e:
            return Result(ok=False, error=str(e))

    def upload(self, file_path: str, filename: str, title: str = None) -> Result:
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
        except OSError as e:
            return Result(ok=False, error=str(e))

        boundary = uuid.uuid4().hex
        body = (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f'Content-Type: application/octet-stream\r\n'
            f'\r\n'
        ).encode() + content + f'\r\n--{boundary}--\r\n'.encode()

        req = urllib.request.Request(
            self._base_url() + '/upload',
            data=body,
            method='POST',
        )
        req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
        req.add_header('Content-Length', str(len(body)))

        try:
            resp = urllib.request.urlopen(req, timeout=self.upload_timeout)
            if resp.status == 201:
                return Result(ok=True)
            return Result(ok=False, error=f'Unexpected status {resp.status}')
        except urllib.error.HTTPError as e:
            body_excerpt = e.read(200).decode('utf-8', errors='replace')
            return Result(ok=False, error=f'HTTP {e.code}: {body_excerpt}')
        except urllib.error.URLError as e:
            return Result(ok=False, error=str(e.reason))
        except Exception as e:
            return Result(ok=False, error=str(e))
