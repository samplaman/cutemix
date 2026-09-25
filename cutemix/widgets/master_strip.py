"""
Master Output Strip Widget for CuteMix.
Houses Mix Bus Selection, Global Solo Indicator/Clear, Master Fader,
Dual L/R Peak Meters, Master Mute, Reset Sends (RST), and Studio Talkback/Listenback.
"""

from ..qt_compat import QtCore, QtGui, QtWidgets, Signal, Qt, is_qt_available
from .fader import StudioFader
from .led_meter import LedLadderMeter
from .rotary_knob import RotaryKnob
from ..osc.cuemix_protocol import format_db

if is_qt_available():
    class MasterStrip(QtWidgets.QFrame):
        busChanged = Signal(int)
        masterFaderChanged = Signal(int, float)
        masterMuteChanged = Signal(int, bool)
        clearSolosRequested = Signal()
        resetSendsRequested = Signal(int)
        talkbackToggled = Signal(bool)
        listenbackToggled = Signal(bool)
        attenChanged = Signal(float)

        def __init__(self, num_buses: int = 4, initial_bus: int = 0, parent=None):
            super().__init__(parent)
            self.num_buses = num_buses
            self.active_bus_idx = initial_bus

            self.setFixedWidth(112)
            self.setObjectName("masterStrip")
            self.setStyleSheet("""
                QFrame#masterStrip {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1e2a2e, stop:1 #151d20);
                    border: 1px solid #163f45;
                    border-left: 2px solid #2ec4d6;
                    border-radius: 2px;
                }
            """)

            self._build_ui()
            self._connect_signals()

        def _build_ui(self):
            layout = QtWidgets.QVBoxLayout(self)
            layout.setContentsMargins(4, 5, 4, 5)
            layout.setSpacing(4)

            # 1. Header Label
            self.lbl_title = QtWidgets.QLabel("MASTER BUS")
            self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.lbl_title.setStyleSheet("""
                font-family: monospace;
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 1px;
                color: #4fd6e6;
                padding-bottom: 2px;
            """)
            layout.addWidget(self.lbl_title)

            # 2. Mix Bus Selector
            self.cmb_bus = QtWidgets.QComboBox()
            for b in range(self.num_buses):
                self.cmb_bus.addItem(f"Mix {b + 1}")
            self.cmb_bus.setCurrentIndex(self.active_bus_idx)
            self.cmb_bus.setStyleSheet("""
                QComboBox {
                    background-color: #121f22;
                    border: 1px solid #1e4e56;
                    color: #4fd6e6;
                    font-weight: bold;
                    font-size: 10px;
                    padding: 3px 6px;
                }
            """)
            layout.addWidget(self.cmb_bus)

            # 3. Global Solo Alert / Clear Button
            self.btn_solo_clear = QtWidgets.QPushButton("SOLO ACTIVE")
            self.btn_solo_clear.setToolTip("Click to clear all active solos across the console")
            self.btn_solo_clear.setCheckable(False)
            self.btn_solo_clear.setFixedHeight(20)
            self.btn_solo_clear.setStyleSheet("""
                QPushButton {
                    font-family: monospace;
                    font-size: 9px;
                    font-weight: bold;
                    color: #555b63;
                    background-color: #1c2024;
                    border: 1px solid #2a2e36;
                    border-radius: 2px;
                }
            """)
            layout.addWidget(self.btn_solo_clear)

            # 4. Quick Action Buttons: RST (Reset Sends)
            action_row = QtWidgets.QHBoxLayout()
            action_row.setSpacing(2)

            self.btn_rst = QtWidgets.QPushButton("RST")
            self.btn_rst.setToolTip("Reset all channel sends in this mix to Unity & Center")
            self.btn_rst.setFixedHeight(18)
            self.btn_rst.setStyleSheet("font-size: 9px; font-weight: bold; color: #a4abb5;")
            action_row.addWidget(self.btn_rst)

            self.btn_mute = QtWidgets.QPushButton("MUTE")
            self.btn_mute.setCheckable(True)
            self.btn_mute.setProperty("class", "btn-mute")
            self.btn_mute.setFixedHeight(18)
            self.btn_mute.setToolTip("Mute Master Output")
            action_row.addWidget(self.btn_mute)

            layout.addLayout(action_row)

            # Separator
            sep = QtWidgets.QFrame()
            sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
            sep.setStyleSheet("background-color: #163f45; max-height: 1px;")
            layout.addWidget(sep)

            # 5. Studio Talkback / Listen / Atten
            talk_box = QtWidgets.QHBoxLayout()
            talk_box.setSpacing(2)

            self.btn_talk = QtWidgets.QPushButton("TALK")
            self.btn_talk.setCheckable(True)
            self.btn_talk.setFixedSize(30, 16)
            self.btn_talk.setStyleSheet("""
                QPushButton { font-size: 8px; font-weight: bold; color: #88909c; }
                QPushButton:checked { background-color: #d94b36; color: #ffffff; }
            """)
            self.btn_talk.setToolTip("Talkback into mixes")

            self.btn_listen = QtWidgets.QPushButton("LSTN")
            self.btn_listen.setCheckable(True)
            self.btn_listen.setFixedSize(30, 16)
            self.btn_listen.setStyleSheet("""
                QPushButton { font-size: 8px; font-weight: bold; color: #88909c; }
                QPushButton:checked { background-color: #2ec4d6; color: #10262b; }
            """)
            self.btn_listen.setToolTip("Listenback from studio")

            self.knob_atten = RotaryKnob(mode="trim", default_val=0.2)
            self.knob_atten.setToolTip("Talkback Dim / Atten level")
            self.knob_atten.setFixedSize(32, 40)

            talk_box.addWidget(self.btn_talk)
            talk_box.addWidget(self.btn_listen)
            talk_box.addWidget(self.knob_atten)
            layout.addLayout(talk_box)

            # 6. Master Fader + Stereo L/R Meters
            fader_box = QtWidgets.QHBoxLayout()
            fader_box.setSpacing(2)
            fader_box.setContentsMargins(0, 2, 0, 2)

            self.fader = StudioFader(is_master=True)
            self.meter = LedLadderMeter(is_stereo=True)

            fader_box.addWidget(self.fader, stretch=1)
            fader_box.addWidget(self.meter)
            layout.addLayout(fader_box, stretch=1)

            # 7. Master dB Badge
            self.lbl_db = QtWidgets.QLabel("0.0 dB")
            self.lbl_db.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.lbl_db.setStyleSheet("""
                QLabel {
                    font-family: monospace;
                    font-size: 10px;
                    font-weight: bold;
                    color: #4fd6e6;
                    background-color: #121c1f;
                    border: 1px solid #1c4b52;
                    border-radius: 2px;
                    padding: 2px 0px;
                }
            """)
            layout.addWidget(self.lbl_db)

        def _connect_signals(self):
            self.cmb_bus.currentIndexChanged.connect(self._on_bus_combo_changed)
            self.btn_solo_clear.clicked.connect(self.clearSolosRequested.emit)
            self.btn_rst.clicked.connect(self._on_rst_clicked)
            self.btn_mute.toggled.connect(self._on_mute_toggled)

            self.btn_talk.toggled.connect(self.talkbackToggled.emit)
            self.btn_listen.toggled.connect(self.listenbackToggled.emit)
            self.knob_atten.valueChanged.connect(self.attenChanged.emit)

            self.fader.valueChanged.connect(self._on_fader_changed)
            self.fader.sliderMoved.connect(self._update_db_label)

        def _on_bus_combo_changed(self, idx: int):
            self.active_bus_idx = idx
            self.busChanged.emit(idx)

        def _on_rst_clicked(self):
            ret = QtWidgets.QMessageBox.question(
                self,
                "Reset Sends",
                f"Reset all channel sends in {self.cmb_bus.currentText()} to Unity (0 dB) and Center Pan?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.No
            )
            if ret == QtWidgets.QMessageBox.StandardButton.Yes:
                self.resetSendsRequested.emit(self.active_bus_idx)

        def _on_fader_changed(self, val: float):
            self._update_db_label(val)
            self.masterFaderChanged.emit(self.active_bus_idx, val)

        def _update_db_label(self, val: float):
            db = self.fader.db_value()
            self.lbl_db.setText(format_db(db))

        def _on_mute_toggled(self, checked: bool):
            self.fader.setMuted(checked)
            self.masterMuteChanged.emit(self.active_bus_idx, checked)

        # ----------------- External Updates -----------------

        def setSoloActive(self, active: bool):
            """Lights up the global solo indicator."""
            if active:
                self.btn_solo_clear.setStyleSheet("""
                    QPushButton {
                        font-family: monospace;
                        font-size: 9px;
                        font-weight: bold;
                        color: #1a0f00;
                        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffc04d, stop:1 #e08c19);
                        border: 1px solid #ffa622;
                        border-radius: 2px;
                    }
                """)
            else:
                self.btn_solo_clear.setStyleSheet("""
                    QPushButton {
                        font-family: monospace;
                        font-size: 9px;
                        font-weight: bold;
                        color: #555b63;
                        background-color: #1c2024;
                        border: 1px solid #2a2e36;
                        border-radius: 2px;
                    }
                """)

        def setBusIndex(self, idx: int):
            self.cmb_bus.blockSignals(True)
            self.cmb_bus.setCurrentIndex(idx)
            self.active_bus_idx = idx
            self.cmb_bus.blockSignals(False)

        def setMasterFaderSilent(self, norm_val: float):
            self.fader.setValueSilent(norm_val)
            self._update_db_label(norm_val)

        def setMasterMuteSilent(self, muted: bool):
            self.btn_mute.blockSignals(True)
            self.btn_mute.setChecked(muted)
            self.fader.setMuted(muted)
            self.btn_mute.blockSignals(False)

        def setStereoLevels(self, left: float, right: float):
            self.meter.setStereoLevels(left, right)

        def decayMeter(self, dt: float):
            self.meter.decay(dt)
