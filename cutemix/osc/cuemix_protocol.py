"""
CueMix FX OSC Protocol and Address Mapping Engine.
Reverse engineered from CueMixFX-PCI-424.touchosc and devfrp/Linux-motu-pci-424 docs.
Provides translation between UI state and OSC messages for MOTU PCI/PCIe-424 + 24i.
"""

import math
import re
from typing import Any, Dict, List, Optional, Tuple, Union
from .osc_core import OscMessage


# -----------------------------------------------------------------------------
# Fader / Pan / Trim Conversion Helpers
# -----------------------------------------------------------------------------

def norm_to_db(norm: float) -> float:
    """
    Converts normalized fader position (0.0 .. 1.0) to decibels (-inf .. +6 dB).
    Unity (0 dB) is calibrated at ~0.78 fader travel.
    """
    if norm <= 0.001:
        return -float("inf")
    if norm >= 0.999:
        return 6.0
    if norm <= 0.78:
        # Range -60 dB to 0 dB
        # 40 * log10(norm / 0.78)
        ratio = max(0.0001, norm / 0.78)
        db = 40.0 * math.log10(ratio)
        return max(-60.0, db)
    else:
        # Range 0 dB to +6 dB
        t = (norm - 0.78) / (1.0 - 0.78)
        return t * 6.0


def db_to_norm(db: float) -> float:
    """Converts decibels (-inf .. +6 dB) to normalized fader position (0.0 .. 1.0)."""
    if db <= -60.0 or math.isinf(db):
        return 0.0
    if db >= 6.0:
        return 1.0
    if db <= 0.0:
        # inverse of db = 40 * log10(norm / 0.78)
        ratio = 10.0 ** (db / 40.0)
        return max(0.0, min(0.78, ratio * 0.78))
    else:
        t = db / 6.0
        return 0.78 + t * (1.0 - 0.78)


def format_db(db: float) -> str:
    """Formats decibel value for UI labels."""
    if math.isinf(db) or db <= -60.0:
        return "-inf dB"
    if abs(db) < 0.05:
        return "0.0 dB"
    if db > 0:
        return f"+{db:.1f} dB"
    return f"{db:.1f} dB"


def norm_to_pan(norm: float) -> int:
    """Converts 0.0 .. 1.0 to pan integer -100 (L) to +100 (R)."""
    p = int(round((norm - 0.5) * 200.0))
    return max(-100, min(100, p))


def pan_to_norm(pan: int) -> float:
    """Converts pan integer -100 .. +100 to normalized 0.0 .. 1.0."""
    return max(0.0, min(1.0, (pan / 200.0) + 0.5))


def format_pan(pan: int) -> str:
    """Formats pan integer for UI labels."""
    if pan == 0:
        return "C"
    if pan < 0:
        return f"L{abs(pan)}"
    return f"R{pan}"


def norm_to_trim(norm: float, max_trim_db: float = 24.0) -> float:
    """Converts normalized 0.0 .. 1.0 to trim dB (0 .. max_trim_db)."""
    return norm * max_trim_db


def trim_to_norm(trim_db: float, max_trim_db: float = 24.0) -> float:
    """Converts trim dB to normalized 0.0 .. 1.0."""
    return max(0.0, min(1.0, trim_db / max_trim_db))


def format_trim(trim_db: float) -> str:
    """Formats trim dB for UI labels."""
    if abs(trim_db) < 0.05:
        return "0 dB"
    return f"+{trim_db:.1f} dB"


# -----------------------------------------------------------------------------
# CueMix FX OSC Protocol Translation
# -----------------------------------------------------------------------------

