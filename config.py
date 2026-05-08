from calibre.utils.config import JSONConfig
from qt.core import (
    QComboBox, QFormLayout, QLabel, QLineEdit, QSpinBox, QWidget,
)

prefs = JSONConfig('plugins/remarkable')
prefs.defaults['host'] = '10.11.99.1'
prefs.defaults['connect_timeout_seconds'] = 2
prefs.defaults['connection_type'] = 'ssh'
prefs.defaults['ssh_password'] = ''


class ConfigWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QFormLayout(self)

        self._conn_type = QComboBox()
        self._conn_type.addItem('SSH (recommended)', 'ssh')
        self._conn_type.addItem('USB web interface (upload only)', 'usb_web')
        idx = self._conn_type.findData(prefs['connection_type'])
        if idx >= 0:
            self._conn_type.setCurrentIndex(idx)
        layout.addRow(QLabel('Connection type:'), self._conn_type)

        self._host = QLineEdit(prefs['host'])
        layout.addRow(QLabel('Tablet host:'), self._host)

        self._timeout = QSpinBox()
        self._timeout.setRange(1, 30)
        self._timeout.setSuffix(' s')
        self._timeout.setValue(prefs['connect_timeout_seconds'])
        layout.addRow(QLabel('Connection timeout:'), self._timeout)

        self._ssh_password = QLineEdit(prefs['ssh_password'])
        self._ssh_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._ssh_password.setPlaceholderText('Settings → Help → Copyrights and licenses')
        layout.addRow(QLabel('SSH password:'), self._ssh_password)

        self._conn_type.currentIndexChanged.connect(self._update_ssh_visibility)
        self._update_ssh_visibility()

    def _update_ssh_visibility(self):
        is_ssh = self._conn_type.currentData() == 'ssh'
        self._ssh_password.setVisible(is_ssh)
        self.layout().labelForField(self._ssh_password).setVisible(is_ssh)

    def commit(self):
        prefs['connection_type'] = self._conn_type.currentData()
        prefs['host'] = self._host.text().strip()
        prefs['connect_timeout_seconds'] = self._timeout.value()
        prefs['ssh_password'] = self._ssh_password.text()
