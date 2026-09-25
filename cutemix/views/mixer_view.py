"""
Main Mixer Console View for CuteMix.
Hosts 24 input channel strips in a smooth horizontal scroll area with quick bank selectors,
and a pinned Master Bus Strip on the right.
"""

from typing import Dict, List
from ..qt_compat import QtCore, QtGui, QtWidgets, Signal, Qt, is_qt_available
from ..widgets.channel_strip import ChannelStrip
from ..widgets.master_strip import MasterStrip
from ..model.mixer_state import MixerState
from ..model.config import AppConfig

if is_qt_available():
    class MixerView(QtWidgets.QWidget):
        # Forwarded events to controller
        faderChanged = Signal(int, int, float)  # bus, ch, val
        panChanged = Signal(int, int, float)
        muteChanged = Signal(int, int, bool)
        soloChanged = Signal(int, int, bool)
        trimChanged = Signal(int, float)
        padChanged = Signal(int, bool)
        phaseChanged = Signal(int, bool)
        stereoChanged = Signal(int, bool)
        channelNameChanged = Signal(int, str)
        masterFaderChanged = Signal(int, float)
        masterMuteChanged = Signal(int, bool)
        busChanged = Signal(int)
        clearSolosRequested = Signal()
        resetSendsRequested = Signal(int)

        def __init__(self, mixer_state: MixerState, config: AppConfig, parent=None):
            super().__init__(parent)
            self.state = mixer_state
            self.config = config
            self.strips: Dict[int, ChannelStrip] = {}

            self._build_ui()
            self._connect_signals()

        def _build_ui(self):
            root_layout = QtWidgets.QVBoxLayout(self)
            root_layout.setContentsMargins(6, 6, 6, 6)
            root_layout.setSpacing(4)

            # 1. Bank Navigation Bar
            nav_box = QtWidgets.QHBoxLayout()
            nav_box.setSpacing(6)

            lbl_banks = QtWidgets.QLabel("BANKS:")
            lbl_banks.setStyleSheet("font-family: monospace; font-size: 10px; font-weight: bold; color: #747c87;")
            nav_box.addWidget(lbl_banks)

            self.btn_bank_all = QtWidgets.QPushButton("ALL 24")
            self.btn_bank_1 = QtWidgets.QPushButton("CH 01-08")
            self.btn_bank_2 = QtWidgets.QPushButton("CH 09-16")
            self.btn_bank_3 = QtWidgets.QPushButton("CH 17-24")

            for btn in (self.btn_bank_all, self.btn_bank_1, self.btn_bank_2, self.btn_bank_3):
                btn.setFixedHeight(22)
                btn.setCheckable(True)
                nav_box.addWidget(btn)

            self.btn_bank_all.setChecked(True)

            nav_box.addStretch()

            self.lbl_bus_indicator = QtWidgets.QLabel(f"Active: Mix {self.state.active_bus_idx + 1}")
            self.lbl_bus_indicator.setStyleSheet("font-family: monospace; font-size: 11px; font-weight: bold; color: #4fd6e6;")
            nav_box.addWidget(self.lbl_bus_indicator)

            root_layout.addLayout(nav_box)

            # 2. Main Console Layout: Scrollable Channels + Pinned Master
            console_box = QtWidgets.QHBoxLayout()
            console_box.setSpacing(4)

            # Scroll Area for Channel Strips
            self.scroll_area = QtWidgets.QScrollArea()
            self.scroll_area.setWidgetResizable(True)
            self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.scroll_area.setStyleSheet("""
                QScrollArea {
                    background-color: #141518;
                    border: 1px solid #1c1e22;
                    border-radius: 2px;
                }
            """)

            # Container widget inside scroll area
            self.strips_container = QtWidgets.QWidget()
            self.strips_layout = QtWidgets.QHBoxLayout(self.strips_container)
            self.strips_layout.setContentsMargins(4, 4, 4, 4)
            self.strips_layout.setSpacing(3)
            self.strips_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

            # Build 24 Channel Strips
            active_bus = self.state.get_active_bus()
            for ch in range(self.config.num_channels):
                name = self.config.get_channel_name(ch)
                strip = ChannelStrip(ch, initial_name=name)

                # Initialize values from state
                inp = self.state.get_input(ch)
                send = active_bus.sends[ch]

                strip.setFaderSilent(send.fader_norm)
                strip.setPanSilent(send.pan_norm)
                strip.setMuteSilent(send.mute)
                strip.setSoloSilent(send.solo)
                strip.setGangSilent(send.gang)
                strip.setTrimSilent(inp.trim_norm)
                strip.setPadSilent(inp.pad)
                strip.setPhaseSilent(inp.phase)
                strip.setStereoSilent(inp.stereo_link)

                self.strips[ch] = strip
                self.strips_layout.addWidget(strip)

            self.scroll_area.setWidget(self.strips_container)
            console_box.addWidget(self.scroll_area, stretch=1)

            # Pinned Master Strip on Right
            self.master_strip = MasterStrip(num_buses=self.config.num_buses, initial_bus=self.state.active_bus_idx)
            self.master_strip.setMasterFaderSilent(active_bus.master_fader_norm)
            self.master_strip.setMasterMuteSilent(active_bus.master_mute)
            console_box.addWidget(self.master_strip)

            root_layout.addLayout(console_box, stretch=1)

        def _connect_signals(self):
            # Bank selectors
            self.btn_bank_all.clicked.connect(lambda: self._select_bank(0, 24, self.btn_bank_all))
            self.btn_bank_1.clicked.connect(lambda: self._select_bank(0, 8, self.btn_bank_1))
            self.btn_bank_2.clicked.connect(lambda: self._select_bank(8, 16, self.btn_bank_2))
            self.btn_bank_3.clicked.connect(lambda: self._select_bank(16, 24, self.btn_bank_3))

            # Channel strip signals
            for ch, strip in self.strips.items():
                strip.faderChanged.connect(lambda c, v: self.faderChanged.emit(self.state.active_bus_idx, c, v))
                strip.panChanged.connect(lambda c, v: self.panChanged.emit(self.state.active_bus_idx, c, v))
                strip.muteChanged.connect(lambda c, b: self.muteChanged.emit(self.state.active_bus_idx, c, b))
                strip.soloChanged.connect(lambda c, b: self.soloChanged.emit(self.state.active_bus_idx, c, b))
                strip.trimChanged.connect(self.trimChanged.emit)
                strip.padChanged.connect(self.padChanged.emit)
                strip.phaseChanged.connect(self.phaseChanged.emit)
                strip.stereoChanged.connect(self.stereoChanged.emit)
                strip.nameChanged.connect(self.channelNameChanged.emit)

            # Master strip signals
            self.master_strip.busChanged.connect(self._on_bus_changed)
            self.master_strip.masterFaderChanged.connect(self.masterFaderChanged.emit)
            self.master_strip.masterMuteChanged.connect(self.masterMuteChanged.emit)
            self.master_strip.clearSolosRequested.connect(self.clearSolosRequested.emit)
            self.master_strip.resetSendsRequested.connect(self.resetSendsRequested.emit)

        def _select_bank(self, start_ch: int, end_ch: int, active_btn: QtWidgets.QPushButton):
            for btn in (self.btn_bank_all, self.btn_bank_1, self.btn_bank_2, self.btn_bank_3):
                btn.setChecked(btn == active_btn)

            if start_ch == 0 and end_ch == 24:
                # Show all
                for strip in self.strips.values():
                    strip.setVisible(True)
            else:
                for ch, strip in self.strips.items():
                    strip.setVisible(start_ch <= ch < end_ch)

        def _on_bus_changed(self, bus_idx: int):
            self.state.active_bus_idx = bus_idx
            self.lbl_bus_indicator.setText(f"Active: Mix {bus_idx + 1}")
            self.refresh_bus_view(bus_idx)
            self.busChanged.emit(bus_idx)

        def refresh_bus_view(self, bus_idx: int):
            """Refreshes all faders, pans, mutes, and solos for the newly selected mix bus."""
            bus = self.state.buses[bus_idx]
            for ch, strip in self.strips.items():
                send = bus.sends[ch]
                strip.setFaderSilent(send.fader_norm)
                strip.setPanSilent(send.pan_norm)
                strip.setMuteSilent(send.mute)
                strip.setSoloSilent(send.solo)
                strip.setGangSilent(send.gang)

            self.master_strip.setBusIndex(bus_idx)
            self.master_strip.setMasterFaderSilent(bus.master_fader_norm)
            self.master_strip.setMasterMuteSilent(bus.master_mute)
            self.update_solo_alert()

        def update_solo_alert(self):
            any_solo = self.state.is_any_solo_active(self.state.active_bus_idx)
            self.master_strip.setSoloActive(any_solo)
