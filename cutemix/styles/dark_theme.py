"""
Dark Studio Theme for CuteMix.
Inspired by hardware mixing consoles (UAD Console / SSL / MOTU CueMix FX).
Clean typography, high contrast, subtle borders, hardware-styled illuminated buttons.
"""

DARK_STYLESHEET = """
/* Global Application Style */
QWidget {
    background-color: #17181c;
    color: #c7ccd2;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 11px;
    selection-background-color: #1c525e;
    selection-color: #ffffff;
}

QMainWindow, QDialog {
    background-color: #141518;
}

/* ToolBar & MenuBar */
QMenuBar {
    background-color: #1a1c20;
    border-bottom: 1px solid #0d0e10;
    padding: 2px 4px;
}
QMenuBar::item {
    background: transparent;
    padding: 4px 8px;
    border-radius: 2px;
}
QMenuBar::item:selected {
    background-color: #282c34;
    color: #ffffff;
}

QMenu {
    background-color: #1d2025;
    border: 1px solid #333740;
    padding: 4px 0px;
}
QMenu::item {
    padding: 5px 24px 5px 16px;
}
QMenu::item:selected {
    background-color: #254a54;
    color: #4fd6e6;
}
QMenu::separator {
    height: 1px;
    background-color: #2b2f38;
    margin: 4px 0px;
}

QToolBar {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #25282d, stop:1 #1c1e22);
    border-bottom: 1px solid #0c0d0f;
    spacing: 6px;
    padding: 3px 8px;
}

/* Tabs */
QTabWidget::pane {
    border-top: 1px solid #0d0e10;
    background-color: #17181c;
}

QTabBar::tab {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #22252a, stop:1 #1a1b1f);
    color: #8c939d;
    padding: 8px 18px;
    margin-right: 2px;
    border-top-left-radius: 3px;
    border-top-right-radius: 3px;
    border: 1px solid #23272e;
    border-bottom: none;
    font-weight: bold;
    font-size: 11px;
    letter-spacing: 0.5px;
}

QTabBar::tab:selected {
    color: #eef2f5;
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #28373d, stop:1 #1c262a);
    border-top: 2px solid #2ec4d6;
    border-left: 1px solid #2ec4d6;
    border-right: 1px solid #2ec4d6;
}

QTabBar::tab:hover:!selected {
    color: #d1d7de;
    background-color: #26292f;
}

/* ScrollBars */
QScrollBar:horizontal {
    background-color: #121316;
    height: 12px;
    margin: 0px;
    border: 1px solid #1c1e22;
}
QScrollBar::handle:horizontal {
    background-color: #323740;
    min-width: 28px;
    border-radius: 3px;
    margin: 1px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #454c59;
}
QScrollBar:vertical {
    background-color: #121316;
    width: 12px;
    margin: 0px;
    border: 1px solid #1c1e22;
}
QScrollBar::handle:vertical {
    background-color: #323740;
    min-height: 28px;
    border-radius: 3px;
    margin: 1px;
}
QScrollBar::handle:vertical:hover {
    background-color: #454c59;
}
QScrollBar::add-line, QScrollBar::sub-line {
    width: 0px;
    height: 0px;
}

/* Push Buttons & Tool Buttons */
QPushButton {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2c3036, stop:1 #202227);
    color: #c7ccd2;
    border: 1px solid #0f1013;
    border-radius: 2px;
    padding: 4px 10px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #363b43, stop:1 #272a30);
    color: #ffffff;
    border-color: #1e2229;
}
QPushButton:pressed {
    background-color: #16181b;
}
QPushButton:disabled {
    color: #555b63;
    background-color: #1b1d20;
    border-color: #121315;
}

/* Channel Strip Toggle Buttons */
QPushButton.btn-mute {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2a2d33, stop:1 #1e2024);
    color: #838a94;
    font-weight: bold;
    font-size: 10px;
    border: 1px solid #111215;
    border-radius: 2px;
}
QPushButton.btn-mute:checked {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e2554b, stop:1 #a8322a);
    color: #ffffff;
    border: 1px solid #751a14;
}

QPushButton.btn-solo {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2a2d33, stop:1 #1e2024);
    color: #838a94;
    font-weight: bold;
    font-size: 10px;
    border: 1px solid #111215;
    border-radius: 2px;
}
QPushButton.btn-solo:checked {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f0a63a, stop:1 #b87418);
    color: #1c1002;
    border: 1px solid #854d05;
}

QPushButton.btn-pad {
    font-size: 9px;
    font-weight: bold;
    color: #79808a;
    border: 1px solid #111215;
}
QPushButton.btn-pad:checked {
    background-color: #d97724;
    color: #ffffff;
}

QPushButton.btn-phase {
    font-size: 9px;
    font-weight: bold;
    color: #79808a;
    border: 1px solid #111215;
}
QPushButton.btn-phase:checked {
    background-color: #2499a8;
    color: #ffffff;
}

QPushButton.btn-link {
    font-size: 9px;
    font-weight: bold;
    color: #79808a;
    border: 1px solid #111215;
}
QPushButton.btn-link:checked {
    background-color: #2ec4d6;
    color: #0d1e22;
}

QPushButton.btn-gang {
    font-size: 9px;
    font-weight: bold;
    color: #79808a;
    border: 1px solid #111215;
}
QPushButton.btn-gang:checked {
    background-color: #9066d9;
    color: #ffffff;
}

/* Master Solo Indicator Button */
QPushButton.btn-master-solo {
    font-weight: bold;
    font-size: 11px;
    color: #6e747c;
    background-color: #1f2227;
    border: 1px solid #2d3138;
    border-radius: 3px;
    padding: 6px 12px;
}
QPushButton.btn-master-solo.active {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffb84d, stop:1 #e08c19);
    color: #1a0f00;
    border: 1px solid #ffaa33;
}

/* Inputs, SpinBoxes, ComboBoxes */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #1e2025;
    border: 1px solid #2f343e;
    border-radius: 2px;
    color: #e4e7ea;
    padding: 3px 6px;
    selection-background-color: #2ec4d6;
    selection-color: #0b1a1d;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #2ec4d6;
}
QComboBox::drop-down {
    border: none;
    width: 18px;
}
QComboBox QAbstractItemView {
    background-color: #1d2025;
    border: 1px solid #333740;
    selection-background-color: #254a54;
    color: #c7ccd2;
}

/* Status Bar */
QStatusBar {
    background-color: #141518;
    border-top: 1px solid #0d0e10;
    color: #7d848e;
    font-size: 10px;
    padding: 2px 8px;
}
QStatusBar QLabel {
    color: #7d848e;
}

/* Tables & Lists */
QTableWidget, QTableView, QTreeWidget, QListWidget {
    background-color: #181a1e;
    border: 1px solid #262930;
    gridline-color: #23262d;
    color: #c7ccd2;
    selection-background-color: #203a42;
    selection-color: #4fd6e6;
}
QHeaderView::section {
    background-color: #202328;
    color: #8c939d;
    padding: 4px 6px;
    border: 1px solid #141619;
    font-weight: bold;
    font-size: 10px;
}

/* Group Boxes */
QGroupBox {
    border: 1px solid #272a31;
    border-radius: 3px;
    margin-top: 14px;
    padding: 10px 8px 6px 8px;
    font-weight: bold;
    color: #9aa1ab;
    font-size: 11px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 8px;
    padding: 0 4px;
    background-color: #17181c;
}
"""
