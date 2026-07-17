from __future__ import annotations

import unittest

from neko.proximity import DetectorTrack, GroundPlaneCalibration, ProximityEstimator


class CalibrationTests(unittest.TestCase):
    def test_piecewise_interpolation_and_range(self) -> None:
        calibration = GroundPlaneCalibration(((0.4, 3.05), (0.7, 1.8), (0.9, 1.2)))
        self.assertAlmostEqual(calibration.estimate_m(0.55), 2.425)
        self.assertIsNone(calibration.estimate_m(0.2))

    def test_rejects_unsorted_calibration(self) -> None:
        with self.assertRaises(ValueError):
            GroundPlaneCalibration(((0.8, 1.0), (0.4, 3.0)))


class ProximityEstimatorTests(unittest.TestCase):
    def detection(self, at: float, bottom: float) -> DetectorTrack:
        return DetectorTrack("bench", "temporary-1", 0.9, at, bottom)

    def test_approach_requires_stable_distance_decrease(self) -> None:
        estimator = ProximityEstimator(
            {"bench": GroundPlaneCalibration(((0.4, 3.2), (0.9, 1.0)))},
            approach_delta_m=0.25,
        )
        self.assertFalse(estimator.observe(self.detection(1.0, 0.5)).approaching)
        self.assertFalse(estimator.observe(self.detection(2.0, 0.6)).approaching)
        event = estimator.observe(self.detection(3.0, 0.7))
        self.assertTrue(event.approaching)
        self.assertEqual(event.stable_observations, 3)
        self.assertEqual(event.dwell_s, 2.0)
        self.assertEqual(event.bottom_y_normalized, 0.7)

    def test_expiry_emits_media_free_gone_event(self) -> None:
        estimator = ProximityEstimator(
            {"bench": GroundPlaneCalibration(((0.4, 3.2), (0.9, 1.0)))},
            stale_after_s=2.0,
        )
        estimator.observe(self.detection(1.0, 0.5))
        self.assertEqual(estimator.expire(2.0), ())
        gone = estimator.expire(3.0)
        self.assertEqual((gone[0].camera_id, gone[0].track_id), ("bench", "temporary-1"))


if __name__ == "__main__":
    unittest.main()
