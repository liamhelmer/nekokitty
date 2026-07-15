from __future__ import annotations

from array import array
import sys
import unittest

from scripts.neko_asr_transcribe import pcm16_to_float


class AsrHelperTests(unittest.TestCase):
    def test_pcm16_normalization(self) -> None:
        values = array("h", [-32768, 0, 16384, 32767])
        if sys.byteorder != "little":
            values.byteswap()
        samples = pcm16_to_float(values.tobytes())
        self.assertEqual(samples[:3], [-1.0, 0.0, 0.5])
        self.assertAlmostEqual(samples[3], 32767 / 32768)


if __name__ == "__main__":
    unittest.main()
