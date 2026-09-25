"""
Complete Mixer State Data Model for CuteMix.
Maintains state of 24 input channels, multi-bus sends, master strips,
stereo links, gang groups, meter states, and undo/redo snapshots.
"""

import copy
import json
import os
import time
from typing import Callable, Dict, List, Optional, Any, Tuple
from .config import AppConfig


class InputChannelState:
    def __init__(self, idx: int):
        self.idx = idx
        self.trim_norm: float = 0.0      # 0.0 .. 1.0 (0 dB .. max trim)
        self.pad: bool = False           # -20 dB pad
        self.phase: bool = False         # Invert polarity
        self.stereo_link: bool = False   # Linked with idx+1 (if even) or idx-1 (if odd)
        self.input_mute: bool = False    # Input pre-fader mute

        # Metering runtime state
        self.meter_level: float = 0.0
        self.meter_peak: float = 0.0
        self.meter_clip: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "idx": self.idx,
            "trim_norm": self.trim_norm,
            "pad": self.pad,
            "phase": self.phase,
            "stereo_link": self.stereo_link,
            "input_mute": self.input_mute,
        }

    def from_dict(self, data: Dict[str, Any]):
        self.trim_norm = float(data.get("trim_norm", self.trim_norm))
        self.pad = bool(data.get("pad", self.pad))
        self.phase = bool(data.get("phase", self.phase))
        self.stereo_link = bool(data.get("stereo_link", self.stereo_link))
        self.input_mute = bool(data.get("input_mute", self.input_mute))


class BusSendState:
    def __init__(self, channel_idx: int):
        self.channel_idx = channel_idx
        self.fader_norm: float = 0.78     # Unity (0 dB)
        self.pan_norm: float = 0.5        # Center
        self.mute: bool = False
        self.solo: bool = False
        self.gang: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel_idx": self.channel_idx,
            "fader_norm": self.fader_norm,
            "pan_norm": self.pan_norm,
            "mute": self.mute,
            "solo": self.solo,
            "gang": self.gang,
        }

    def from_dict(self, data: Dict[str, Any]):
        self.fader_norm = float(data.get("fader_norm", self.fader_norm))
        self.pan_norm = float(data.get("pan_norm", self.pan_norm))
        self.mute = bool(data.get("mute", self.mute))
        self.solo = bool(data.get("solo", self.solo))
        self.gang = bool(data.get("gang", self.gang))


class MixBusState:
    def __init__(self, idx: int, num_channels: int = 24):
        self.idx = idx
        self.name: str = f"Mix {idx + 1}"
        self.sends: Dict[int, BusSendState] = {
            i: BusSendState(i) for i in range(num_channels)
        }
        self.master_fader_norm: float = 0.78  # Unity (0 dB)
        self.master_mute: bool = False

        # Master meter runtime state
        self.meter_l: float = 0.0
        self.meter_r: float = 0.0
        self.peak_l: float = 0.0
        self.peak_r: float = 0.0
        self.clip_l: bool = False
        self.clip_r: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "idx": self.idx,
            "name": self.name,
            "master_fader_norm": self.master_fader_norm,
            "master_mute": self.master_mute,
            "sends": {str(k): v.to_dict() for k, v in self.sends.items()},
        }

    def from_dict(self, data: Dict[str, Any]):
        self.name = data.get("name", self.name)
        self.master_fader_norm = float(data.get("master_fader_norm", self.master_fader_norm))
        self.master_mute = bool(data.get("master_mute", self.master_mute))
        if "sends" in data:
            for k_str, s_dict in data["sends"].items():
                k = int(k_str)
                if k in self.sends:
                    self.sends[k].from_dict(s_dict)


