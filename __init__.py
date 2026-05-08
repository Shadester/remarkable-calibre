import os
import sys

# Ensure the plugin's own directory is on sys.path so `device`, `config`, and
# `backends` are importable both inside Calibre (zip-extracted) and in tests.
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

from calibre.devices.interface import DevicePlugin  # noqa: F401
from device import RemarkableDevice  # noqa: F401
