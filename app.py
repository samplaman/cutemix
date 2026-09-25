#!/usr/bin/env python3
"""
CuteMix - MOTU PCIe-424 + 24i Mixer Console over OSC
Main Application Entry Point.
"""

import argparse
import os
import random
import sys

from cutemix.qt_compat import QtWidgets, QtCore, is_qt_available, get_qt_lib
from cutemix.model.config import AppConfig


def check_qt_installed():
    """Checks if a supported Qt binding is installed. If not, provides instructions."""
    if not is_qt_available():
        sys.stderr.write(
            "\n"
            "====================================================================\n"
            "  CuteMix Error: No Qt binding found (PySide6 or PyQt6 required)\n"
            "====================================================================\n"
            "\n"
            "To install the required dependencies on Windows or macOS/Linux, run:\n\n"
            "    pip install PySide6\n"
            "    or\n"
            "    pip install -r requirements.txt\n"
            "\n"
            "====================================================================\n"
        )
        sys.exit(1)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="CuteMix - Qt Python app for managing MOTU PCIe-424 with 24i over OSC"
    )
    parser.add_argument(
        "--host", type=str, default=None,
        help="Target host running MOTU CueMix FX (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--target-port", type=int, default=None,
        help="OSC send port where CueMix FX listens (default: 8000)"
    )
    parser.add_argument(
        "--listen-port", type=int, default=None,
        help="OSC receive port where CuteMix listens (default: 9000)"
    )
    parser.add_argument(
        "--dialect", type=str, choices=["touchosc", "direct", "both"], default=None,
        help="OSC address format dialect (default: touchosc)"
    )
    parser.add_argument(
        "--demo", action="store_true",
        help="Run in demo simulation mode with synthetic meter activity"
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    check_qt_installed()

    # Import main window only after Qt availability is confirmed
    from cutemix.main_window import CuteMixMainWindow

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("CuteMix")
    app.setApplicationDisplayName("CuteMix - MOTU PCIe-424")

    # Load configuration
    config = AppConfig()
    config.load()

    # Command line overrides
    if args.host:
        config.osc_target_host = args.host
    if args.target_port:
        config.osc_target_port = args.target_port
    if args.listen_port:
        config.osc_listen_port = args.listen_port
    if args.dialect:
        config.osc_dialect = args.dialect

    window = CuteMixMainWindow(config)
    window.show()

    # Demo simulation timer if requested
    if args.demo:
        demo_timer = QtCore.QTimer(window)
        demo_timer.setInterval(80)

        def _on_demo_tick():
            # Generate subtle synthetic meter pulses for input channels
            for ch in range(config.num_channels):
                # Simulated noise floor / occasional peaks
                base = random.uniform(0.05, 0.45)
                if random.random() < 0.08:
                    base = random.uniform(0.65, 0.92)
                fader = window.state.get_active_bus().sends[ch].fader_norm
                mute = window.state.get_active_bus().sends[ch].mute
                level = 0.0 if mute else (base * fader)
                if ch in window.view_mixer.strips:
                    window.view_mixer.strips[ch].setMeterLevel(level)
                if ch in window.view_inputs.cards:
                    window.view_inputs.cards[ch].meter.setLevel(level)

            # Master meter
            ml = random.uniform(0.15, 0.65)
            mr = random.uniform(0.15, 0.65)
            master_fader = window.state.get_active_bus().master_fader_norm
            master_mute = window.state.get_active_bus().master_mute
            if master_mute:
                window.view_mixer.master_strip.setStereoLevels(0.0, 0.0)
            else:
                window.view_mixer.master_strip.setStereoLevels(ml * master_fader, mr * master_fader)

        demo_timer.timeout.connect(_on_demo_tick)
        demo_timer.start()
        window.status_bar.showMessage("CuteMix running in DEMO mode (synthetic audio meters active)", 5000)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
