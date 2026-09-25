"""
Matrix Overview View for CuteMix.
Displays an Input Channels × Mix Buses matrix table, showing send levels,
pans, mutes, and solos across all monitor mixes simultaneously.
"""

from ..qt_compat import QtCore, QtGui, QtWidgets, Signal, Qt, is_qt_available
from ..model.mixer_state import MixerState
from ..model.config import AppConfig
from ..osc.cuemix_protocol import format_db, format_pan, norm_to_db, norm_to_pan

if is_qt_available():
    class MatrixView(QtWidgets.QWidget):
        faderChanged = Signal(int, int, float)  # bus, ch, val
        panChanged = Signal(int, int, float)
        muteChanged = Signal(int, int, bool)
        soloChanged = Signal(int, int, bool)

        def __init__(self, mixer_state: MixerState, config: AppConfig, parent=None):
            super().__init__(parent)
            self.state = mixer_state
            self.config = config

            self._build_ui()

        def _build_ui(self):
            layout = QtWidgets.QVBoxLayout(self)
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setSpacing(6)

            # Header
            lbl = QtWidgets.QLabel("INPUTS × MIX BUSES MATRIX OVERVIEW")
            lbl.setStyleSheet("font-family: monospace; font-size: 11px; font-weight: bold; color: #4fd6e6;")
            layout.addWidget(lbl)

            # Table Widget
            self.table = QtWidgets.QTableWidget(self.config.num_channels, self.config.num_buses)
            self.table.setVerticalHeaderLabels([f"IN {i + 1:02d}: {self.config.get_channel_name(i)}" for i in range(self.config.num_channels)])
            self.table.setHorizontalHeaderLabels([f"Mix Bus {b + 1}" for b in range(self.config.num_buses)])
            self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
            self.table.verticalHeader().setDefaultSectionSize(32)

            self.table.setStyleSheet("""
                QTableWidget {
                    font-family: monospace;
                    font-size: 10px;
                    background-color: #121316;
                    gridline-color: #1d2025;
                }
            """)

            self._populate_cells()
            layout.addWidget(self.table, stretch=1)

        def _populate_cells(self):
            for ch in range(self.config.num_channels):
                for b in range(self.config.num_buses):
                    cell_widget = QtWidgets.QWidget()
                    cell_layout = QtWidgets.QHBoxLayout(cell_widget)
                    cell_layout.setContentsMargins(4, 2, 4, 2)
                    cell_layout.setSpacing(4)

                    send = self.state.buses[b].sends[ch]

                    # Slider for Level
                    slider = QtWidgets.QSlider(Qt.Orientation.Horizontal)
                    slider.setRange(0, 1000)
                    slider.setValue(int(send.fader_norm * 1000))
                    slider.setStyleSheet("""
                        QSlider::groove:horizontal { height: 4px; background: #23272e; border-radius: 2px; }
                        QSlider::handle:horizontal { background: #afbfc9; width: 10px; margin: -3px 0; border-radius: 2px; }
                    """)
                    slider.valueChanged.connect(self._make_fader_handler(b, ch))
                    cell_layout.addWidget(slider, stretch=2)

                    # dB Label
                    lbl_db = QtWidgets.QLabel(format_db(norm_to_db(send.fader_norm)))
                    lbl_db.setFixedWidth(46)
                    lbl_db.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    lbl_db.setStyleSheet("font-size: 9px; color: #8c939d;")
                    cell_layout.addWidget(lbl_db)

                    # Mute toggle
                    btn_m = QtWidgets.QPushButton("M")
                    btn_m.setCheckable(True)
                    btn_m.setProperty("class", "btn-mute")
                    btn_m.setFixedSize(18, 18)
                    btn_m.setChecked(send.mute)
                    btn_m.toggled.connect(self._make_mute_handler(b, ch))
                    cell_layout.addWidget(btn_m)

                    # Solo toggle
                    btn_s = QtWidgets.QPushButton("S")
                    btn_s.setCheckable(True)
                    btn_s.setProperty("class", "btn-solo")
                    btn_s.setFixedSize(18, 18)
                    btn_s.setChecked(send.solo)
                    btn_s.toggled.connect(self._make_solo_handler(b, ch))
                    cell_layout.addWidget(btn_s)

                    self.table.setCellWidget(ch, b, cell_widget)

        def _make_fader_handler(self, bus: int, ch: int):
            def handler(val: int):
                norm = val / 1000.0
                self.faderChanged.emit(bus, ch, norm)
            return handler

        def _make_mute_handler(self, bus: int, ch: int):
            def handler(checked: bool):
                self.muteChanged.emit(bus, ch, checked)
            return handler

        def _make_solo_handler(self, bus: int, ch: int):
            def handler(checked: bool):
                self.soloChanged.emit(bus, ch, checked)
            return handler

        def refresh_table(self):
            for ch in range(self.config.num_channels):
                for b in range(self.config.num_buses):
                    cell = self.table.cellWidget(ch, b)
                    if cell:
                        send = self.state.buses[b].sends[ch]
                        slider = cell.findChild(QtWidgets.QSlider)
                        if slider:
                            slider.blockSignals(True)
                            slider.setValue(int(send.fader_norm * 1000))
                            slider.blockSignals(False)
                        labels = cell.findChildren(QtWidgets.QLabel)
                        if labels:
                            labels[0].setText(format_db(norm_to_db(send.fader_norm)))
                        buttons = cell.findChildren(QtWidgets.QPushButton)
                        if len(buttons) >= 2:
                            buttons[0].blockSignals(True)
                            buttons[0].setChecked(send.mute)
                            buttons[0].blockSignals(False)
                            buttons[1].blockSignals(True)
                            buttons[1].setChecked(send.solo)
                            buttons[1].blockSignals(False)
