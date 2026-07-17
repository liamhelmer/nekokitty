from __future__ import annotations

from io import BytesIO
import json
import threading
import unittest
from unittest.mock import patch

from neko.tts_protocol import MAX_AUDIO_BYTES, TtsClient, read_exact, read_json, write_json


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

    @patch("neko.tts_protocol.subprocess.Popen")
    def test_pre_cancelled_playback_starts_no_player(self, popen: object) -> None:
        cancelled = threading.Event()
        cancelled.set()
        result = TtsClient().synthesize("Stop now.", play=True, cancel_event=cancelled)
        self.assertTrue(result["cancelled"])
        popen.assert_not_called()

    @patch("neko.tts_protocol.subprocess.Popen")
    @patch("neko.tts_protocol.socket.socket")
    def test_player_uses_worker_announced_sample_rate(
        self,
        socket_factory: object,
        popen: object,
    ) -> None:
        class Duplex:
            def __init__(self) -> None:
                self.lines = [
                    json.dumps(
                        {
                            "event": "start",
                            "sample_rate": 22_050,
                            "sample_format": "s16le",
                        }
                    ).encode()
                    + b"\n",
                    b'{"event":"audio","bytes":4}\n',
                    b'{"event":"complete","sample_rate":22050}\n',
                ]
                self.audio = BytesIO(b"\x01\x02\x03\x04")

            def write(self, data: bytes) -> int:
                return len(data)

            def flush(self) -> None:
                return None

            def readline(self, _size: int = -1) -> bytes:
                return self.lines.pop(0) if self.lines else b""

            def read(self, count: int) -> bytes:
                return self.audio.read(count)

        class Connected:
            def __init__(self) -> None:
                self.stream = Duplex()

            def __enter__(self) -> "Connected":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def settimeout(self, _timeout: float) -> None:
                return None

            def connect(self, _path: str) -> None:
                return None

            def makefile(self, _mode: str, buffering: int = 0) -> Duplex:
                return self.stream

        class FakePlayer:
            def __init__(self) -> None:
                self.stdin = BytesIO()
                self.returncode = 0

            def wait(self, timeout: float | None = None) -> int:
                return 0

        socket_factory.return_value = Connected()
        popen.return_value = FakePlayer()
        first_pcm: list[bool] = []
        result = TtsClient().synthesize(
            "Hi!",
            play=True,
            on_first_pcm=lambda: first_pcm.append(True),
        )

        self.assertEqual(result["sample_rate"], 22_050)
        self.assertEqual(first_pcm, [True])
        command = popen.call_args.args[0]
        self.assertIn("--rate=22050", command)


if __name__ == "__main__":
    unittest.main()
