from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from neko.story_recording_rebuild import enqueue_story_rebuild


class StoryRecordingRebuildTests(unittest.TestCase):
    def test_enqueue_is_atomic_and_deduplicated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = enqueue_story_rebuild(
                "original.luna-stick-garden",
                "stale_source",
                queue_root=root,
                launch=False,
            )
            second = enqueue_story_rebuild(
                "original.luna-stick-garden",
                "duplicate",
                queue_root=root,
                launch=False,
            )
            self.assertTrue(first)
            self.assertFalse(second)
            requests = list(root.glob("request-*.json"))
            self.assertEqual(len(requests), 1)
            request = json.loads(requests[0].read_text(encoding="utf-8"))
            self.assertEqual(request["story_id"], "original.luna-stick-garden")
            self.assertEqual(request["reason"], "stale_source")
            self.assertEqual(requests[0].stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
