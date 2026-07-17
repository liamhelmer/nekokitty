"""Small bounded Unix-socket protocol for Neko's resident TTS worker."""

from __future__ import annotations

import json
from pathlib import Path
import socket
import subprocess
import threading
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
        cancel_event: threading.Event | None = None,
    ) -> dict[str, Any]:
        if not text.strip():
            raise ValueError("TTS text must not be empty")
        if output is None and not play:
            raise ValueError("select output, playback, or both")

        if cancel_event is not None and cancel_event.is_set():
            return {"event": "cancelled", "cancelled": True}

        player: subprocess.Popen[bytes] | None = None
        wav_file: wave.Wave_write | None = None
        client: socket.socket | None = None
        state_lock = threading.Lock()
        watcher_done = threading.Event()
        watcher: threading.Thread | None = None
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
        cancelled = False
        terminal = False

        def state() -> tuple[bool, bool]:
            with state_lock:
                return cancelled, terminal

        def stop_player(candidate: subprocess.Popen[bytes] | None) -> None:
            if candidate is None or candidate.poll() is not None:
                return
            candidate.terminate()
            try:
                candidate.wait(timeout=0.25)
            except subprocess.TimeoutExpired:
                candidate.kill()
                candidate.wait(timeout=1)

        def cancel_playback() -> None:
            """Stop both queued audio and a blocked worker read on barge-in."""

            nonlocal cancelled
            assert cancel_event is not None
            while not watcher_done.is_set():
                if not cancel_event.wait(0.02):
                    continue
                with state_lock:
                    if terminal:
                        return
                    cancelled = True
                    candidate_player = player
                    candidate_client = client
                stop_player(candidate_player)
                if candidate_client is not None:
                    try:
                        candidate_client.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                return

        if cancel_event is not None:
            watcher = threading.Thread(
                target=cancel_playback,
                name="neko-tts-cancel",
                daemon=True,
            )
            watcher.start()
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connected:
                with state_lock:
                    client = connected
                    cancel_before_connect = cancelled
                if cancel_before_connect:
                    return {"event": "cancelled", "cancelled": True}
                client.settimeout(self.timeout_s)
                client.connect(str(self.socket_path))
                if state()[0]:
                    return {"event": "cancelled", "cancelled": True}
                stream = client.makefile("rwb", buffering=0)
                write_json(stream, {"text": text})
                while True:
                    if state()[0]:
                        break
                    event = read_json(stream)
                    kind = event.get("event")
                    if kind == "audio":
                        pcm = read_exact(stream, int(event.get("bytes", -1)))
                        if state()[0]:
                            break
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
        except (BrokenPipeError, ConnectionError, EOFError, OSError):
            if not state()[0]:
                raise
        finally:
            if wav_file is not None:
                wav_file.close()
            if player is not None:
                with state_lock:
                    if (
                        cancel_event is not None
                        and cancel_event.is_set()
                        and not terminal
                    ):
                        cancelled = True
                was_cancelled = state()[0]
                if was_cancelled:
                    stop_player(player)
                elif player.stdin is not None:
                    try:
                        player.stdin.close()
                    except BrokenPipeError:
                        pass
                if not was_cancelled:
                    try:
                        return_code = player.wait(timeout=self.timeout_s)
                    except subprocess.TimeoutExpired:
                        stop_player(player)
                        raise RuntimeError("PipeWire playback did not stop")
                else:
                    return_code = player.returncode
                if return_code and result is not None and not was_cancelled:
                    raise RuntimeError(f"PipeWire playback exited {return_code}")
            with state_lock:
                terminal = True
            watcher_done.set()
            if watcher is not None:
                watcher.join(timeout=0.2)
        if state()[0]:
            return {"event": "cancelled", "cancelled": True}
        if result is None:
            raise RuntimeError("TTS worker returned no completion event")
        return result
