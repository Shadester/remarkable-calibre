from calibre.customize import InterfaceActionBase


class SendToRemarkablePlugin(InterfaceActionBase):
    name = 'Send to reMarkable'
    description = 'Send selected books to a USB-tethered reMarkable tablet'
    supported_platforms = ['windows', 'osx', 'linux']
    author = 'remarkablecalibre'
    version = (1, 0, 0)
    minimum_calibre_version = (6, 0, 0)

    actual_plugin = 'calibre_plugins.remarkable.action:SendToRemarkableAction'

    def is_customizable(self):
        return True

    def config_widget(self):
        from calibre_plugins.remarkable.config import ConfigWidget
        return ConfigWidget()

    def save_settings(self, config_widget):
        config_widget.commit()
