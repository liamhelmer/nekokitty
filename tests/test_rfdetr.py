import unittest

import numpy as np

from neko.rfdetr import (
    CentroidPersonTracker,
    PersonDetection,
    decode_people,
    preprocess_rgb,
)


class RFDETRTests(unittest.TestCase):
    def test_preprocess_contract(self):
        value = preprocess_rgb(np.zeros((10, 20, 3), dtype=np.uint8), size=16)
        self.assertEqual(value.shape, (1, 3, 16, 16))
        self.assertEqual(value.dtype, np.float32)
        self.assertAlmostEqual(float(value[0, 0, 0, 0]), -0.485 / 0.229, places=5)

    def test_decode_sparse_coco_person(self):
        boxes = np.zeros((1, 300, 4), dtype=np.float32)
        logits = np.full((1, 300, 91), -20.0, dtype=np.float32)
        boxes[0, 3] = (0.5, 0.5, 0.4, 0.6)
        logits[0, 3, 1] = 4.0
        logits[0, 4, 2] = 8.0
        people = decode_people(boxes, logits)
        self.assertEqual(len(people), 1)
        self.assertGreater(people[0].confidence, 0.98)
        np.testing.assert_allclose(
            people[0].xyxy_normalized, (0.3, 0.2, 0.7, 0.8), rtol=0, atol=1e-6
        )

    def test_tracker_preserves_nearby_identity(self):
        tracker = CentroidPersonTracker()
        first = PersonDetection(0.9, (0.1, 0.1, 0.3, 0.8))
        second = PersonDetection(0.8, (0.12, 0.1, 0.32, 0.8))
        first_id = tracker.update((first,))[0].track_id
        second_id = tracker.update((second,))[0].track_id
        self.assertEqual(first_id, second_id)


if __name__ == "__main__":
    unittest.main()
