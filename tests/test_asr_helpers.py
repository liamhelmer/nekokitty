from __future__ import annotations

from array import array
import sys
import unittest

from scripts.neko_asr_transcribe import capture_pipewire, pcm16_to_float, pcm_levels_db


class AsrHelperTests(unittest.TestCase):
    def test_pcm16_normalization(self) -> None:
        values = array("h", [-32768, 0, 16384, 32767])
        if sys.byteorder != "little":
            values.byteswap()
        samples = pcm16_to_float(values.tobytes())
        self.assertEqual(samples[:3], [-1.0, 0.0, 0.5])
        self.assertAlmostEqual(samples[3], 32767 / 32768)

    def test_pcm_levels(self) -> None:
        rms_db, peak_db = pcm_levels_db([0.5, -0.5])
        self.assertAlmostEqual(rms_db, -6.0206, places=3)
        self.assertAlmostEqual(peak_db, -6.0206, places=3)
        self.assertEqual(pcm_levels_db([0.0, 0.0]), (None, None))

    def test_pipewire_capture_rejects_nonpositive_duration(self) -> None:
        with self.assertRaises(ValueError):
            capture_pipewire(0)


if __name__ == "__main__":
    unittest.main()