# Regex patterns to decode incoming TouchOSC and Direct OSC addresses
_RE_TOUCHOSC_IN_TRM = re.compile(r"^/in/fvInCS\+(\d+)/in/trm$")
_RE_TOUCHOSC_IN_PAD = re.compile(r"^/in/fvInCS\+(\d+)/in/pad$")
_RE_TOUCHOSC_IN_PSI = re.compile(r"^/in/fvInCS\+(\d+)/in/psi$")
_RE_TOUCHOSC_IN_ST = re.compile(r"^/in/fvInCS\+(\d+)/in/st$")
_RE_TOUCHOSC_IN_MUTE = re.compile(r"^/in/fvInCS\+(\d+)/in/mute$")
_RE_TOUCHOSC_IN_PFL = re.compile(r"^/bin/fvEB\+(\d+)/fvInCS\+(\d+)/pflS$")
_RE_TOUCHOSC_SND_CDF = re.compile(r"^/bin/fvEB\+(\d+)/fvInCS\+(\d+)/cdf$")
_RE_TOUCHOSC_SND_PAN = re.compile(r"^/bin/fvEB\+(\d+)/fvInCS\+(\d+)/pan$")
_RE_TOUCHOSC_SND_MUTE = re.compile(r"^/bin/fvEB\+(\d+)/fvInCS\+(\d+)/mute$")
_RE_TOUCHOSC_SND_SOLO = re.compile(r"^/bin/fvEB\+(\d+)/fvInCS\+(\d+)/solo$")
_RE_TOUCHOSC_BUS_MASTER = re.compile(r"^/bus/fvEB\+(\d+)/mix/blS$")
_RE_TOUCHOSC_BUS_MUTE = re.compile(r"^/bus/fvEB\+(\d+)/mix/mute$")

# Hierarchical direct patterns
_RE_DIRECT_IN_TRM = re.compile(r"^/input/(\d+)/trim$")
_RE_DIRECT_IN_PAD = re.compile(r"^/input/(\d+)/pad$")
_RE_DIRECT_IN_PSI = re.compile(r"^/input/(\d+)/phase$")
_RE_DIRECT_IN_ST = re.compile(r"^/input/(\d+)/stereo$")
_RE_DIRECT_IN_MUTE = re.compile(r"^/input/(\d+)/mute$")
_RE_DIRECT_SND_VOL = re.compile(r"^/mix/(\d+)/input/(\d+)/vol(?:ume)?$")
_RE_DIRECT_SND_PAN = re.compile(r"^/mix/(\d+)/input/(\d+)/pan$")
_RE_DIRECT_SND_MUTE = re.compile(r"^/mix/(\d+)/input/(\d+)/mute$")
_RE_DIRECT_SND_SOLO = re.compile(r"^/mix/(\d+)/input/(\d+)/solo$")
_RE_DIRECT_BUS_MASTER = re.compile(r"^/mix/(\d+)/master/vol(?:ume)?$")
_RE_DIRECT_BUS_MUTE = re.compile(r"^/mix/(\d+)/master/mute$")


