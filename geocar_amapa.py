# -*- coding: utf-8 -*-
"""
GeoCAR Amapá - Classe principal do plugin
"""

import os
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from .geocar_amapa_dialog import GeoCARAmapaDiag


class GeoCARAmapa:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = 'GeoCAR Amapá'
        self.dlg = None

    def add_action(self, icon_path, text, callback, parent=None):
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        self.iface.addToolBarIcon(action)
        self.iface.addPluginToMenu(self.menu, action)
        self.actions.append(action)
        return action

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        self.add_action(
            icon_path,
            text='GeoCAR Amapá',
            callback=self.run,
            parent=self.iface.mainWindow()
        )

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu('GeoCAR Amapá', action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        if self.dlg is None:
            self.dlg = GeoCARAmapaDiag(self.iface)
        self.dlg.show()
        self.dlg.raise_()
        self.dlg.activateWindow()
