"""Stub out calibre and qt modules so tests run without a Calibre installation."""
import json
import os
import sys
import tempfile
import types
from unittest.mock import MagicMock

# ------------------------------------------------------------------ #
# 1. Stub leaf calibre / qt modules with MagicMock                   #
# ------------------------------------------------------------------ #
for _mod in [
    'calibre',
    'calibre.customize',
    'calibre.gui2',
    'calibre.gui2.actions',
    'calibre.utils',
    'calibre.devices',
    'calibre.devices.usbms',
    'qt',
    'qt.core',
]:
    sys.modules.setdefault(_mod, MagicMock())

# DevicePlugin must be a real class so that RemarkableDevice can subclass it.
class _FakeDevicePlugin:
    pass

_iface_mod = types.ModuleType('calibre.devices.interface')
_iface_mod.DevicePlugin = _FakeDevicePlugin
sys.modules['calibre.devices.interface'] = _iface_mod

# ------------------------------------------------------------------ #
# 2. Functional stubs for calibre.devices.usbms.books and            #
#    calibre.utils.config so device.py logic can be tested.          #
# ------------------------------------------------------------------ #

class _FakeBook:
    def __init__(self, prefix='', lpath='', other=None):
        self.lpath = lpath
        self.path = lpath
        self.uuid = None
        self.title = ''
        self.authors = []
        self._new_book = False
        if other is not None:
            for attr in ('uuid', 'title', 'authors', 'series', 'series_index'):
                val = getattr(other, attr, None)
                if val is not None:
                    setattr(self, attr, val)

    def __eq__(self, other):
        return self.lpath == getattr(other, 'lpath', None)

    def __hash__(self):
        return hash(self.lpath)


class _FakeBookList(list):
    def __init__(self, *args, **kwargs):
        super().__init__()

    def add_book(self, book, replace_metadata=False):
        if replace_metadata:
            for i, b in enumerate(self):
                if b.lpath == book.lpath:
                    self[i] = book
                    return
        self.append(book)


class _FakeJsonCodec:
    def encode_to_file(self, f, booklist):
        data = [{'lpath': b.lpath, 'uuid': b.uuid, 'title': b.title, 'authors': b.authors}
                for b in booklist]
        f.write(json.dumps(data).encode())

    def decode_from_file(self, f, booklist, **kwargs):
        for item in json.loads(f.read()):
            b = _FakeBook(lpath=item.get('lpath', ''))
            b.uuid = item.get('uuid')
            b.title = item.get('title', '')
            b.authors = item.get('authors', [])
            booklist.append(b)


_books_mod = types.ModuleType('calibre.devices.usbms.books')
_books_mod.Book = _FakeBook
_books_mod.BookList = _FakeBookList
_books_mod.JsonCodec = _FakeJsonCodec
sys.modules['calibre.devices.usbms.books'] = _books_mod

_tmp_config_dir = tempfile.mkdtemp()
_utils_config_mod = types.ModuleType('calibre.utils.config')
_utils_config_mod.config_dir = _tmp_config_dir
_utils_config_mod.JSONConfig = MagicMock()
sys.modules['calibre.utils.config'] = _utils_config_mod

# ------------------------------------------------------------------ #
# 3. Add project root to sys.path so `device`, `config`, `backends`  #
#    are importable directly (the same path device.py itself inserts) #
# ------------------------------------------------------------------ #
_project_root = os.path.dirname(os.path.dirname(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# ------------------------------------------------------------------ #
# 4. Replace MagicMock prefs with a real dict so tests can set/read  #
#    config values without MagicMock return values leaking into URLs. #
# ------------------------------------------------------------------ #
import config as _config_mod
_config_mod.prefs = {
    'host': '10.11.99.1',
    'connect_timeout_seconds': 2,
    'connection_type': 'usb_web',
    'ssh_password': '',
}


# ------------------------------------------------------------------ #
# 5. Helper: a minimal Calibre-like Metadata object for tests        #
# ------------------------------------------------------------------ #
class FakeMetadata:
    def __init__(self, title='Test Book', authors=None, uuid=None):
        self.title = title
        self.authors = authors or ['Test Author']
        self.uuid = uuid or 'calibre-uuid-test'
