"""
Unit Tests for CuteMix Model (State, Config, Linking, Undo/Redo).
"""

import os
import tempfile
import unittest
from cutemix.model.config import AppConfig
from cutemix.model.mixer_state import MixerState


class TestMixerModel(unittest.TestCase):
    def setUp(self):
        self.config = AppConfig()
        self.state = MixerState(self.config)

    def test_initial_state(self):
        self.assertEqual(self.state.num_channels, 24)
        self.assertEqual(self.state.num_buses, 4)
        self.assertEqual(self.state.active_bus_idx, 0)

        # Check default faders at Unity (0.78)
        for b in range(self.state.num_buses):
            self.assertAlmostEqual(self.state.buses[b].master_fader_norm, 0.78, places=2)
            for ch in range(self.state.num_channels):
                self.assertAlmostEqual(self.state.buses[b].sends[ch].fader_norm, 0.78, places=2)
                self.assertAlmostEqual(self.state.buses[b].sends[ch].pan_norm, 0.5, places=2)
                self.assertFalse(self.state.buses[b].sends[ch].mute)
                self.assertFalse(self.state.buses[b].sends[ch].solo)

    def test_stereo_link(self):
        # Link channel 4 and 5
        affected = self.state.set_stereo_link(4, True)
        self.assertIn(4, affected)
        self.assertIn(5, affected)
        self.assertTrue(self.state.inputs[4].stereo_link)
        self.assertTrue(self.state.inputs[5].stereo_link)

        # Pan should auto-spread Left and Right
        self.assertEqual(self.state.buses[0].sends[4].pan_norm, 0.0)
        self.assertEqual(self.state.buses[0].sends[5].pan_norm, 1.0)

        # Moving fader 4 should move fader 5
        self.state.set_send_fader(0, 4, 0.60)
        self.assertAlmostEqual(self.state.buses[0].sends[5].fader_norm, 0.60)

        # Muting 4 should mute 5
        self.state.set_send_mute(0, 4, True)
        self.assertTrue(self.state.buses[0].sends[5].mute)

    def test_gang_grouping(self):
        # Set channels 0, 1, 2 into gang group
        self.state.buses[0].sends[0].gang = True
        self.state.buses[0].sends[1].gang = True
        self.state.buses[0].sends[2].gang = True

        # Initial faders: 0.78
        # Move channel 0 by +0.10
        self.state.set_send_fader(0, 0, 0.88)
        self.assertAlmostEqual(self.state.buses[0].sends[1].fader_norm, 0.88, places=2)
        self.assertAlmostEqual(self.state.buses[0].sends[2].fader_norm, 0.88, places=2)

    def test_undo_redo(self):
        self.assertFalse(self.state.can_undo())
        self.assertFalse(self.state.can_redo())

        # Step 1
        self.state.set_send_fader(0, 0, 0.95)
        self.state.push_history("Step 1")
        self.assertTrue(self.state.can_undo())

        # Step 2
        self.state.set_send_fader(0, 0, 0.30)
        self.state.push_history("Step 2")

        self.assertAlmostEqual(self.state.buses[0].sends[0].fader_norm, 0.30)

        # Undo to Step 1
        self.assertTrue(self.state.undo())
        self.assertAlmostEqual(self.state.buses[0].sends[0].fader_norm, 0.95)
        self.assertTrue(self.state.can_redo())

        # Redo to Step 2
        self.assertTrue(self.state.redo())
        self.assertAlmostEqual(self.state.buses[0].sends[0].fader_norm, 0.30)

    def test_snapshot_file_roundtrip(self):
        # Customize some values
        self.state.buses[0].sends[7].fader_norm = 0.42
        self.state.inputs[3].trim_norm = 0.65
        self.state.inputs[3].pad = True

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            tmp_path = tf.name

        try:
            self.assertTrue(self.state.save_snapshot_file(tmp_path))

            # New state to load into
            new_state = MixerState(self.config)
            self.assertNotEqual(new_state.buses[0].sends[7].fader_norm, 0.42)

            self.assertTrue(new_state.load_snapshot_file(tmp_path))
            self.assertAlmostEqual(new_state.buses[0].sends[7].fader_norm, 0.42)
            self.assertAlmostEqual(new_state.inputs[3].trim_norm, 0.65)
            self.assertTrue(new_state.inputs[3].pad)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
