"""
Configuration Management for CuteMix.
Stores user settings, network ports, channel names, and interface profile.
"""

import json
import os
from typing import Dict, Any, Optional


def get_default_config_path() -> str:
    """Returns platform-appropriate config file path."""
    app_data = os.environ.get("APPDATA")
    if app_data:  # Windows
        conf_dir = os.path.join(app_data, "CuteMix")
    else:  # macOS / Linux
        home = os.path.expanduser("~")
        conf_dir = os.path.join(home, ".config", "cutemix")

    os.makedirs(conf_dir, exist_ok=True)
    return os.path.join(conf_dir, "config.json")


class AppConfig:
    """CuteMix application configuration."""

    def __init__(self):
        self.osc_target_host: str = "127.0.0.1"
        self.osc_target_port: int = 8000
        self.osc_listen_port: int = 9000
        self.osc_dialect: str = "touchosc"  # 'touchosc', 'direct', 'both'
        self.osc_prefix: str = ""

        self.interface_model: str = "24i"
        self.slot_letter: str = "A"
        self.num_channels: int = 24
        self.num_buses: int = 4
        self.active_bus: int = 0

        # Channel names dictionary: {channel_idx (str): custom_name (str)}
        self.channel_names: Dict[str, str] = {
            str(i): f"Analog {i + 1}" for i in range(24)
        }

        self.enable_zeroconf: bool = True
        self.zeroconf_name: str = "CuteMix 424 (TouchOSC)"
        self.auto_connect: bool = True

    def get_channel_name(self, idx: int) -> str:
        return self.channel_names.get(str(idx), f"Analog {idx + 1}")

    def set_channel_name(self, idx: int, name: str):
        self.channel_names[str(idx)] = name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "osc_target_host": self.osc_target_host,
            "osc_target_port": self.osc_target_port,
            "osc_listen_port": self.osc_listen_port,
            "osc_dialect": self.osc_dialect,
            "osc_prefix": self.osc_prefix,
            "interface_model": self.interface_model,
            "slot_letter": self.slot_letter,
            "num_channels": self.num_channels,
            "num_buses": self.num_buses,
            "active_bus": self.active_bus,
            "channel_names": self.channel_names,
            "enable_zeroconf": self.enable_zeroconf,
            "zeroconf_name": self.zeroconf_name,
            "auto_connect": self.auto_connect,
        }

    def from_dict(self, data: Dict[str, Any]):
        self.osc_target_host = data.get("osc_target_host", self.osc_target_host)
        self.osc_target_port = int(data.get("osc_target_port", self.osc_target_port))
        self.osc_listen_port = int(data.get("osc_listen_port", self.osc_listen_port))
        self.osc_dialect = data.get("osc_dialect", self.osc_dialect)
        self.osc_prefix = data.get("osc_prefix", self.osc_prefix)

        self.interface_model = data.get("interface_model", self.interface_model)
        self.slot_letter = data.get("slot_letter", self.slot_letter)
        self.num_channels = int(data.get("num_channels", self.num_channels))
        self.num_buses = int(data.get("num_buses", self.num_buses))
        self.active_bus = int(data.get("active_bus", self.active_bus))

        if "channel_names" in data and isinstance(data["channel_names"], dict):
            self.channel_names.update(data["channel_names"])

        self.enable_zeroconf = bool(data.get("enable_zeroconf", self.enable_zeroconf))
        self.zeroconf_name = data.get("zeroconf_name", self.zeroconf_name)
        self.auto_connect = bool(data.get("auto_connect", self.auto_connect))

    def load(self, path: Optional[str] = None) -> bool:
        path = path or get_default_config_path()
        if not os.path.exists(path):
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.from_dict(data)
            return True
        except Exception:
            return False

    def save(self, path: Optional[str] = None) -> bool:
        path = path or get_default_config_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2, sort_keys=True)
            return True
        except Exception:
            return False
