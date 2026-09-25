"""
Unit Tests for OSC Core & CueMix FX Protocol.
"""

import unittest
from cutemix.osc.osc_core import (
    OscMessage,
    OscBundle,
    decode_packet,
    encode_string,
    decode_string,
    encode_blob,
    decode_blob,
)
from cutemix.osc.cuemix_protocol import (
    CueMixProtocol,
    norm_to_db,
    db_to_norm,
    norm_to_pan,
    pan_to_norm,
    norm_to_trim,
    trim_to_norm,
)


class TestOscCore(unittest.TestCase):
    def test_string_encoding(self):
        s = "test"
        enc = encode_string(s)
        self.assertEqual(len(enc) % 4, 0)
        dec, offset = decode_string(enc)
        self.assertEqual(dec, s)
        self.assertEqual(offset, len(enc))

    def test_blob_encoding(self):
        blob = b"\x01\x02\x03\x04\x05"
        enc = encode_blob(blob)
        self.assertEqual(len(enc) % 4, 0)
        dec, offset = decode_blob(enc)
        self.assertEqual(dec, blob)

    def test_message_roundtrip(self):
        msg = OscMessage("/test/path", [42, 3.14159, "hello", True, False])
        raw = msg.encode()
        self.assertEqual(len(raw) % 4, 0)
        decoded = decode_packet(raw)
        self.assertIsInstance(decoded, OscMessage)
        self.assertEqual(decoded.address, "/test/path")
        self.assertEqual(decoded.args[0], 42)
        self.assertAlmostEqual(decoded.args[1], 3.14159, places=4)
        self.assertEqual(decoded.args[2], "hello")
        self.assertEqual(decoded.args[3], True)
        self.assertEqual(decoded.args[4], False)

    def test_bundle_roundtrip(self):
        m1 = OscMessage("/ch/1", [0.5])
        m2 = OscMessage("/ch/2", [0.75])
        bundle = OscBundle(timetag=1.0, elements=[m1, m2])
        raw = bundle.encode()
        decoded = decode_packet(raw)
        self.assertIsInstance(decoded, OscBundle)
        self.assertEqual(len(decoded.elements), 2)
        self.assertEqual(decoded.elements[0].address, "/ch/1")
        self.assertEqual(decoded.elements[1].address, "/ch/2")


class TestCueMixProtocol(unittest.TestCase):
    def setUp(self):
        self.proto_touchosc = CueMixProtocol(dialect="touchosc")
        self.proto_direct = CueMixProtocol(dialect="direct")
        self.proto_both = CueMixProtocol(dialect="both")

    def test_send_fader_touchosc(self):
        # Channel 3, Bus 1
        msgs = self.proto_touchosc.encode_send_fader(1, 3, 0.85)
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].address, "/bin/fvEB+1/fvInCS+3/cdf")
        self.assertAlmostEqual(msgs[0].args[0], 0.85, places=5)

        dec = self.proto_touchosc.decode_message(msgs[0])
        self.assertIsNotNone(dec)
        self.assertEqual(dec["target"], "send_fader")
        self.assertEqual(dec["bus"], 1)
        self.assertEqual(dec["channel"], 3)
        self.assertAlmostEqual(dec["value"], 0.85, places=5)

    def test_send_fader_direct(self):
        msgs = self.proto_direct.encode_send_fader(0, 0, 0.78)
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].address, "/mix/1/input/1/volume")

        dec = self.proto_direct.decode_message(msgs[0])
        self.assertEqual(dec["target"], "send_fader")
        self.assertEqual(dec["bus"], 0)
        self.assertEqual(dec["channel"], 0)

    def test_send_pan(self):
        msgs = self.proto_touchosc.encode_send_pan(0, 5, 0.25)
        self.assertEqual(msgs[0].address, "/bin/fvEB+0/fvInCS+5/pan")
        dec = self.proto_touchosc.decode_message(msgs[0])
        self.assertEqual(dec["target"], "send_pan")
        self.assertEqual(dec["channel"], 5)
        self.assertAlmostEqual(dec["value"], 0.25)

    def test_input_trim_pad_phase_stereo_mute(self):
        # Trim
        t_msg = self.proto_touchosc.encode_input_trim(2, 0.5)[0]
        self.assertEqual(t_msg.address, "/in/fvInCS+2/in/trm")
        self.assertEqual(self.proto_touchosc.decode_message(t_msg)["target"], "input_trim")

        # Pad
        pad_msg = self.proto_touchosc.encode_input_pad(2, True)[0]
        self.assertEqual(pad_msg.address, "/in/fvInCS+2/in/pad")
        self.assertEqual(self.proto_touchosc.decode_message(pad_msg)["target"], "input_pad")

        # Phase
        psi_msg = self.proto_touchosc.encode_input_phase(2, True)[0]
        self.assertEqual(psi_msg.address, "/in/fvInCS+2/in/psi")
        self.assertEqual(self.proto_touchosc.decode_message(psi_msg)["target"], "input_phase")

        # Stereo
        st_msg = self.proto_touchosc.encode_input_stereo(2, True)[0]
        self.assertEqual(st_msg.address, "/in/fvInCS+2/in/st")
        self.assertEqual(self.proto_touchosc.decode_message(st_msg)["target"], "input_stereo")

        # Mute
        m_msg = self.proto_touchosc.encode_input_mute(2, True)[0]
        self.assertEqual(m_msg.address, "/in/fvInCS+2/in/mute")
        self.assertEqual(self.proto_touchosc.decode_message(m_msg)["target"], "input_mute")

    def test_master_fader_and_mute(self):
        m_fader = self.proto_touchosc.encode_master_fader(0, 0.90)[0]
        self.assertEqual(m_fader.address, "/bus/fvEB+0/mix/blS")
        dec = self.proto_touchosc.decode_message(m_fader)
        self.assertEqual(dec["target"], "master_fader")
        self.assertEqual(dec["bus"], 0)

        m_mute = self.proto_touchosc.encode_master_mute(0, True)[0]
        self.assertEqual(m_mute.address, "/bus/fvEB+0/mix/mute")
        self.assertEqual(self.proto_touchosc.decode_message(m_mute)["target"], "master_mute")

    def test_conversion_helpers(self):
        # 0 dB Unity
        self.assertAlmostEqual(norm_to_db(0.78), 0.0, delta=0.2)
        self.assertAlmostEqual(db_to_norm(0.0), 0.78, delta=0.05)

        # Pan
        self.assertEqual(norm_to_pan(0.5), 0)
        self.assertEqual(norm_to_pan(0.0), -100)
        self.assertEqual(norm_to_pan(1.0), 100)
        self.assertAlmostEqual(pan_to_norm(0), 0.5)

        # Trim
        self.assertEqual(norm_to_trim(0.0), 0.0)
        self.assertEqual(norm_to_trim(1.0, max_trim_db=24.0), 24.0)
        self.assertEqual(trim_to_norm(12.0, max_trim_db=24.0), 0.5)


if __name__ == "__main__":
    unittest.main()