class MixerState:
    """
    Central mixer state model holding inputs, buses, global parameters,
    and undo/redo history.
    """

    def __init__(self, config: AppConfig):
        self.config = config
        self.num_channels = config.num_channels
        self.num_buses = config.num_buses
        self.active_bus_idx = config.active_bus

        # Inputs (channel conditioning)
        self.inputs: Dict[int, InputChannelState] = {
            i: InputChannelState(i) for i in range(self.num_channels)
        }

        # Mix buses
        self.buses: Dict[int, MixBusState] = {
            b: MixBusState(b, self.num_channels) for b in range(self.num_buses)
        }

        # Global studio controls
        self.talkback: bool = False
        self.listenback: bool = False
        self.atten_norm: float = 0.2  # ~ -20 dB ducking

        # Change callbacks
        self.on_state_changed: Optional[Callable[[str, Any], None]] = None

        # Undo / Redo history stack
        self._history: List[Dict[str, Any]] = []
        self._history_idx: int = -1
        self._max_history = 30
        self.push_history("Initial State")

    # ----------------- History / Undo / Redo -----------------

    def push_history(self, action_name: str = ""):
        state_snapshot = copy.deepcopy(self.to_dict())
        # Truncate any forward history if we made changes after an undo
        if self._history_idx >= 0 and self._history_idx < len(self._history) - 1:
            self._history = self._history[:self._history_idx + 1]

        self._history.append(state_snapshot)
        if len(self._history) > self._max_history:
            self._history.pop(0)
        self._history_idx = len(self._history) - 1

    def can_undo(self) -> bool:
        return self._history_idx > 0

    def can_redo(self) -> bool:
        return self._history_idx >= 0 and self._history_idx < len(self._history) - 1

    def undo(self) -> bool:
        if not self.can_undo():
            return False
        self._history_idx -= 1
        prev = self._history[self._history_idx]
        self.from_dict(prev)
        if self.on_state_changed:
            self.on_state_changed("undo", None)
        return True

    def redo(self) -> bool:
        if not self.can_redo():
            return False
        self._history_idx += 1
        nxt = self._history[self._history_idx]
        self.from_dict(nxt)
        if self.on_state_changed:
            self.on_state_changed("redo", None)
        return True

    # ----------------- Helpers -----------------

    def get_input(self, ch: int) -> InputChannelState:
        return self.inputs[ch]

    def get_active_bus(self) -> MixBusState:
        return self.buses.get(self.active_bus_idx, self.buses[0])

    def get_send(self, bus_idx: int, ch: int) -> BusSendState:
        return self.buses[bus_idx].sends[ch]

    def get_partner_channel(self, ch: int) -> Optional[int]:
        """Returns paired channel index if stereo linked, else None."""
        if not self.inputs[ch].stereo_link:
            return None
        return (ch + 1) if (ch % 2 == 0) else (ch - 1)

    def is_any_solo_active(self, bus_idx: Optional[int] = None) -> bool:
        """Returns True if any input send is soloed."""
        target_buses = [self.buses[bus_idx]] if bus_idx is not None else self.buses.values()
        for b in target_buses:
            for s in b.sends.values():
                if s.solo:
                    return True
        return False

    def clear_all_solos(self, bus_idx: Optional[int] = None):
        """Clears solo on all sends."""
        target_buses = [self.buses[bus_idx]] if bus_idx is not None else self.buses.values()
        for b in target_buses:
            for s in b.sends.values():
                s.solo = False
        if self.on_state_changed:
            self.on_state_changed("clear_solos", bus_idx)

    def reset_bus_sends(self, bus_idx: int):
        """Resets all sends in bus_idx to unity (0 dB), center pan, mutes off."""
        bus = self.buses[bus_idx]
        for s in bus.sends.values():
            s.fader_norm = 0.78
            s.pan_norm = 0.5
            s.mute = False
            s.solo = False
        bus.master_fader_norm = 0.78
        bus.master_mute = False
        if self.on_state_changed:
            self.on_state_changed("reset_bus", bus_idx)

    # ----------------- Actions with Linking / Ganging -----------------

    def set_send_fader(self, bus_idx: int, ch: int, norm_value: float, update_links: bool = True) -> List[Tuple[int, float]]:
        """Sets send fader position. Handles stereo link and gang groups."""
        norm_value = max(0.0, min(1.0, norm_value))
        send = self.get_send(bus_idx, ch)
        delta = norm_value - send.fader_norm
        send.fader_norm = norm_value

        affected = [(ch, norm_value)]

        if update_links:
            # Check Stereo Link
            partner = self.get_partner_channel(ch)
            if partner is not None and partner in self.buses[bus_idx].sends:
                p_send = self.get_send(bus_idx, partner)
                p_val = max(0.0, min(1.0, p_send.fader_norm + delta))
                p_send.fader_norm = p_val
                affected.append((partner, p_val))

            # Check Gang Group
            if send.gang:
                for other_ch, other_send in self.buses[bus_idx].sends.items():
                    if other_ch != ch and other_ch != partner and other_send.gang:
                        g_val = max(0.0, min(1.0, other_send.fader_norm + delta))
                        other_send.fader_norm = g_val
                        affected.append((other_ch, g_val))

        return affected

    def set_send_pan(self, bus_idx: int, ch: int, norm_value: float, update_links: bool = True) -> List[Tuple[int, float]]:
        norm_value = max(0.0, min(1.0, norm_value))
        send = self.get_send(bus_idx, ch)
        send.pan_norm = norm_value
        affected = [(ch, norm_value)]

        if update_links:
            # In stereo mode, mirror partner pan (L <-> R)
            partner = self.get_partner_channel(ch)
            if partner is not None and partner in self.buses[bus_idx].sends:
                p_send = self.get_send(bus_idx, partner)
                p_val = 1.0 - norm_value
                p_send.pan_norm = p_val
                affected.append((partner, p_val))

        return affected

    def set_send_mute(self, bus_idx: int, ch: int, muted: bool, update_links: bool = True) -> List[Tuple[int, bool]]:
        send = self.get_send(bus_idx, ch)
        send.mute = muted
        affected = [(ch, muted)]

        if update_links:
            partner = self.get_partner_channel(ch)
            if partner is not None and partner in self.buses[bus_idx].sends:
                self.get_send(bus_idx, partner).mute = muted
                affected.append((partner, muted))

        return affected

    def set_send_solo(self, bus_idx: int, ch: int, soloed: bool, update_links: bool = True) -> List[Tuple[int, bool]]:
        send = self.get_send(bus_idx, ch)
        send.solo = soloed
        affected = [(ch, soloed)]

        if update_links:
            partner = self.get_partner_channel(ch)
            if partner is not None and partner in self.buses[bus_idx].sends:
                self.get_send(bus_idx, partner).solo = soloed
                affected.append((partner, soloed))

        return affected

    def set_stereo_link(self, ch: int, linked: bool) -> List[int]:
        """Toggles stereo linking between ch and its even/odd partner."""
        partner = (ch + 1) if (ch % 2 == 0) else (ch - 1)
        if partner < 0 or partner >= self.num_channels:
            return [ch]

        self.inputs[ch].stereo_link = linked
        self.inputs[partner].stereo_link = linked

        # If linking was just engaged, auto-pan L and R
        if linked:
            left_ch = min(ch, partner)
            right_ch = max(ch, partner)
            for b in self.buses.values():
                b.sends[left_ch].pan_norm = 0.0   # Hard Left
                b.sends[right_ch].pan_norm = 1.0  # Hard Right
                # Match faders
                b.sends[right_ch].fader_norm = b.sends[left_ch].fader_norm
                b.sends[right_ch].mute = b.sends[left_ch].mute

        return [ch, partner]

    # ----------------- Serialization -----------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "num_channels": self.num_channels,
            "num_buses": self.num_buses,
            "active_bus_idx": self.active_bus_idx,
            "talkback": self.talkback,
            "listenback": self.listenback,
            "atten_norm": self.atten_norm,
            "inputs": {str(k): v.to_dict() for k, v in self.inputs.items()},
            "buses": {str(k): v.to_dict() for k, v in self.buses.items()},
        }

    def from_dict(self, data: Dict[str, Any]):
        self.active_bus_idx = int(data.get("active_bus_idx", self.active_bus_idx))
        self.talkback = bool(data.get("talkback", self.talkback))
        self.listenback = bool(data.get("listenback", self.listenback))
        self.atten_norm = float(data.get("atten_norm", self.atten_norm))

        if "inputs" in data:
            for k_str, in_dict in data["inputs"].items():
                k = int(k_str)
                if k in self.inputs:
                    self.inputs[k].from_dict(in_dict)

        if "buses" in data:
            for k_str, bus_dict in data["buses"].items():
                k = int(k_str)
                if k in self.buses:
                    self.buses[k].from_dict(bus_dict)

    def save_snapshot_file(self, file_path: str) -> bool:
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2, sort_keys=True)
            return True
        except Exception:
            return False

    def load_snapshot_file(self, file_path: str) -> bool:
        if not os.path.exists(file_path):
            return False
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.from_dict(data)
                self.push_history(f"Loaded snapshot: {os.path.basename(file_path)}")
            return True
        except Exception:
            return False
