"""
Main Window for CuteMix.
Hosts the console views, toolbars, menubars, status bars, and dialogs.
"""

import os
from .qt_compat import QtCore, QtGui, QtWidgets, Qt, is_qt_available
from .model.config import AppConfig
from .model.mixer_state import MixerState
from .controller import CuteMixController
from .views.mixer_view import MixerView
from .views.inputs_view import InputsPreampView
from .views.matrix_view import MatrixView
from .views.settings_dialog import SettingsDialog
from .widgets.osc_monitor import OscMonitorWidget
from .styles.dark_theme import DARK_STYLESHEET

if is_qt_available():
    class CuteMixMainWindow(QtWidgets.QMainWindow):
        def __init__(self, config: AppConfig, parent=None):
            super().__init__(parent)
            self.config = config
            self.state = MixerState(config)
            self.controller = CuteMixController(config, self.state, self)

            self.setWindowTitle("CuteMix - MOTU PCIe-424 + 24i Mixer Console (OSC)")
            self.resize(1300, 780)
            self.setMinimumSize(960, 600)
            self.setStyleSheet(DARK_STYLESHEET)

            self._build_ui()
            self._connect_signals()

            # Start OSC Networking
            self.controller.start()

        def _build_ui(self):
            # 1. Menus
            self._create_menus()

            # 2. ToolBar
            self._create_toolbar()

            # 3. Main Central Tabs
            self.tabs = QtWidgets.QTabWidget()
            self.tabs.setDocumentMode(True)

            self.view_mixer = MixerView(self.state, self.config)
            self.view_inputs = InputsPreampView(self.state, self.config)
            self.view_matrix = MatrixView(self.state, self.config)
            self.view_monitor = OscMonitorWidget()

            self.tabs.addTab(self.view_mixer, "MIX CONSOLE")
            self.tabs.addTab(self.view_inputs, "INPUTS PREAMP RACK")
            self.tabs.addTab(self.view_matrix, "MATRIX OVERVIEW")
            self.tabs.addTab(self.view_monitor, "OSC MONITOR & DIAGNOSTICS")

            self.setCentralWidget(self.tabs)

            # 4. Status Bar
            self.status_bar = QtWidgets.QStatusBar()
            self.setStatusBar(self.status_bar)

            self.lbl_status_net = QtWidgets.QLabel("OSC: Initializing...")
            self.lbl_status_net.setStyleSheet("font-family: monospace; font-size: 10px; color: #4fd6e6; padding: 0 8px;")
            self.status_bar.addPermanentWidget(self.lbl_status_net)

            self.lbl_status_hw = QtWidgets.QLabel(f"Hardware: PCIe-424 | {self.config.interface_model} (Slot {self.config.slot_letter})")
            self.lbl_status_hw.setStyleSheet("font-family: monospace; font-size: 10px; color: #8c939d; padding: 0 8px;")
            self.status_bar.addPermanentWidget(self.lbl_status_hw)

        def _create_menus(self):
            mb = self.menuBar()

            # File Menu
            m_file = mb.addMenu("&File")

            act_new = m_file.addAction("&Reset to Unity Defaults")
            act_new.setShortcut("Ctrl+N")
            act_new.triggered.connect(self._reset_mixer_defaults)

            m_file.addSeparator()

            act_open = m_file.addAction("&Load Snapshot...")
            act_open.setShortcut("Ctrl+O")
            act_open.triggered.connect(self._open_snapshot_dialog)

            act_save = m_file.addAction("&Save Snapshot...")
            act_save.setShortcut("Ctrl+S")
            act_save.triggered.connect(self._save_snapshot_dialog)

            m_file.addSeparator()

            act_prefs = m_file.addAction("&Preferences & OSC Settings...")
            act_prefs.setShortcut("Ctrl+,")
            act_prefs.triggered.connect(self._open_settings_dialog)

            m_file.addSeparator()

            act_exit = m_file.addAction("E&xit")
            act_exit.setShortcut("Ctrl+Q")
            act_exit.triggered.connect(self.close)

            # Edit Menu
            m_edit = mb.addMenu("&Edit")

            self.act_undo = m_edit.addAction("&Undo")
            self.act_undo.setShortcut("Ctrl+Z")
            self.act_undo.triggered.connect(self._on_undo)

            self.act_redo = m_edit.addAction("&Redo")
            self.act_redo.setShortcut("Ctrl+Y")
            self.act_redo.triggered.connect(self._on_redo)

            m_edit.addSeparator()

            act_clear_solos = m_edit.addAction("&Clear All Solos")
            act_clear_solos.setShortcut("Esc")
            act_clear_solos.triggered.connect(self.controller.clear_all_solos)

            act_reset_sends = m_edit.addAction("Reset Current &Mix Sends")
            act_reset_sends.setShortcut("Ctrl+R")
            act_reset_sends.triggered.connect(lambda: self.controller.reset_bus_sends(self.state.active_bus_idx))

            # View Menu
            m_view = mb.addMenu("&View")
            act_v1 = m_view.addAction("Mix &Console")
            act_v1.setShortcut("Alt+1")
            act_v1.triggered.connect(lambda: self.tabs.setCurrentIndex(0))

            act_v2 = m_view.addAction("&Inputs Preamp Rack")
            act_v2.setShortcut("Alt+2")
            act_v2.triggered.connect(lambda: self.tabs.setCurrentIndex(1))

            act_v3 = m_view.addAction("&Matrix Overview")
            act_v3.setShortcut("Alt+3")
            act_v3.triggered.connect(lambda: self.tabs.setCurrentIndex(2))

            act_v4 = m_view.addAction("&OSC Monitor & Diagnostics")
            act_v4.setShortcut("Alt+4")
            act_v4.triggered.connect(lambda: self.tabs.setCurrentIndex(3))

            # Help Menu
            m_help = mb.addMenu("&Help")
            act_doc = m_help.addAction("MOTU CueMix FX OSC Setup Guide")
            act_doc.triggered.connect(self._show_help_dialog)

            act_about = m_help.addAction("&About CuteMix")
            act_about.triggered.connect(self._show_about_dialog)

        def _create_toolbar(self):
            tb = self.addToolBar("Main Controls")
            tb.setMovable(False)

            # Snapshots
            btn_load = QtWidgets.QToolButton()
            btn_load.setText("Load Snapshot")
            btn_load.clicked.connect(self._open_snapshot_dialog)
            tb.addWidget(btn_load)

            btn_save = QtWidgets.QToolButton()
            btn_save.setText("Save Snapshot")
            btn_save.clicked.connect(self._save_snapshot_dialog)
            tb.addWidget(btn_save)

            tb.addSeparator()

            # Undo / Redo
            self.tb_undo = QtWidgets.QToolButton()
            self.tb_undo.setText("Undo")
            self.tb_undo.clicked.connect(self._on_undo)
            tb.addWidget(self.tb_undo)

            self.tb_redo = QtWidgets.QToolButton()
            self.tb_redo.setText("Redo")
            self.tb_redo.clicked.connect(self._on_redo)
            tb.addWidget(self.tb_redo)

            tb.addSeparator()

            # Panic Mute Button
            self.btn_panic_mute = QtWidgets.QPushButton("PANIC MUTE ALL")
            self.btn_panic_mute.setToolTip("Immediately mute master outputs on all mix buses")
            self.btn_panic_mute.setStyleSheet("""
                QPushButton {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #a82e24, stop:1 #6b1912);
                    color: #ffffff;
                    font-weight: bold;
                    border: 1px solid #d43b2f;
                    padding: 4px 10px;
                }
                QPushButton:hover {
                    background-color: #d43b2f;
                }
            """)
            self.btn_panic_mute.clicked.connect(self._on_panic_mute)
            tb.addWidget(self.btn_panic_mute)

            tb.addSeparator()

            # Settings
            btn_prefs = QtWidgets.QToolButton()
            btn_prefs.setText("OSC Preferences")
            btn_prefs.clicked.connect(self._open_settings_dialog)
            tb.addWidget(btn_prefs)

        def _connect_signals(self):
            # MixerView -> Controller
            self.view_mixer.faderChanged.connect(self.controller.on_fader_changed)
            self.view_mixer.panChanged.connect(self.controller.on_pan_changed)
            self.view_mixer.muteChanged.connect(self.controller.on_mute_changed)
            self.view_mixer.soloChanged.connect(self.controller.on_solo_changed)
            self.view_mixer.trimChanged.connect(self.controller.on_trim_changed)
            self.view_mixer.padChanged.connect(self.controller.on_pad_changed)
            self.view_mixer.phaseChanged.connect(self.controller.on_phase_changed)
            self.view_mixer.stereoChanged.connect(self.controller.on_stereo_changed)
            self.view_mixer.masterFaderChanged.connect(self.controller.on_master_fader_changed)
            self.view_mixer.masterMuteChanged.connect(self.controller.on_master_mute_changed)
            self.view_mixer.clearSolosRequested.connect(self.controller.clear_all_solos)
            self.view_mixer.resetSendsRequested.connect(self.controller.reset_bus_sends)
            self.view_mixer.channelNameChanged.connect(self._on_channel_renamed)

            # InputsPreampView -> Controller
            self.view_inputs.trimChanged.connect(self.controller.on_trim_changed)
            self.view_inputs.padChanged.connect(self.controller.on_pad_changed)
            self.view_inputs.phaseChanged.connect(self.controller.on_phase_changed)
            self.view_inputs.stereoChanged.connect(self.controller.on_stereo_changed)
            self.view_inputs.muteChanged.connect(self._on_input_mute_changed)

            # MatrixView -> Controller
            self.view_matrix.faderChanged.connect(self.controller.on_fader_changed)
            self.view_matrix.panChanged.connect(self.controller.on_pan_changed)
            self.view_matrix.muteChanged.connect(self.controller.on_mute_changed)
            self.view_matrix.soloChanged.connect(self.controller.on_solo_changed)

            # Controller -> UI Updates
            self.controller.stateUpdated.connect(self._on_state_updated)
            self.controller.oscStatsUpdated.connect(self._on_osc_stats_updated)
            self.controller.oscPacketLogged.connect(self.view_monitor.append_entry)
            self.controller.statusMessage.connect(self.status_bar.showMessage)

            # Monitor -> Controller
            self.view_monitor.manualSendRequested.connect(self.controller.send_manual_osc)

            # Tabs changed: sync matrix or mixer
            self.tabs.currentChanged.connect(self._on_tab_changed)

        # ----------------- UI Event Handlers -----------------

        def _on_state_updated(self, target: str, payload: object):
            if target == "fader":
                bus, ch, val = payload
                if bus == self.state.active_bus_idx and ch in self.view_mixer.strips:
                    self.view_mixer.strips[ch].setFaderSilent(val)
            elif target == "fader_silent":
                bus, ch, val = payload
                if bus == self.state.active_bus_idx and ch in self.view_mixer.strips:
                    self.view_mixer.strips[ch].setFaderSilent(val)
            elif target == "pan":
                bus, ch, val = payload
                if bus == self.state.active_bus_idx and ch in self.view_mixer.strips:
                    self.view_mixer.strips[ch].setPanSilent(val)
            elif target == "pan_silent":
                bus, ch, val = payload
                if bus == self.state.active_bus_idx and ch in self.view_mixer.strips:
                    self.view_mixer.strips[ch].setPanSilent(val)
            elif target == "mute" or target == "mute_silent":
                bus, ch, val = payload
                if bus == self.state.active_bus_idx and ch in self.view_mixer.strips:
                    self.view_mixer.strips[ch].setMuteSilent(val)
            elif target == "solo" or target == "solo_silent":
                bus, ch, val = payload
                if bus == self.state.active_bus_idx and ch in self.view_mixer.strips:
                    self.view_mixer.strips[ch].setSoloSilent(val)
                self.view_mixer.update_solo_alert()
            elif target == "clear_solos":
                bus = payload
                if bus == self.state.active_bus_idx:
                    for s in self.view_mixer.strips.values():
                        s.setSoloSilent(False)
                self.view_mixer.update_solo_alert()
            elif target == "reset_bus":
                bus = payload
                if bus == self.state.active_bus_idx:
                    self.view_mixer.refresh_bus_view(bus)
            elif target == "trim" or target == "trim_silent":
                ch, val = payload
                if ch in self.view_mixer.strips:
                    self.view_mixer.strips[ch].setTrimSilent(val)
                self.view_inputs.sync_input_state(ch)
            elif target == "pad" or target == "pad_silent":
                ch, val = payload
                if ch in self.view_mixer.strips:
                    self.view_mixer.strips[ch].setPadSilent(val)
                self.view_inputs.sync_input_state(ch)
            elif target == "phase" or target == "phase_silent":
                ch, val = payload
                if ch in self.view_mixer.strips:
                    self.view_mixer.strips[ch].setPhaseSilent(val)
                self.view_inputs.sync_input_state(ch)
            elif target == "stereo" or target == "stereo_silent":
                ch, val = payload
                if ch in self.view_mixer.strips:
                    self.view_mixer.strips[ch].setStereoSilent(val)
                partner = self.state.get_partner_channel(ch)
                if partner is not None and partner in self.view_mixer.strips:
                    self.view_mixer.strips[partner].setStereoSilent(val)
                self.view_inputs.sync_input_state(ch)
            elif target == "meter_decay":
                dt = payload
                for s in self.view_mixer.strips.values():
                    s.decayMeter(dt)
                self.view_mixer.master_strip.decayMeter(dt)
                for card in self.view_inputs.cards.values():
                    card.meter.decay(dt)
            elif target in ("snapshot_loaded", "undo", "redo"):
                self.view_mixer.refresh_bus_view(self.state.active_bus_idx)
                for c in range(self.config.num_channels):
                    self.view_inputs.sync_input_state(c)
                self.view_matrix.refresh_table()

        def _on_osc_stats_updated(self, in_pkts: int, out_pkts: int, in_bytes: int, out_bytes: int, is_running: bool):
            status_text = f"OSC: {'Active' if is_running else 'Offline'} [{self.config.osc_target_host}:{self.config.osc_target_port}]"
            self.lbl_status_net.setText(status_text)
            self.view_monitor.update_stats(in_pkts, out_pkts, in_bytes, out_bytes, is_running)

        def _on_input_mute_changed(self, ch: int, muted: bool):
            self.state.inputs[ch].input_mute = muted
            msgs = self.controller.protocol.encode_input_mute(ch, muted)
            self.controller.osc_client.send_messages(msgs)

        def _on_channel_renamed(self, ch: int, name: str):
            self.config.set_channel_name(ch, name)
            self.config.save()
            if ch in self.view_inputs.cards:
                self.view_inputs.cards[ch].lbl_name.setText(name)
            self.view_matrix.table.setVerticalHeaderItem(
                ch, QtWidgets.QTableWidgetItem(f"IN {ch + 1:02d}: {name}")
            )

        def _on_tab_changed(self, idx: int):
            if idx == 2:  # Matrix view
                self.view_matrix.refresh_table()

        def _on_panic_mute(self):
            # Mute all master buses immediately
            for b in range(self.config.num_buses):
                self.controller.on_master_mute_changed(b, True)
            self.view_mixer.master_strip.setMasterMuteSilent(True)
            self.status_bar.showMessage("PANIC MUTE ALL ENGAGED: All master outputs muted", 5000)

        def _on_undo(self):
            if self.state.undo():
                self.status_bar.showMessage("Undo executed", 2000)
            else:
                self.status_bar.showMessage("Nothing to undo", 2000)

        def _on_redo(self):
            if self.state.redo():
                self.status_bar.showMessage("Redo executed", 2000)
            else:
                self.status_bar.showMessage("Nothing to redo", 2000)

        def _reset_mixer_defaults(self):
            ret = QtWidgets.QMessageBox.question(
                self,
                "Reset Console",
                "Reset entire console to Unity Gain (0 dB) defaults on all buses?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.No
            )
            if ret == QtWidgets.QMessageBox.StandardButton.Yes:
                for b in range(self.config.num_buses):
                    self.controller.reset_bus_sends(b)
                self.status_bar.showMessage("Console reset to Unity defaults", 3000)

        def _open_snapshot_dialog(self):
            here = os.path.dirname(os.path.abspath(__file__))
            default_dir = os.path.join(os.path.dirname(here), "snapshots")
            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "Load Mixer Snapshot", default_dir, "CuteMix Snapshot (*.json)"
            )
            if path:
                if self.controller.load_snapshot(path):
                    self.status_bar.showMessage(f"Snapshot loaded: {os.path.basename(path)}", 4000)
                else:
                    QtWidgets.QMessageBox.warning(self, "Load Error", f"Could not load snapshot from: {path}")

        def _save_snapshot_dialog(self):
            here = os.path.dirname(os.path.abspath(__file__))
            default_dir = os.path.join(os.path.dirname(here), "snapshots")
            os.makedirs(default_dir, exist_ok=True)
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Save Mixer Snapshot", os.path.join(default_dir, "snapshot.json"), "CuteMix Snapshot (*.json)"
            )
            if path:
                if self.controller.save_snapshot(path):
                    self.status_bar.showMessage(f"Snapshot saved: {os.path.basename(path)}", 4000)
                else:
                    QtWidgets.QMessageBox.warning(self, "Save Error", f"Could not save snapshot to: {path}")

        def _open_settings_dialog(self):
            dlg = SettingsDialog(self.config, self)
            dlg.settingsSaved.connect(self._on_settings_applied)
            dlg.exec()

        def _on_settings_applied(self):
            self.controller.update_config()
            self.lbl_status_hw.setText(f"Hardware: PCIe-424 | {self.config.interface_model} (Slot {self.config.slot_letter})")
            self.view_mixer.refresh_bus_view(self.state.active_bus_idx)
            self.status_bar.showMessage("Preferences saved and OSC client updated", 3000)

        def _show_help_dialog(self):
            text = (
                "<h3>MOTU CueMix FX + CuteMix OSC Setup Guide</h3>"
                "<p>This Qt application controls your MOTU PCIe-424 with 24i interface over Open Sound Control (OSC).</p>"
                "<h4>Windows Desktop Setup:</h4>"
                "<ol>"
                "<li><b>Launch MOTU CueMix FX:</b> Open the CueMix FX application installed with your MOTU PCIe-424 Windows driver.</li>"
                "<li><b>Configure OSC in CueMix FX:</b>"
                "<ul>"
                "<li>Go to the menu <b>Control Surfaces > Configure OSC Devices...</b></li>"
                "<li>If Bonjour is enabled, <b>CuteMix 424 (TouchOSC)</b> will appear automatically. Select it!</li>"
                "<li>Alternatively, enter manually: Host <code>127.0.0.1</code>, Send Port <code>9000</code>, Receive Port <code>8000</code>.</li>"
                "<li>Under <b>Control Surfaces > TouchOSC</b>, ensure the connection is checked/enabled.</li>"
                "</ul></li>"
                "<li><b>Using CuteMix:</b>"
                "<ul>"
                "<li>Adjust any fader, pan, trim, mute, solo, or pad: CuteMix transmits OSC commands to CueMix FX immediately.</li>"
                "<li>Inspect live packet traffic in the <b>OSC Monitor & Diagnostics</b> tab.</li>"
                "<li>Save & recall snapshots with <code>Ctrl+S</code> / <code>Ctrl+O</code>.</li>"
                "</ul></li>"
                "</ol>"
            )
            QtWidgets.QMessageBox.information(self, "CuteMix OSC Setup Guide", text)

        def _show_about_dialog(self):
            text = (
                "<h2>CuteMix v1.0.0</h2>"
                "<p><b>Hardware Console Controller for MOTU PCIe-424 & 24i over OSC</b></p>"
                "<p>Built with Python & Qt.</p>"
                "<p>Reverse engineered from MOTU CueMix FX TouchOSC layouts and the Linux-motu-pci-424 control map.</p>"
                "<p>Supports 24 analog input channels, multi-bus sends, preamp conditioning, stereo linking, and live OSC inspection.</p>"
            )
            QtWidgets.QMessageBox.about(self, "About CuteMix", text)

        def closeEvent(self, event: QtGui.QCloseEvent):
            self.controller.stop()
            self.config.save()
            event.accept()
