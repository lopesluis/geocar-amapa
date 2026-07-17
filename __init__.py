# -*- coding: utf-8 -*-
"""
GeoCAR Amapá - Plugin QGIS para processamento ambiental do CAR
SEMA-AP / Setor CAR
"""

def classFactory(iface):
    from .geocar_amapa import GeoCARAmapa
    return GeoCARAmapa(iface)