class CueMixProtocol:
    """
    Encodes UI mixer actions to OSC messages and decodes incoming OSC messages from CueMix FX.
    Supports TouchOSC dialect, Direct hierarchical dialect, or Dual broadcast.
    """

    def __init__(self, dialect: str = "touchosc", prefix: str = ""):
        # dialect can be 'touchosc', 'direct', or 'both'
        self.dialect = dialect.lower()
        self.prefix = prefix.rstrip("/") if prefix else ""

    def _fmt_addr(self, addr: str) -> str:
        if self.prefix:
            return f"{self.prefix}{addr}"
        return addr

    # ----------------- Encoding: Input Conditioning -----------------

    def encode_input_trim(self, channel_idx: int, norm_value: float) -> List[OscMessage]:
        msgs = []
        val = float(max(0.0, min(1.0, norm_value)))
        if self.dialect in ("touchosc", "both"):
            msgs.append(OscMessage(self._fmt_addr(f"/in/fvInCS+{channel_idx}/in/trm"), [val]))
        if self.dialect in ("direct", "both"):
            msgs.append(OscMessage(self._fmt_addr(f"/input/{channel_idx + 1}/trim"), [val]))
        return msgs

    def encode_input_pad(self, channel_idx: int, enabled: bool) -> List[OscMessage]:
        msgs = []
        val = 1.0 if enabled else 0.0
        if self.dialect in ("touchosc", "both"):
            msgs.append(OscMessage(self._fmt_addr(f"/in/fvInCS+{channel_idx}/in/pad"), [val]))
        if self.dialect in ("direct", "both"):
            msgs.append(OscMessage(self._fmt_addr(f"/input/{channel_idx + 1}/pad"), [val]))
        return msgs

    def encode_input_phase(self, channel_idx: int, inverted: bool) -> List[OscMessage]:
        msgs = []
        val = 1.0 if inverted else 0.0
        if self.dialect in ("touchosc", "both"):
            msgs.append(OscMessage(self._fmt_addr(f"/in/fvInCS+{channel_idx}/in/psi"), [val]))
        if self.dialect in ("direct", "both"):
            msgs.append(OscMessage(self._fmt_addr(f"/input/{channel_idx + 1}/phase"), [val]))
        return msgs

    def encode_input_stereo(self, channel_idx: int, paired: bool) -> List[OscMessage]:
        msgs = []
        val = 1.0 if paired else 0.0
        if self.dialect in ("touchosc", "both"):
            msgs.append(OscMessage(self._fmt_addr(f"/in/fvInCS+{channel_idx}/in/st"), [val]))
        if self.dialect in ("direct", "both"):
            msgs.append(OscMessage(self._fmt_addr(f"/input/{channel_idx + 1}/stereo"), [val]))
        return msgs

    def encode_input_mute(self, channel_idx: int, muted: bool) -> List[OscMessage]:
        msgs = []
        val = 1.0 if muted else 0.0
        if self.dialect in ("touchosc", "both"):
            msgs.append(OscMessage(self._fmt_addr(f"/in/fvInCS+{channel_idx}/in/mute"), [val]))
        if self.dialect in ("direct", "both"):
            msgs.append(OscMessage(self._fmt_addr(f"/input/{channel_idx + 1}/mute"), [val]))
        return msgs

    # ----------------- Encoding: Matrix Sends -----------------

    def encode_send_fader(self, bus_idx: int, channel_idx: int, norm_value: float) -> List[OscMessage]:
        msgs = []
        val = float(max(0.0, min(1.0, norm_value)))
        if self.dialect in ("touchosc", "both"):
            msgs.append(OscMessage(self._fmt_addr(f"/bin/fvEB+{bus_idx}/fvInCS+{channel_idx}/cdf"), [val]))
        if self.dialect in ("direct", "both"):
            msgs.append(OscMessage(self._fmt_addr(f"/mix/{bus_idx + 1}/input/{channel_idx + 1}/volume"), [val]))
        return msgs

    def encode_send_pan(self, bus_idx: int, channel_idx: int, norm_value: float) -> List[OscMessage]:
        msgs = []
        val = float(max(0.0, min(1.0, norm_value)))
        if self.dialect in ("touchosc", "both"):
            msgs.append(OscMessage(self._fmt_addr(f"/bin/fvEB+{bus_idx}/fvInCS+{channel_idx}/pan"), [val]))
        if self.dialect in ("direct", "both"):
            msgs.append(OscMessage(self._fmt_addr(f"/mix/{bus_idx + 1}/input/{channel_idx + 1}/pan"), [val]))
        return msgs

    def encode_send_mute(self, bus_idx: int, channel_idx: int, muted: bool) -> List[OscMessage]:
        msgs = []
        val = 1.0 if muted else 0.0
        if self.dialect in ("touchosc", "both"):
            msgs.append(OscMessage(self._fmt_addr(f"/bin/fvEB+{bus_idx}/fvInCS+{channel_idx}/mute"), [val]))
        if self.dialect in ("direct", "both"):
            msgs.append(OscMessage(self._fmt_addr(f"/mix/{bus_idx + 1}/input/{channel_idx + 1}/mute"), [val]))
        return msgs

    def encode_send_solo(self, bus_idx: int, channel_idx: int, soloed: bool) -> List[OscMessage]:
        msgs = []
        val = 1.0 if soloed else 0.0
        if self.dialect in ("touchosc", "both"):
            msgs.append(OscMessage(self._fmt_addr(f"/bin/fvEB+{bus_idx}/fvInCS+{channel_idx}/solo"), [val]))
        if self.dialect in ("direct", "both"):
            msgs.append(OscMessage(self._fmt_addr(f"/mix/{bus_idx + 1}/input/{channel_idx + 1}/solo"), [val]))
        return msgs

    # ----------------- Encoding: Bus Master & Global -----------------

    def encode_master_fader(self, bus_idx: int, norm_value: float) -> List[OscMessage]:
        msgs = []
        val = float(max(0.0, min(1.0, norm_value)))
        if self.dialect in ("touchosc", "both"):
            msgs.append(OscMessage(self._fmt_addr(f"/bus/fvEB+{bus_idx}/mix/blS"), [val]))
        if self.dialect in ("direct", "both"):
            msgs.append(OscMessage(self._fmt_addr(f"/mix/{bus_idx + 1}/master/volume"), [val]))
        return msgs

    def encode_master_mute(self, bus_idx: int, muted: bool) -> List[OscMessage]:
        msgs = []
        val = 1.0 if muted else 0.0
        if self.dialect in ("touchosc", "both"):
            msgs.append(OscMessage(self._fmt_addr(f"/bus/fvEB+{bus_idx}/mix/mute"), [val]))
        if self.dialect in ("direct", "both"):
            msgs.append(OscMessage(self._fmt_addr(f"/mix/{bus_idx + 1}/master/mute"), [val]))
        return msgs

    def encode_meters_toggle(self, enabled: bool) -> List[OscMessage]:
        val = 1.0 if enabled else 0.0
        return [OscMessage(self._fmt_addr("/metersToggle"), [val])]

    def encode_talkback(self, active: bool) -> List[OscMessage]:
        val = 1.0 if active else 0.0
        return [OscMessage(self._fmt_addr("/talkback"), [val])]

    def encode_listenback(self, active: bool) -> List[OscMessage]:
        val = 1.0 if active else 0.0
        return [OscMessage(self._fmt_addr("/listenback"), [val])]

    def encode_atten(self, norm_value: float) -> List[OscMessage]:
        return [OscMessage(self._fmt_addr("/atten"), [float(norm_value)])]

    # ----------------- Decoding Incoming OSC Messages -----------------

    def decode_message(self, message: OscMessage) -> Optional[Dict[str, Any]]:
        """
        Parses an incoming OSC message and returns a normalized dictionary:
        {
            'target': 'input_trim' | 'input_pad' | 'input_phase' | 'input_stereo' |
                      'input_mute' | 'send_fader' | 'send_pan' | 'send_mute' |
                      'send_solo' | 'master_fader' | 'master_mute' | 'meters' | ...
            'bus': bus_idx (0-based) or None,
            'channel': channel_idx (0-based) or None,
            'value': raw_value (float, bool, etc.)
        }
        """
        addr = message.address
        if self.prefix and addr.startswith(self.prefix):
            addr = addr[len(self.prefix):]

        args = message.args
        first_arg = args[0] if args else None

        # TouchOSC Dialect checks
        m = _RE_TOUCHOSC_SND_CDF.match(addr)
        if m:
            bus, ch = int(m.group(1)), int(m.group(2))
            return {"target": "send_fader", "bus": bus, "channel": ch, "value": float(first_arg or 0.0)}

        m = _RE_TOUCHOSC_SND_PAN.match(addr)
        if m:
            bus, ch = int(m.group(1)), int(m.group(2))
            return {"target": "send_pan", "bus": bus, "channel": ch, "value": float(first_arg or 0.5)}

        m = _RE_TOUCHOSC_SND_MUTE.match(addr)
        if m:
            bus, ch = int(m.group(1)), int(m.group(2))
            return {"target": "send_mute", "bus": bus, "channel": ch, "value": bool(first_arg)}

        m = _RE_TOUCHOSC_SND_SOLO.match(addr)
        if m:
            bus, ch = int(m.group(1)), int(m.group(2))
            return {"target": "send_solo", "bus": bus, "channel": ch, "value": bool(first_arg)}

        m = _RE_TOUCHOSC_BUS_MASTER.match(addr)
        if m:
            bus = int(m.group(1))
            return {"target": "master_fader", "bus": bus, "channel": None, "value": float(first_arg or 0.0)}

        m = _RE_TOUCHOSC_BUS_MUTE.match(addr)
        if m:
            bus = int(m.group(1))
            return {"target": "master_mute", "bus": bus, "channel": None, "value": bool(first_arg)}

        m = _RE_TOUCHOSC_IN_TRM.match(addr)
        if m:
            ch = int(m.group(1))
            return {"target": "input_trim", "bus": None, "channel": ch, "value": float(first_arg or 0.0)}

        m = _RE_TOUCHOSC_IN_PAD.match(addr)
        if m:
            ch = int(m.group(1))
            return {"target": "input_pad", "bus": None, "channel": ch, "value": bool(first_arg)}

        m = _RE_TOUCHOSC_IN_PSI.match(addr)
        if m:
            ch = int(m.group(1))
            return {"target": "input_phase", "bus": None, "channel": ch, "value": bool(first_arg)}

        m = _RE_TOUCHOSC_IN_ST.match(addr)
        if m:
            ch = int(m.group(1))
            return {"target": "input_stereo", "bus": None, "channel": ch, "value": bool(first_arg)}

        m = _RE_TOUCHOSC_IN_MUTE.match(addr)
        if m:
            ch = int(m.group(1))
            return {"target": "input_mute", "bus": None, "channel": ch, "value": bool(first_arg)}

        # Direct Hierarchical checks
        m = _RE_DIRECT_SND_VOL.match(addr)
        if m:
            bus, ch = int(m.group(1)) - 1, int(m.group(2)) - 1
            return {"target": "send_fader", "bus": bus, "channel": ch, "value": float(first_arg or 0.0)}

        m = _RE_DIRECT_SND_PAN.match(addr)
        if m:
            bus, ch = int(m.group(1)) - 1, int(m.group(2)) - 1
            return {"target": "send_pan", "bus": bus, "channel": ch, "value": float(first_arg or 0.5)}

        m = _RE_DIRECT_SND_MUTE.match(addr)
        if m:
            bus, ch = int(m.group(1)) - 1, int(m.group(2)) - 1
            return {"target": "send_mute", "bus": bus, "channel": ch, "value": bool(first_arg)}

        m = _RE_DIRECT_SND_SOLO.match(addr)
        if m:
            bus, ch = int(m.group(1)) - 1, int(m.group(2)) - 1
            return {"target": "send_solo", "bus": bus, "channel": ch, "value": bool(first_arg)}

        m = _RE_DIRECT_BUS_MASTER.match(addr)
        if m:
            bus = int(m.group(1)) - 1
            return {"target": "master_fader", "bus": bus, "channel": None, "value": float(first_arg or 0.0)}

        m = _RE_DIRECT_BUS_MUTE.match(addr)
        if m:
            bus = int(m.group(1)) - 1
            return {"target": "master_mute", "bus": bus, "channel": None, "value": bool(first_arg)}

        m = _RE_DIRECT_IN_TRM.match(addr)
        if m:
            ch = int(m.group(1)) - 1
            return {"target": "input_trim", "bus": None, "channel": ch, "value": float(first_arg or 0.0)}

        m = _RE_DIRECT_IN_PAD.match(addr)
        if m:
            ch = int(m.group(1)) - 1
            return {"target": "input_pad", "bus": None, "channel": ch, "value": bool(first_arg)}

        m = _RE_DIRECT_IN_PSI.match(addr)
        if m:
            ch = int(m.group(1)) - 1
            return {"target": "input_phase", "bus": None, "channel": ch, "value": bool(first_arg)}

        m = _RE_DIRECT_IN_ST.match(addr)
        if m:
            ch = int(m.group(1)) - 1
            return {"target": "input_stereo", "bus": None, "channel": ch, "value": bool(first_arg)}

        m = _RE_DIRECT_IN_MUTE.match(addr)
        if m:
            ch = int(m.group(1)) - 1
            return {"target": "input_mute", "bus": None, "channel": ch, "value": bool(first_arg)}

        # Meters
        if addr in ("/metersLED", "/meters", "/meter"):
            return {"target": "meters", "bus": None, "channel": None, "value": args}

        return None
