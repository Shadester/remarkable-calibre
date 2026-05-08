"""Stub out calibre and qt modules so tests run without a Calibre installation."""
import os
import sys
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
    'calibre.utils.config',
    'calibre.devices',
    'calibre.devices.usbms',
    'calibre.devices.usbms.books',
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
# 2. Add project root to sys.path so `device`, `config`, `backends`  #
#    are importable directly (the same path device.py itself inserts) #
# ------------------------------------------------------------------ #
_project_root = os.path.dirname(os.path.dirname(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# ------------------------------------------------------------------ #
# 3. Replace MagicMock prefs with a real dict so tests can set/read  #
#    config values without MagicMock return values leaking into URLs. #
# ------------------------------------------------------------------ #
import config as _config_mod
_config_mod.prefs = {
    'host': '10.11.99.1',
    'connect_timeout_seconds': 2,
}
