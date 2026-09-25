"""
Qt Compatibility Abstraction Layer for CuteMix.
Supports PySide6, PyQt6, and PyQt5 transparently.
Provides safe fallbacks if Qt is not yet installed.
"""

import sys

QT_LIB = None
QtCore = None
QtGui = None
QtWidgets = None
QtNetwork = None
Signal = None
Slot = None
Property = None
Qt = None

try:
    from PySide6 import QtCore, QtGui, QtWidgets, QtNetwork
    from PySide6.QtCore import Signal, Slot, Property, Qt
    QT_LIB = "PySide6"
except ImportError:
    try:
        from PyQt6 import QtCore, QtGui, QtWidgets, QtNetwork
        from PyQt6.QtCore import pyqtSignal as Signal, pyqtSlot as Slot, pyqtProperty as Property, Qt
        QT_LIB = "PyQt6"
    except ImportError:
        try:
            from PyQt5 import QtCore, QtGui, QtWidgets, QtNetwork
            from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot, pyqtProperty as Property, Qt
            QT_LIB = "PyQt5"
        except ImportError:
            pass


def is_qt_available() -> bool:
    return QT_LIB is not None


def get_qt_lib() -> str:
    return QT_LIB


# Helper to get AlignmentFlag across Qt versions
def align_center():
    if QT_LIB in ("PySide6", "PyQt6") and Qt is not None:
        return Qt.AlignmentFlag.AlignCenter
    elif Qt is not None:
        return Qt.AlignCenter
    return None


def align_left():
    if QT_LIB in ("PySide6", "PyQt6") and Qt is not None:
        return Qt.AlignmentFlag.AlignLeft
    elif Qt is not None:
        return Qt.AlignLeft
    return None


def align_right():
    if QT_LIB in ("PySide6", "PyQt6") and Qt is not None:
        return Qt.AlignmentFlag.AlignRight
    elif Qt is not None:
        return Qt.AlignRight
    return None


def align_vcenter():
    if QT_LIB in ("PySide6", "PyQt6") and Qt is not None:
        return Qt.AlignmentFlag.AlignVCenter
    elif Qt is not None:
        return Qt.AlignVCenter
    return None


def orient_vertical():
    if QT_LIB in ("PySide6", "PyQt6") and Qt is not None:
        return Qt.Orientation.Vertical
    elif Qt is not None:
        return Qt.Vertical
    return None


def orient_horizontal():
    if QT_LIB in ("PySide6", "PyQt6") and Qt is not None:
        return Qt.Orientation.Horizontal
    elif Qt is not None:
        return Qt.Horizontal
    return None
