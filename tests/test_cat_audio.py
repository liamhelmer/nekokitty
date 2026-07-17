from __future__ import annotations

import math
import unittest

from neko.cat_audio import db_to_linear, peak_limited_gain_db, playback_multiplier


class CatAudioNormalizationTests(unittest.TestCase):
    def test_db_conversion(self) -> None:
        self.assertAlmostEqual(db_to_linear(0.0), 1.0)
        self.assertAlmostEqual(db_to_linear(20.0), 10.0)

    def test_quiet_source_retains_replaygain_correction(self) -> None:
        applied = peak_limited_gain_db(12.28, 0.05584717, 0.35)
        self.assertAlmostEqual(applied, 12.28)

    def test_peak_heavy_source_is_limited(self) -> None:
        multiplier, applied, peak = playback_multiplier(13.81, 0.99267578, 0.35)
        self.assertLess(applied, 13.81)
        self.assertAlmostEqual(peak, 10 ** (-1.0 / 20.0))
        self.assertGreater(multiplier, 0.0)

    def test_invalid_peak_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            peak_limited_gain_db(1.0, 0.0, 0.35)
        with self.assertRaises(ValueError):
            peak_limited_gain_db(1.0, math.inf, 0.35)


if __name__ == "__main__":
    unittest.main()
