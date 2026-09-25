"""
Input Channel Strip Widget for CuteMix.
Integrates Preamp Conditioning (Trim, Pad, Phase, Stereo Link), Matrix Send (Pan, Mute, Solo, Gang),
Long-throw Fader, LED Ladder Meter, and Editable Name Header.
"""

from ..qt_compat import QtCore, QtGui, QtWidgets, Signal, Qt, is_qt_available
from .fader import StudioFader
from .rotary_knob import RotaryKnob
from .led_meter import LedLadderMeter
from ..osc.cuemix_protocol import format_db

if is_qt_available():
    class ChannelStrip(QtWidgets.QFrame):
        """
        Complete hardware-styled channel strip for one 24i input channel.
        """
        faderChanged = Signal(int, float)
        panChanged = Signal(int, float)
        muteChanged = Signal(int, bool)
        soloChanged = Signal(int, bool)
        gangChanged = Signal(int, bool)
        trimChanged = Signal(int, float)
        padChanged = Signal(int, bool)
        phaseChanged = Signal(int, bool)
        stereoChanged = Signal(int, bool)
        nameChanged = Signal(int, str)

        def __init__(self, channel_idx: int, initial_name: str = "", parent=None):
            super().__init__(parent)
            self.channel_idx = channel_idx
            self.channel_name = initial_name or f"Analog {channel_idx + 1}"

            self.setFixedWidth(86)
            self.setObjectName("channelStrip")
            self.setStyleSheet("""
                QFrame#channelStrip {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #22252a, stop:1 #191a1d);
                    border: 1px solid #101114;
                    border-right: 1px solid #0b0c0d;
                    border-radius: 2px;
                }
            """)

            self._build_ui()
            self._connect_signals()

        def _build_ui(self):
            layout = QtWidgets.QVBoxLayout(self)
            layout.setContentsMargins(3, 4, 3, 4)
            layout.setSpacing(3)

            # 1. Header: Channel Number & Editable Label
            self.lbl_ch_num = QtWidgets.QLabel(f"IN {self.channel_idx + 1:02d}")
            self.lbl_ch_num.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.lbl_ch_num.setStyleSheet("font-family: monospace; font-size: 9px; font-weight: bold; color: #858d99;")
            layout.addWidget(self.lbl_ch_num)

            self.edit_name = QtWidgets.QLineEdit(self.channel_name)
            self.edit_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.edit_name.setFixedHeight(18)
            self.edit_name.setStyleSheet("""
                QLineEdit {
                    background-color: #121316;
                    border: 1px solid #23272e;
                    border-radius: 2px;
                    color: #4fd6e6;
                    font-size: 9px;
                    font-weight: bold;
                    padding: 0px 2px;
                }
                QLineEdit:focus {
                    border: 1px solid #2ec4d6;
                    background-color: #16181d;
                }
            """)
            layout.addWidget(self.edit_name)

            # Separator line
            sep1 = QtWidgets.QFrame()
            sep1.setFrameShape(QtWidgets.QFrame.Shape.HLine)
            sep1.setStyleSheet("background-color: #0f1013; max-height: 1px;")
            layout.addWidget(sep1)

            # 2. Preamp Conditioning: Trim knob & Switches
            trim_box = QtWidgets.QHBoxLayout()
            trim_box.setSpacing(2)
            trim_box.setContentsMargins(0, 0, 0, 0)

            self.knob_trim = RotaryKnob(mode="trim", default_val=0.0)
            trim_box.addWidget(self.knob_trim)

            switches_layout = QtWidgets.QVBoxLayout()
            switches_layout.setSpacing(2)

            self.btn_pad = QtWidgets.QPushButton("-20")
            self.btn_pad.setCheckable(True)
            self.btn_pad.setProperty("class", "btn-pad")
            self.btn_pad.setFixedSize(28, 14)
            self.btn_pad.setToolTip("Pad (-20 dB)")

            self.btn_phase = QtWidgets.QPushButton("Ø")
            self.btn_phase.setCheckable(True)
            self.btn_phase.setProperty("class", "btn-phase")
            self.btn_phase.setFixedSize(28, 14)
            self.btn_phase.setToolTip("Phase Invert")

            self.btn_link = QtWidgets.QPushButton("ST")
            self.btn_link.setCheckable(True)
            self.btn_link.setProperty("class", "btn-link")
            self.btn_link.setFixedSize(28, 14)
            self.btn_link.setToolTip("Stereo Link with Pair")

            switches_layout.addWidget(self.btn_pad)
            switches_layout.addWidget(self.btn_phase)
            switches_layout.addWidget(self.btn_link)
            trim_box.addLayout(switches_layout)
            layout.addLayout(trim_box)

            # Separator line
            sep2 = QtWidgets.QFrame()
            sep2.setFrameShape(QtWidgets.QFrame.Shape.HLine)
            sep2.setStyleSheet("background-color: #0f1013; max-height: 1px;")
            layout.addWidget(sep2)

            # 3. Pan Potentiometer
            pan_box = QtWidgets.QHBoxLayout()
            pan_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.knob_pan = RotaryKnob(mode="pan", default_val=0.5)
            pan_box.addWidget(self.knob_pan)
            layout.addLayout(pan_box)

            # 4. Mute / Solo / Gang Button Row
            btn_row = QtWidgets.QHBoxLayout()
            btn_row.setSpacing(2)
            btn_row.setContentsMargins(1, 0, 1, 0)

            self.btn_mute = QtWidgets.QPushButton("M")
            self.btn_mute.setCheckable(True)
            self.btn_mute.setProperty("class", "btn-mute")
            self.btn_mute.setFixedSize(24, 18)
            self.btn_mute.setToolTip("Mute Channel")

            self.btn_solo = QtWidgets.QPushButton("S")
            self.btn_solo.setCheckable(True)
            self.btn_solo.setProperty("class", "btn-solo")
            self.btn_solo.setFixedSize(24, 18)
            self.btn_solo.setToolTip("Solo Channel (PFL)")

            self.btn_gang = QtWidgets.QPushButton("G")
            self.btn_gang.setCheckable(True)
            self.btn_gang.setProperty("class", "btn-gang")
            self.btn_gang.setFixedSize(24, 18)
            self.btn_gang.setToolTip("Gang Group (faders move together)")

            btn_row.addWidget(self.btn_mute)
            btn_row.addWidget(self.btn_solo)
            btn_row.addWidget(self.btn_gang)
            layout.addLayout(btn_row)

            # 5. Fader + Meter Area
            fader_meter_box = QtWidgets.QHBoxLayout()
            fader_meter_box.setSpacing(1)
            fader_meter_box.setContentsMargins(0, 2, 0, 2)

            self.fader = StudioFader(is_master=False)
            self.meter = LedLadderMeter(is_stereo=False)

            fader_meter_box.addWidget(self.fader, stretch=1)
            fader_meter_box.addWidget(self.meter)
            layout.addLayout(fader_meter_box, stretch=1)

            # 6. Bottom dB Badge
            self.lbl_db = QtWidgets.QLabel("0.0 dB")
            self.lbl_db.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.lbl_db.setStyleSheet("""
                QLabel {
                    font-family: monospace;
                    font-size: 10px;
                    color: #d8dee8;
                    background-color: #121316;
                    border: 1px solid #23272e;
                    border-radius: 2px;
                    padding: 2px 0px;
                }
            """)
            layout.addWidget(self.lbl_db)

        def _connect_signals(self):
            self.edit_name.editingFinished.connect(self._on_name_edited)
            self.knob_trim.valueChanged.connect(lambda v: self.trimChanged.emit(self.channel_idx, v))
            self.btn_pad.toggled.connect(lambda b: self.padChanged.emit(self.channel_idx, b))
            self.btn_phase.toggled.connect(lambda b: self.phaseChanged.emit(self.channel_idx, b))
            self.btn_link.toggled.connect(lambda b: self.stereoChanged.emit(self.channel_idx, b))

            self.knob_pan.valueChanged.connect(lambda v: self.panChanged.emit(self.channel_idx, v))
            self.btn_mute.toggled.connect(self._on_mute_toggled)
            self.btn_solo.toggled.connect(lambda b: self.soloChanged.emit(self.channel_idx, b))
            self.btn_gang.toggled.connect(lambda b: self.gangChanged.emit(self.channel_idx, b))

            self.fader.valueChanged.connect(self._on_fader_changed)
            self.fader.sliderMoved.connect(self._update_db_label)

        def _on_name_edited(self):
            txt = self.edit_name.text().strip() or f"Analog {self.channel_idx + 1}"
            self.channel_name = txt
            self.nameChanged.emit(self.channel_idx, txt)

        def _on_fader_changed(self, val: float):
            self._update_db_label(val)
            self.faderChanged.emit(self.channel_idx, val)

        def _update_db_label(self, val: float):
            db = self.fader.db_value()
            self.lbl_db.setText(format_db(db))

        def _on_mute_toggled(self, checked: bool):
            self.fader.setMuted(checked)
            self.muteChanged.emit(self.channel_idx, checked)

        # ----------------- Silent Updates from OSC -----------------

        def setFaderSilent(self, norm_val: float):
            self.fader.setValueSilent(norm_val)
            self._update_db_label(norm_val)

        def setPanSilent(self, norm_val: float):
            self.knob_pan.setValueSilent(norm_val)

        def setMuteSilent(self, muted: bool):
            self.btn_mute.blockSignals(True)
            self.btn_mute.setChecked(muted)
            self.fader.setMuted(muted)
            self.btn_mute.blockSignals(False)

        def setSoloSilent(self, soloed: bool):
            self.btn_solo.blockSignals(True)
            self.btn_solo.setChecked(soloed)
            self.btn_solo.blockSignals(False)

        def setGangSilent(self, ganged: bool):
            self.btn_gang.blockSignals(True)
            self.btn_gang.setChecked(ganged)
            self.btn_gang.blockSignals(False)

        def setTrimSilent(self, norm_val: float):
            self.knob_trim.setValueSilent(norm_val)

        def setPadSilent(self, enabled: bool):
            self.btn_pad.blockSignals(True)
            self.btn_pad.setChecked(enabled)
            self.btn_pad.blockSignals(False)

        def setPhaseSilent(self, enabled: bool):
            self.btn_phase.blockSignals(True)
            self.btn_phase.setChecked(enabled)
            self.btn_phase.blockSignals(False)

        def setStereoSilent(self, enabled: bool):
            self.btn_link.blockSignals(True)
            self.btn_link.setChecked(enabled)
            self.btn_link.blockSignals(False)

        def setMeterLevel(self, level: float):
            self.meter.setLevel(level)

        def decayMeter(self, dt: float):
            self.meter.decay(dt)
