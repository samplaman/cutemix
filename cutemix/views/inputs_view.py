"""
Analog Preamp & Conditioning Rack View for CuteMix.
Focuses on the 24 analog inputs of the MOTU 24i interface:
Trim Gain, -20 dB Pad, Polarity Invert, Stereo Pairing, Input Mute, and Metering.
"""

from typing import Dict
from ..qt_compat import QtCore, QtGui, QtWidgets, Signal, Qt, is_qt_available
from ..widgets.rotary_knob import RotaryKnob
from ..widgets.led_meter import LedLadderMeter
from ..model.mixer_state import MixerState
from ..model.config import AppConfig

if is_qt_available():
    class SingleInputPreampCard(QtWidgets.QFrame):
        trimChanged = Signal(int, float)
        padChanged = Signal(int, bool)
        phaseChanged = Signal(int, bool)
        stereoChanged = Signal(int, bool)
        muteChanged = Signal(int, bool)

        def __init__(self, ch: int, name: str, parent=None):
            super().__init__(parent)
            self.ch = ch
            self.name = name

            self.setFixedWidth(68)
            self.setObjectName("preampCard")
            self.setStyleSheet("""
                QFrame#preampCard {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #22262c, stop:1 #181a1e);
                    border: 1px solid #101215;
                    border-radius: 3px;
                }
            """)
            self._build_ui()

        def _build_ui(self):
            layout = QtWidgets.QVBoxLayout(self)
            layout.setContentsMargins(4, 5, 4, 5)
            layout.setSpacing(4)

            # Header
            lbl_num = QtWidgets.QLabel(f"IN {self.ch + 1:02d}")
            lbl_num.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_num.setStyleSheet("font-family: monospace; font-size: 10px; font-weight: bold; color: #4fd6e6;")
            layout.addWidget(lbl_num)

            self.lbl_name = QtWidgets.QLabel(self.name)
            self.lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.lbl_name.setStyleSheet("font-size: 8px; color: #88909c;")
            layout.addWidget(self.lbl_name)

            # Trim Knob
            self.knob_trim = RotaryKnob(mode="trim", default_val=0.0)
            self.knob_trim.valueChanged.connect(lambda v: self.trimChanged.emit(self.ch, v))
            layout.addWidget(self.knob_trim, alignment=Qt.AlignmentFlag.AlignCenter)

            # Switches
            self.btn_pad = QtWidgets.QPushButton("-20")
            self.btn_pad.setCheckable(True)
            self.btn_pad.setProperty("class", "btn-pad")
            self.btn_pad.setFixedHeight(16)
            self.btn_pad.toggled.connect(lambda b: self.padChanged.emit(self.ch, b))
            layout.addWidget(self.btn_pad)

            self.btn_phase = QtWidgets.QPushButton("Ø")
            self.btn_phase.setCheckable(True)
            self.btn_phase.setProperty("class", "btn-phase")
            self.btn_phase.setFixedHeight(16)
            self.btn_phase.toggled.connect(lambda b: self.phaseChanged.emit(self.ch, b))
            layout.addWidget(self.btn_phase)

            self.btn_st = QtWidgets.QPushButton("ST")
            self.btn_st.setCheckable(True)
            self.btn_st.setProperty("class", "btn-link")
            self.btn_st.setFixedHeight(16)
            self.btn_st.toggled.connect(lambda b: self.stereoChanged.emit(self.ch, b))
            layout.addWidget(self.btn_st)

            self.btn_mute = QtWidgets.QPushButton("MUTE")
            self.btn_mute.setCheckable(True)
            self.btn_mute.setProperty("class", "btn-mute")
            self.btn_mute.setFixedHeight(16)
            self.btn_mute.toggled.connect(lambda b: self.muteChanged.emit(self.ch, b))
            layout.addWidget(self.btn_mute)

            # Meter
            self.meter = LedLadderMeter(is_stereo=False)
            layout.addWidget(self.meter, stretch=1, alignment=Qt.AlignmentFlag.AlignCenter)


    class InputsPreampView(QtWidgets.QWidget):
        trimChanged = Signal(int, float)
        padChanged = Signal(int, bool)
        phaseChanged = Signal(int, bool)
        stereoChanged = Signal(int, bool)
        muteChanged = Signal(int, bool)

        def __init__(self, mixer_state: MixerState, config: AppConfig, parent=None):
            super().__init__(parent)
            self.state = mixer_state
            self.config = config
            self.cards: Dict[int, SingleInputPreampCard] = {}

            self._build_ui()

        def _build_ui(self):
            root_layout = QtWidgets.QVBoxLayout(self)
            root_layout.setContentsMargins(8, 8, 8, 8)
            root_layout.setSpacing(6)

            # Top Toolbar
            tb = QtWidgets.QHBoxLayout()
            lbl = QtWidgets.QLabel("24I ANALOG FRONT-END PREAMP & CONDITIONING RACK")
            lbl.setStyleSheet("font-family: monospace; font-size: 11px; font-weight: bold; color: #4fd6e6;")
            tb.addWidget(lbl)
            tb.addStretch()

            btn_zero_trims = QtWidgets.QPushButton("Zero All Trims")
            btn_zero_trims.clicked.connect(self._zero_all_trims)
            tb.addWidget(btn_zero_trims)

            btn_clear_mutes = QtWidgets.QPushButton("Unmute All Inputs")
            btn_clear_mutes.clicked.connect(self._unmute_all)
            tb.addWidget(btn_clear_mutes)

            root_layout.addLayout(tb)

            # Scroll Area
            scroll = QtWidgets.QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setStyleSheet("background-color: #141518; border: 1px solid #1c1e22;")

            container = QtWidgets.QWidget()
            layout = QtWidgets.QHBoxLayout(container)
            layout.setContentsMargins(4, 4, 4, 4)
            layout.setSpacing(4)
            layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

            for ch in range(self.config.num_channels):
                name = self.config.get_channel_name(ch)
                card = SingleInputPreampCard(ch, name)

                inp = self.state.get_input(ch)
                card.knob_trim.setValueSilent(inp.trim_norm)
                card.btn_pad.setChecked(inp.pad)
                card.btn_phase.setChecked(inp.phase)
                card.btn_st.setChecked(inp.stereo_link)
                card.btn_mute.setChecked(inp.input_mute)

                card.trimChanged.connect(self.trimChanged.emit)
                card.padChanged.connect(self.padChanged.emit)
                card.phaseChanged.connect(self.phaseChanged.emit)
                card.stereoChanged.connect(self.stereoChanged.emit)
                card.muteChanged.connect(self.muteChanged.emit)

                self.cards[ch] = card
                layout.addWidget(card)

            scroll.setWidget(container)
            root_layout.addWidget(scroll, stretch=1)

        def _zero_all_trims(self):
            for ch in range(self.config.num_channels):
                self.cards[ch].knob_trim.setValue(0.0)

        def _unmute_all(self):
            for ch in range(self.config.num_channels):
                self.cards[ch].btn_mute.setChecked(False)

        def sync_input_state(self, ch: int):
            if ch in self.cards:
                inp = self.state.get_input(ch)
                card = self.cards[ch]
                card.knob_trim.setValueSilent(inp.trim_norm)
                card.btn_pad.setChecked(inp.pad)
                card.btn_phase.setChecked(inp.phase)
                card.btn_st.setChecked(inp.stereo_link)
                card.btn_mute.setChecked(inp.input_mute)
