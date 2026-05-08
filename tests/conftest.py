"""Stub out calibre modules so backend/logic tests run without a Calibre installation."""
import sys
from unittest.mock import MagicMock

for mod in [
    'calibre',
    'calibre.customize',
    'calibre.gui2',
    'calibre.gui2.actions',
]:
    sys.modules.setdefault(mod, MagicMock())
