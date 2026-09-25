"""
Main Controller for CuteMix.
Bridges Qt UI views, MixerState data model, CueMix OSC protocol, and UDP network client.
Manages bi-directional synchronization, linking, undo/redo, and meter decay timers.
"""

from typing import Any, Dict, List, Optional
from .qt_compat import QtCore, Signal, Slot, is_qt_available
from .model.config import AppConfig
from .model.mixer_state import MixerState
from .osc.osc_core import OscMessage
from .osc.osc_client import OscClient, OscLogEntry
from .osc.cuemix_protocol import CueMixProtocol
from .osc.zeroconf_service import CueMixZeroconfPublisher

if is_qt_available():
    class CuteMixController(QtCore.QObject):
        # UI notification signals
        stateUpdated = Signal(str, object)
        oscStatsUpdated = Signal(int, int, int, int, bool)
        oscPacketLogged = Signal(object)
        statusMessage = Signal(str)

        def __init__(self, config: AppConfig, mixer_state: MixerState, parent=None):
            super().__init__(parent)
            self.config = config
            self.state = mixer_state

            # OSC protocol engine
            self.protocol = CueMixProtocol(dialect=config.osc_dialect, prefix=config.osc_prefix)

            # UDP OSC client/listener
            self.osc_client = OscClient(
                target_host=config.osc_target_host,
                target_port=config.osc_target_port,
                listen_port=config.osc_listen_port
            )
            self.osc_client.on_message_received = self._on_osc_message_received
            self.osc_client.on_packet_logged = self._on_osc_packet_logged
            self.osc_client.on_error = lambda err: self.statusMessage.emit(f"OSC Error: {err}")

            # Bonjour publisher
            self.zeroconf_pub = CueMixZeroconfPublisher(
                service_name=config.zeroconf_name,
                port=config.osc_listen_port
            )

            # Timer for meter decay & status polling
            self._timer = QtCore.QTimer(self)
            self._timer.setInterval(40)  # 25 FPS
            self._timer.timeout.connect(self._on_tick)

        def start(self):
            """Starts network listener and background timers."""
            ok = self.osc_client.start()
            if ok:
                self.statusMessage.emit(
                    f"OSC listening on UDP port {self.config.osc_listen_port} | "
                    f"Sending to {self.config.osc_target_host}:{self.config.osc_target_port}"
                )
            else:
                self.statusMessage.emit(f"Could not bind to UDP port {self.config.osc_listen_port}")

            if self.config.enable_zeroconf and CueMixZeroconfPublisher.is_supported():
                if self.zeroconf_pub.start():
                    self.statusMessage.emit("Bonjour auto-discovery active: 'CuteMix 424 (TouchOSC)'")

            self._timer.start()

        def stop(self):
            self._timer.stop()
            self.zeroconf_pub.stop()
            self.osc_client.stop()

        def update_config(self):
            """Applies new network settings from AppConfig."""
            self.protocol = CueMixProtocol(dialect=self.config.osc_dialect, prefix=self.config.osc_prefix)
            self.osc_client.update_config(
                self.config.osc_target_host,
                self.config.osc_target_port,
                self.config.osc_listen_port
            )
            if self.config.enable_zeroconf and CueMixZeroconfPublisher.is_supported():
                self.zeroconf_pub.stop()
                self.zeroconf_pub.port = self.config.osc_listen_port
                self.zeroconf_pub.start()
            else:
                self.zeroconf_pub.stop()

        # ----------------- User UI Actions -> OSC Out -----------------

        @Slot(int, int, float)
        def on_fader_changed(self, bus_idx: int, channel_idx: int, norm_value: float):
            affected = self.state.set_send_fader(bus_idx, channel_idx, norm_value, update_links=True)
            for ch, val in affected:
                msgs = self.protocol.encode_send_fader(bus_idx, ch, val)
                self.osc_client.send_messages(msgs)
                self.stateUpdated.emit("fader", (bus_idx, ch, val))

        @Slot(int, int, float)
        def on_pan_changed(self, bus_idx: int, channel_idx: int, norm_value: float):
            affected = self.state.set_send_pan(bus_idx, channel_idx, norm_value, update_links=True)
            for ch, val in affected:
                msgs = self.protocol.encode_send_pan(bus_idx, ch, val)
                self.osc_client.send_messages(msgs)
                self.stateUpdated.emit("pan", (bus_idx, ch, val))

        @Slot(int, int, bool)
        def on_mute_changed(self, bus_idx: int, channel_idx: int, muted: bool):
            affected = self.state.set_send_mute(bus_idx, channel_idx, muted, update_links=True)
            for ch, val in affected:
                msgs = self.protocol.encode_send_mute(bus_idx, ch, val)
                self.osc_client.send_messages(msgs)
                self.stateUpdated.emit("mute", (bus_idx, ch, val))

        @Slot(int, int, bool)
        def on_solo_changed(self, bus_idx: int, channel_idx: int, soloed: bool):
            affected = self.state.set_send_solo(bus_idx, channel_idx, soloed, update_links=True)
            for ch, val in affected:
                msgs = self.protocol.encode_send_solo(bus_idx, ch, val)
                self.osc_client.send_messages(msgs)
                self.stateUpdated.emit("solo", (bus_idx, ch, val))

        @Slot(int, float)
        def on_trim_changed(self, channel_idx: int, norm_value: float):
            self.state.inputs[channel_idx].trim_norm = norm_value
            msgs = self.protocol.encode_input_trim(channel_idx, norm_value)
            self.osc_client.send_messages(msgs)
            self.stateUpdated.emit("trim", (channel_idx, norm_value))

        @Slot(int, bool)
        def on_pad_changed(self, channel_idx: int, enabled: bool):
            self.state.inputs[channel_idx].pad = enabled
            msgs = self.protocol.encode_input_pad(channel_idx, enabled)
            self.osc_client.send_messages(msgs)
            self.stateUpdated.emit("pad", (channel_idx, enabled))

        @Slot(int, bool)
        def on_phase_changed(self, channel_idx: int, inverted: bool):
            self.state.inputs[channel_idx].phase = inverted
            msgs = self.protocol.encode_input_phase(channel_idx, inverted)
            self.osc_client.send_messages(msgs)
            self.stateUpdated.emit("phase", (channel_idx, inverted))

        @Slot(int, bool)
        def on_stereo_changed(self, channel_idx: int, linked: bool):
            affected = self.state.set_stereo_link(channel_idx, linked)
            for ch in affected:
                msgs = self.protocol.encode_input_stereo(ch, linked)
                self.osc_client.send_messages(msgs)
                self.stateUpdated.emit("stereo", (ch, linked))

        @Slot(int, float)
        def on_master_fader_changed(self, bus_idx: int, norm_value: float):
            self.state.buses[bus_idx].master_fader_norm = norm_value
            msgs = self.protocol.encode_master_fader(bus_idx, norm_value)
            self.osc_client.send_messages(msgs)
            self.stateUpdated.emit("master_fader", (bus_idx, norm_value))

        @Slot(int, bool)
        def on_master_mute_changed(self, bus_idx: int, muted: bool):
            self.state.buses[bus_idx].master_mute = muted
            msgs = self.protocol.encode_master_mute(bus_idx, muted)
            self.osc_client.send_messages(msgs)
            self.stateUpdated.emit("master_mute", (bus_idx, muted))

        @Slot()
        def clear_all_solos(self):
            bus_idx = self.state.active_bus_idx
            self.state.clear_all_solos(bus_idx)
            for ch in range(self.config.num_channels):
                msgs = self.protocol.encode_send_solo(bus_idx, ch, False)
                self.osc_client.send_messages(msgs)
            self.stateUpdated.emit("clear_solos", bus_idx)

        @Slot(int)
        def reset_bus_sends(self, bus_idx: int):
            self.state.reset_bus_sends(bus_idx)
            # Transmit reset state over OSC
            bus = self.state.buses[bus_idx]
            for ch in range(self.config.num_channels):
                self.osc_client.send_messages(self.protocol.encode_send_fader(bus_idx, ch, 0.78))
                self.osc_client.send_messages(self.protocol.encode_send_pan(bus_idx, ch, 0.5))
                self.osc_client.send_messages(self.protocol.encode_send_mute(bus_idx, ch, False))
                self.osc_client.send_messages(self.protocol.encode_send_solo(bus_idx, ch, False))
            self.osc_client.send_messages(self.protocol.encode_master_fader(bus_idx, 0.78))
            self.osc_client.send_messages(self.protocol.encode_master_mute(bus_idx, False))
            self.stateUpdated.emit("reset_bus", bus_idx)

        @Slot(str, list)
        def send_manual_osc(self, address: str, args: list):
            msg = OscMessage(address, args)
            self.osc_client.send_message(msg)

        # ----------------- Incoming OSC From CueMix FX -----------------

        def _on_osc_message_received(self, msg: OscMessage, addr: tuple):
            parsed = self.protocol.decode_message(msg)
            if not parsed:
                return

            target = parsed["target"]
            bus = parsed["bus"]
            ch = parsed["channel"]
            val = parsed["value"]

            # Dispatch silently to data model & emit update to UI
            if target == "send_fader" and bus is not None and ch is not None:
                self.state.buses[bus].sends[ch].fader_norm = val
                self.stateUpdated.emit("fader_silent", (bus, ch, val))
            elif target == "send_pan" and bus is not None and ch is not None:
                self.state.buses[bus].sends[ch].pan_norm = val
                self.stateUpdated.emit("pan_silent", (bus, ch, val))
            elif target == "send_mute" and bus is not None and ch is not None:
                self.state.buses[bus].sends[ch].mute = bool(val)
                self.stateUpdated.emit("mute_silent", (bus, ch, bool(val)))
            elif target == "send_solo" and bus is not None and ch is not None:
                self.state.buses[bus].sends[ch].solo = bool(val)
                self.stateUpdated.emit("solo_silent", (bus, ch, bool(val)))
            elif target == "master_fader" and bus is not None:
                self.state.buses[bus].master_fader_norm = val
                self.stateUpdated.emit("master_fader_silent", (bus, val))
            elif target == "master_mute" and bus is not None:
                self.state.buses[bus].master_mute = bool(val)
                self.stateUpdated.emit("master_mute_silent", (bus, bool(val)))
            elif target == "input_trim" and ch is not None:
                self.state.inputs[ch].trim_norm = val
                self.stateUpdated.emit("trim_silent", (ch, val))
            elif target == "input_pad" and ch is not None:
                self.state.inputs[ch].pad = bool(val)
                self.stateUpdated.emit("pad_silent", (ch, bool(val)))
            elif target == "input_phase" and ch is not None:
                self.state.inputs[ch].phase = bool(val)
                self.stateUpdated.emit("phase_silent", (ch, bool(val)))
            elif target == "input_stereo" and ch is not None:
                self.state.inputs[ch].stereo_link = bool(val)
                self.stateUpdated.emit("stereo_silent", (ch, bool(val)))
            elif target == "meters":
                self.stateUpdated.emit("meters", val)

        def _on_osc_packet_logged(self, entry: OscLogEntry):
            self.oscPacketLogged.emit(entry)

        def _on_tick(self):
            # Emit statistics
            is_conn = self.osc_client.is_running()
            self.oscStatsUpdated.emit(
                self.osc_client.packets_received,
                self.osc_client.packets_sent,
                self.osc_client.bytes_received,
                self.osc_client.bytes_sent,
                is_conn
            )
            # Emit meter decay
            self.stateUpdated.emit("meter_decay", 0.04)

        # ----------------- Snapshot Management -----------------

        def save_snapshot(self, path: str) -> bool:
            return self.state.save_snapshot_file(path)

        def load_snapshot(self, path: str) -> bool:
            ok = self.state.load_snapshot_file(path)
            if ok:
                # Transmit all restored values over OSC
                active_b = self.state.active_bus_idx
                bus = self.state.buses[active_b]
                for ch in range(self.config.num_channels):
                    send = bus.sends[ch]
                    inp = self.state.inputs[ch]
                    self.osc_client.send_messages(self.protocol.encode_send_fader(active_b, ch, send.fader_norm))
                    self.osc_client.send_messages(self.protocol.encode_send_pan(active_b, ch, send.pan_norm))
                    self.osc_client.send_messages(self.protocol.encode_send_mute(active_b, ch, send.mute))
                    self.osc_client.send_messages(self.protocol.encode_send_solo(active_b, ch, send.solo))
                    self.osc_client.send_messages(self.protocol.encode_input_trim(ch, inp.trim_norm))
                    self.osc_client.send_messages(self.protocol.encode_input_pad(ch, inp.pad))
                    self.osc_client.send_messages(self.protocol.encode_input_phase(ch, inp.phase))
                    self.osc_client.send_messages(self.protocol.encode_input_stereo(ch, inp.stereo_link))
                self.osc_client.send_messages(self.protocol.encode_master_fader(active_b, bus.master_fader_norm))
                self.osc_client.send_messages(self.protocol.encode_master_mute(active_b, bus.master_mute))
                self.stateUpdated.emit("snapshot_loaded", path)
            return ok
