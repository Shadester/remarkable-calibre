from calibre.utils.config import JSONConfig
from qt.core import QFormLayout, QLabel, QLineEdit, QSpinBox, QWidget

prefs = JSONConfig('plugins/remarkable')
prefs.defaults['host'] = '10.11.99.1'
prefs.defaults['connect_timeout_seconds'] = 2


class ConfigWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QFormLayout(self)

        self._host = QLineEdit(prefs['host'])
        layout.addRow(QLabel('Tablet host:'), self._host)

        self._timeout = QSpinBox()
        self._timeout.setRange(1, 30)
        self._timeout.setSuffix(' s')
        self._timeout.setValue(prefs['connect_timeout_seconds'])
        layout.addRow(QLabel('Connection timeout:'), self._timeout)

    def commit(self):
        prefs['host'] = self._host.text().strip()
        prefs['connect_timeout_seconds'] = self._timeout.value()
