#!/usr/bin/env python3
"""Serve pinned low-latency Piper sentence audio over Neko's Unix protocol."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import socket
import socketserver
import sys
import time

from piper import PiperVoice

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neko.tts_protocol import MAX_HEADER_BYTES, write_json  # noqa: E402


DEFAULT_SOCKET = Path("/run/neko/tts-fast.sock")
DEFAULT_MODEL = Path(
    "/home/neko/models/piper-voices/"
    "82999b670b06c78cabeb830d535b63a31cd0ca22/"
    "en_US-lessac-medium/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
)
DEFAULT_MODEL_SHA256 = "5efe09e69902187827af646e1a6e9d269dee769f9877d17b16b1b46eeaaf019f"
DEFAULT_CONFIG_SHA256 = "efe19c417bed055f2d69908248c6ba650fa135bc868b0e6abb3da181dab690a0"
MAX_TEXT_CHARS = 4_000


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_model(model: Path) -> Path:
    config = Path(f"{model}.json")
    expected = (
        (model, DEFAULT_MODEL_SHA256),
        (config, DEFAULT_CONFIG_SHA256),
    )
    for path, expected_hash in expected:
        if not path.is_file():
            raise FileNotFoundError(f"missing pinned Piper artifact: {path}")
        actual = sha256(path)
        if actual != expected_hash:
            raise RuntimeError(f"SHA-256 mismatch for {path}: {actual}")
    return config


def notify_systemd(message: str) -> None:
    notify_socket = os.environ.get("NOTIFY_SOCKET")
    if not notify_socket:
        return
    if notify_socket.startswith("@"):
        notify_socket = "\0" + notify_socket[1:]
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as notifier:
        notifier.connect(notify_socket)
        notifier.sendall(message.encode("utf-8"))


class PiperEngine:
    def __init__(self, model: Path) -> None:
        config = verify_model(model)
        self.voice = PiperVoice.load(model, config_path=config)
        self.sample_rate = self.voice.config.sample_rate

    def synthesize(self, text: str):
        return self.voice.synthesize(text)


class PiperServer(socketserver.UnixStreamServer):
    allow_reuse_address = True

    def __init__(self, socket_path: Path, engine: PiperEngine) -> None:
        self.engine = engine
        super().__init__(str(socket_path), PiperHandler)


class PiperHandler(socketserver.StreamRequestHandler):
    server: PiperServer

    def handle(self) -> None:
        started = time.perf_counter()
        try:
            line = self.rfile.readline(MAX_HEADER_BYTES + 1)
            if not line or len(line) > MAX_HEADER_BYTES:
                raise ValueError("invalid or oversized TTS request")
            value = json.loads(line)
            text = value.get("text") if isinstance(value, dict) else None
            if not isinstance(text, str) or not text.strip():
                raise ValueError("TTS request requires non-empty text")
            if len(text) > MAX_TEXT_CHARS:
                raise ValueError(f"TTS text exceeds {MAX_TEXT_CHARS} characters")

            write_json(
                self.wfile,
                {
                    "event": "start",
                    "profile": "piper-lessac-medium",
                    "sample_rate": self.server.engine.sample_rate,
                    "sample_format": "s16le",
                },
            )
            total_samples = 0
            chunks = 0
            first_audio_seconds: float | None = None
            for index, chunk in enumerate(self.server.engine.synthesize(text)):
                pcm = chunk.audio_int16_bytes
                if first_audio_seconds is None:
                    first_audio_seconds = time.perf_counter() - started
                total_samples += len(pcm) // 2
                chunks += 1
                write_json(
                    self.wfile,
                    {
                        "event": "audio",
                        "index": index,
                        "bytes": len(pcm),
                    },
                )
                self.wfile.write(pcm)
                self.wfile.flush()
            if not chunks:
                raise RuntimeError("Piper produced no audio")
            total_seconds = time.perf_counter() - started
            write_json(
                self.wfile,
                {
                    "event": "complete",
                    "audio_seconds": round(
                        total_samples / self.server.engine.sample_rate,
                        3,
                    ),
                    "chunks": chunks,
                    "first_audio_seconds": round(first_audio_seconds or total_seconds, 3),
                    "peak_rss_mib": round(
                        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
                        1,
                    ),
                    "profile": "piper-lessac-medium",
                    "sample_rate": self.server.engine.sample_rate,
                    "total_seconds": round(total_seconds, 3),
                },
            )
        except Exception as error:
            try:
                write_json(self.wfile, {"event": "error", "message": str(error)})
            except (BrokenPipeError, OSError):
                pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", type=Path, default=DEFAULT_SOCKET)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--no-warmup", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.socket.parent.mkdir(parents=True, exist_ok=True)
    args.socket.unlink(missing_ok=True)
    load_started = time.perf_counter()
    engine = PiperEngine(args.model)
    load_seconds = time.perf_counter() - load_started
    warmup_seconds = 0.0
    if not args.no_warmup:
        warm_started = time.perf_counter()
        next(iter(engine.synthesize("Hi!")))
        warmup_seconds = time.perf_counter() - warm_started
    with PiperServer(args.socket, engine) as server:
        os.chmod(args.socket, 0o660)
        notify_systemd(
            "READY=1\nSTATUS="
            f"Piper Lessac ready; load={load_seconds:.3f}s warmup={warmup_seconds:.3f}s"
        )
        print(
            json.dumps(
                {
                    "event": "ready",
                    "load_seconds": round(load_seconds, 3),
                    "profile": "piper-lessac-medium",
                    "sample_rate": engine.sample_rate,
                    "socket": str(args.socket),
                    "warmup_seconds": round(warmup_seconds, 3),
                },
                sort_keys=True,
            ),
            flush=True,
        )
        try:
            server.serve_forever(poll_interval=0.2)
        except KeyboardInterrupt:
            pass
        finally:
            args.socket.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2) from error
