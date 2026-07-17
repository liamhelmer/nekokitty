from __future__ import annotations

from io import BytesIO
import unittest

from neko.tts_protocol import MAX_AUDIO_BYTES, read_exact, read_json, write_json


class TtsProtocolTests(unittest.TestCase):
    def test_json_header_and_binary_frame_remain_separate(self) -> None:
        stream = BytesIO()
        write_json(stream, {"event": "audio", "bytes": 4})
        stream.write(b"\x01\x02\x03\x04")
        stream.seek(0)
        self.assertEqual(read_json(stream), {"event": "audio", "bytes": 4})
        self.assertEqual(read_exact(stream, 4), b"\x01\x02\x03\x04")

    def test_truncated_frame_fails_closed(self) -> None:
        with self.assertRaises(EOFError):
            read_exact(BytesIO(b"ab"), 3)

    def test_oversized_frame_fails_closed(self) -> None:
        with self.assertRaises(RuntimeError):
            read_exact(BytesIO(), MAX_AUDIO_BYTES + 1)

    def test_non_object_header_is_rejected(self) -> None:
        with self.assertRaises(RuntimeError):
            read_json(BytesIO(b"[]\n"))


if __name__ == "__main__":
    unittest.main()
