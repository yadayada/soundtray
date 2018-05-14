#!/usr/env python2

__version__ = '0.0.2'

import libsoundtouch
import sys

from functools import partial

try:
    from PyQt5.QtGui import QIcon, QCursor, QIcon
    from PyQt5.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QInputDialog
    from PyQt5.QtCore import QCoreApplication, QPoint
except:
    from PyQt4.QtGui import QApplication, QSystemTrayIcon, QMenu, QMessageBox, QIcon, QInputDialog, QCursor
    from PyQt4.QtCore import QCoreApplication, QPoint

# https://specifications.freedesktop.org/icon-naming-spec/icon-naming-spec-latest.html
TRAY_ICON_NAME = 'multimedia-volume-control'
SRC_ICON_NAME = 'audio-card'
BT_ICON_NAME = 'bluetooth-active'
AUX_ICON_NAME = ''
URL_ICON_NAME = 'document-open'
PLAY_PAUSE_ICON_NAME = 'media-playback-start'
VOL_UP_ICON_NAME = 'audio-volume-high'
VOL_DN_ICON_NAME = 'audio-volume-low'
CLOSE_ICON_NAME = 'window-close'

VOL_INCREMENT = 3

DISCOVERY_TIMEOUT = 2
STAT_QR_INTERVAL = 5


# noinspection PyPep8Naming
class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, icon, device):
        QSystemTrayIcon.__init__(self, icon)

        self.menu = QMenu()
        self.dev = device
        self.vol = None
        self.presets = None
        self.status = None

        self.statusAction = None
        self.srcMenu = None
        self.initMenu()
        self.initDynamicActions()
        self.init_listeners()

    def initMenu(self):
        self.statusAction = self.menu.addAction(QIcon.fromTheme(SRC_ICON_NAME), '')
        self.statusAction.setIconVisibleInMenu(True)

        self.menu.addSeparator()

        self.srcMenu = self.menu.addMenu('&Sources')
        bt = self.srcMenu.addAction(QIcon.fromTheme(BT_ICON_NAME), '&Bluetooth')
        bt.setIconVisibleInMenu(True)
        bt.triggered.connect(self.dev.select_source_bluetooth)

        ax = self.srcMenu.addAction('&AUX')
        ax.triggered.connect(self.dev.select_source_aux)

        ua = self.srcMenu.addAction(QIcon.fromTheme(URL_ICON_NAME), '&URL')
        ua.setIconVisibleInMenu(True)
        ua.triggered.connect(self.play_url)

        self.menu.addMenu(self.srcMenu)

        pp = self.menu.addAction(QIcon.fromTheme(PLAY_PAUSE_ICON_NAME), 'Play/&Pause')
        pp.setIconVisibleInMenu(True)
        pp.triggered.connect(self.dev.play_pause)

        vu = self.menu.addAction(QIcon.fromTheme(VOL_UP_ICON_NAME), 'Volume &Up')
        vu.setIconVisibleInMenu(True)
        vu.triggered.connect(self.vol_up)

        vd = self.menu.addAction(QIcon.fromTheme(VOL_DN_ICON_NAME), 'Volume &Down')
        vd.setIconVisibleInMenu(True)
        vd.triggered.connect(self.vol_down)

        self.menu.addSeparator()

        ea = self.menu.addAction(QIcon.fromTheme(CLOSE_ICON_NAME), '&Exit')
        ea.setIconVisibleInMenu(True)
        ea.triggered.connect(QCoreApplication.exit)

        self.setContextMenu(self.menu)
        self.activated.connect(self.clicked)

    def initDynamicActions(self):
        self.vol = self.dev.volume().actual
        self.presets = self.dev.presets()
        self.status = self.dev.status()
        self.onDeviceChange()

        if self.presets:
            self.srcMenu.addSeparator()
        for i, p in enumerate(self.presets):
            a = self.srcMenu.addAction(p.name)
            a.triggered.connect(partial(self.dev.select_preset, self.presets[i]))

    def init_listeners(self):
        self.dev.add_volume_listener(self.volume_listener)
        self.dev.add_presets_listener(self.presets_listener)
        self.dev.add_status_listener(self.status_listener)
        self.dev.add_device_info_listener(self.device_info_listener)
        self.dev.start_notification()

    def onDeviceChange(self):
        self.statusAction.setText(self.status.source + ' %i' % self.vol)

    # TODO: find non-manual way to mirror context activation
    def clicked(self, QSystemTrayIcon_ActivationReason):
        if QSystemTrayIcon_ActivationReason == QSystemTrayIcon.Trigger:
            if not self.menu.isVisible():
                open_at = QCursor.pos()
                open_at.setY(self.geometry().top())
                open_at -= QPoint(0, self.menu.sizeHint().height())
                self.menu.move(open_at)
                self.menu.show()

    def eventFilter(self, QObject, QEvent):
        if QEvent.type() == QEvent.Wheel:
            try:
                delta = QEvent.angleDelta().y()
            except AttributeError:
                delta = QEvent.delta()
            print delta
            if delta > 0:
                self.vol_up()
                return True
            elif delta < 0:
                self.vol_down()
                return True
        return False

    def vol_up(self):
        v = self.dev.volume().actual
        self.dev.set_volume(v + VOL_INCREMENT)

    def vol_down(self):
        v = self.dev.volume().actual
        self.dev.set_volume(v - VOL_INCREMENT)

    def play_url(self):
        d, ok = QInputDialog.getText(None, 'Enter a media/streaming URL', 'URL')
        if ok:
            self.dev.play_url(d)

    def volume_listener(self, vol):
        self.vol = vol.actual
        self.onDeviceChange()

    def status_listener(self, stat):
        self.status = stat
        self.onDeviceChange()

    def presets_listener(self, presets):
        self.presets = presets

    def device_info_listener(self, device_info):
        print(device_info)


def main():
    app = QApplication(sys.argv)

    stds = libsoundtouch.discover_devices(timeout=DISCOVERY_TIMEOUT)

    if len(stds) < 1:
        d = QMessageBox()
        d.setText('No device')
        d.setInformativeText('Device discovery did not find any SoundTouch devices.')
        d.setIcon(QMessageBox.Warning)
        # d.setStandardButtons(QMessageBox.Retry | QMessageBox.Close)
        r = d.exec_()
        sys.exit(1)

    app.setQuitOnLastWindowClosed(False)  # prevent QInputDialog from closing app

    std = stds[0]

    trayIcon = SystemTrayIcon(QIcon.fromTheme(TRAY_ICON_NAME), std)
    app.installEventFilter(trayIcon)

    trayIcon.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
