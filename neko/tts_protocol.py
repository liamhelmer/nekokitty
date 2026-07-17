"""Small bounded Unix-socket protocol for Neko's resident TTS worker."""

from __future__ import annotations

import json
from pathlib import Path
import socket
import subprocess
import wave
from typing import Any, BinaryIO


DEFAULT_SOCKET = Path("/run/neko/tts.sock")
MAX_HEADER_BYTES = 64 * 1024
MAX_AUDIO_BYTES = 32 * 1024 * 1024


def write_json(stream: BinaryIO, value: dict[str, Any]) -> None:
    stream.write(json.dumps(value, separators=(",", ":")).encode("utf-8") + b"\n")
    stream.flush()


def read_json(stream: BinaryIO) -> dict[str, Any]:
    line = stream.readline(MAX_HEADER_BYTES + 1)
    if not line:
        raise EOFError("TTS worker closed the connection")
    if len(line) > MAX_HEADER_BYTES:
        raise RuntimeError("TTS protocol header exceeds its bound")
    value = json.loads(line)
    if not isinstance(value, dict):
        raise RuntimeError("TTS protocol header is not an object")
    return value


def read_exact(stream: BinaryIO, count: int) -> bytes:
    if not 0 <= count <= MAX_AUDIO_BYTES:
        raise RuntimeError("TTS audio frame exceeds its bound")
    parts: list[bytes] = []
    remaining = count
    while remaining:
        part = stream.read(remaining)
        if not part:
            raise EOFError("TTS worker truncated an audio frame")
        parts.append(part)
        remaining -= len(part)
    return b"".join(parts)


class TtsClient:
    """Receive sentence-sized PCM frames and optionally play them immediately."""

    def __init__(self, socket_path: Path = DEFAULT_SOCKET, timeout_s: float = 60.0):
        self.socket_path = socket_path
        self.timeout_s = timeout_s

    def synthesize(
        self,
        text: str,
        *,
        output: Path | None = None,
        play: bool = False,
    ) -> dict[str, Any]:
        if not text.strip():
            raise ValueError("TTS text must not be empty")
        if output is None and not play:
            raise ValueError("select output, playback, or both")

        player: subprocess.Popen[bytes] | None = None
        wav_file: wave.Wave_write | None = None
        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)
            wav_file = wave.open(str(output), "wb")
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(24_000)
        if play:
            player = subprocess.Popen(
                [
                    "/usr/bin/pw-cat",
                    "--playback",
                    "--rate=24000",
                    "--channels=1",
                    "--channel-map=MONO",
                    "--format=s16",
                    "-",
                ],
                stdin=subprocess.PIPE,
            )

        result: dict[str, Any] | None = None
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(self.timeout_s)
                client.connect(str(self.socket_path))
                stream = client.makefile("rwb", buffering=0)
                write_json(stream, {"text": text})
                while True:
                    event = read_json(stream)
                    kind = event.get("event")
                    if kind == "audio":
                        pcm = read_exact(stream, int(event.get("bytes", -1)))
                        if wav_file is not None:
                            wav_file.writeframesraw(pcm)
                        if player is not None and player.stdin is not None:
                            player.stdin.write(pcm)
                            player.stdin.flush()
                    elif kind == "complete":
                        result = event
                        break
                    elif kind == "error":
                        raise RuntimeError(str(event.get("message", "TTS worker failed")))
                    elif kind == "start":
                        if event.get("sample_rate") != 24_000:
                            raise RuntimeError("TTS worker returned an unsupported sample rate")
                        if event.get("sample_format") != "s16le":
                            raise RuntimeError("TTS worker returned an unsupported sample format")
                    else:
                        raise RuntimeError(f"unknown TTS protocol event: {kind!r}")
        finally:
            if wav_file is not None:
                wav_file.close()
            if player is not None:
                if player.stdin is not None:
                    player.stdin.close()
                return_code = player.wait(timeout=self.timeout_s)
                if return_code and result is not None:
                    raise RuntimeError(f"PipeWire playback exited {return_code}")
        if result is None:
            raise RuntimeError("TTS worker returned no completion event")
        return result
