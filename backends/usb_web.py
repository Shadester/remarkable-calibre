import json
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

    def list_books(self) -> list[dict]:
        """Return all DocumentType entries by recursively walking /documents/."""
        books = []
        queue = ['']
        visited = set()
        while queue:
            folder_id = queue.pop(0)
            if folder_id in visited:
                continue
            visited.add(folder_id)
            url = self._base_url() + '/documents/' + folder_id
            try:
                resp = urllib.request.urlopen(url, timeout=self.timeout)
                entries = json.loads(resp.read())
            except Exception:
                continue
            for entry in entries:
                entry_type = entry.get('Type', '')
                name = entry.get('VissibleName') or entry.get('visibleName', '')
                doc_id = entry.get('ID', '')
                if entry_type == 'DocumentType':
                    books.append({'uuid': doc_id, 'visibleName': name})
                elif entry_type == 'CollectionType' and doc_id:
                    queue.append(doc_id)
        return books

    def check_connection(self) -> Result:
        try:
            urllib.request.urlopen(self._base_url() + '/', timeout=self.timeout)
            return Result(ok=True)
        except urllib.error.URLError as e:
            return Result(ok=False, error=str(e.reason))
        except Exception as e:
            return Result(ok=False, error=str(e))

    def _existing_ids(self) -> set:
        """Return the set of all document IDs currently on the device."""
        ids = set()
        queue = ['']
        visited = set()
        while queue:
            folder_id = queue.pop(0)
            if folder_id in visited:
                continue
            visited.add(folder_id)
            try:
                resp = urllib.request.urlopen(
                    self._base_url() + '/documents/' + folder_id, timeout=self.timeout
                )
                for entry in json.loads(resp.read()):
                    doc_id = entry.get('ID', '')
                    if entry.get('Type') == 'DocumentType':
                        ids.add(doc_id)
                    elif entry.get('Type') == 'CollectionType' and doc_id:
                        queue.append(doc_id)
            except Exception:
                break
        return ids

    def upload(self, file_path: str, filename: str, title: str = None, calibre_uuid: str = None) -> Result:
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
        except OSError as e:
            return Result(ok=False, error=str(e))

        before_ids = self._existing_ids()

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
            if resp.status != 201:
                return Result(ok=False, error=f'Unexpected status {resp.status}')
        except urllib.error.HTTPError as e:
            body_excerpt = e.read(200).decode('utf-8', errors='replace')
            return Result(ok=False, error=f'HTTP {e.code}: {body_excerpt}')
        except urllib.error.URLError as e:
            return Result(ok=False, error=str(e.reason))
        except Exception as e:
            return Result(ok=False, error=str(e))

        # Identify the newly created document by diffing IDs.
        new_uuid = None
        try:
            after_ids = self._existing_ids()
            new_ids = after_ids - before_ids
            if new_ids:
                new_uuid = next(iter(new_ids))
        except Exception:
            pass

        return Result(ok=True, uuid=new_uuid)
