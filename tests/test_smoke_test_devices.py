from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


SCRIPT = Path(__file__).parents[1] / "scripts" / "smoke_test_devices.py"
SPEC = importlib.util.spec_from_file_location("smoke_test_devices", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ParseAlsaDevicesTests(unittest.TestCase):
    def test_parse_usb_capture(self) -> None:
        output = """**** List of CAPTURE Hardware Devices ****
card 2: Webcam [C922 Pro Stream Webcam], device 0: USB Audio [USB Audio]
  Subdevices: 1/1
"""
        devices = MODULE.parse_alsa_devices(output, "capture")
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].card, 2)
        self.assertEqual(devices[0].card_id, "Webcam")
        self.assertEqual(devices[0].spec, "plughw:CARD=Webcam,DEV=0")

    def test_ignores_headers_and_subdevice_lines(self) -> None:
        output = """**** List of PLAYBACK Hardware Devices ****
card 0: HDA [NVIDIA Jetson Orin Nano HDA], device 3: HDMI 0 [HDMI 0]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
"""
        devices = MODULE.parse_alsa_devices(output, "playback")
        self.assertEqual([device.device for device in devices], [3])


class ArgumentTests(unittest.TestCase):
    def test_default_run_is_not_audible(self) -> None:
        args = MODULE.build_parser().parse_args([])
        self.assertEqual(args.command, "all")
        self.assertFalse(args.audible)

    def test_rejects_high_test_volume(self) -> None:
        args = MODULE.build_parser().parse_args(["playback", "--volume", "0.5"])
        with self.assertRaisesRegex(ValueError, "no more than 0.1"):
            MODULE.validate_args(args)


class ResultTests(unittest.TestCase):
    def test_rms_pattern_matches_gstreamer_level_message(self) -> None:
        message = (
            "level, rms=(GValueArray)< -42.73949439776851 >, "
            "peak=(GValueArray)< -29.2 >;"
        )
        self.assertEqual(MODULE.RMS_PATTERN.findall(message), ["-42.73949439776851"])

    def test_rms_pattern_accepts_digital_silence(self) -> None:
        self.assertEqual(
            MODULE.RMS_PATTERN.findall("rms=(GValueArray)< -inf >"), ["-inf"]
        )

    def test_skipped_optional_device_is_not_failure(self) -> None:
        results = {
            "synthetic": {"ok": True},
            "camera": {"ok": False, "skipped": True},
        }
        self.assertTrue(MODULE.overall_ok(results))

    def test_skipped_required_device_is_failure(self) -> None:
        results = {"playback": {"ok": False, "skipped": True}}
        self.assertFalse(MODULE.overall_ok(results, frozenset({"playback"})))

    def test_real_failure_fails_run(self) -> None:
        self.assertFalse(MODULE.overall_ok({"gemma": {"ok": False}}))


if __name__ == "__main__":
    unittest.main()
