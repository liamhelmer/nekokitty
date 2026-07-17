#!/usr/bin/env python3
"""Serve pinned KittenTTS sentence frames over a local Unix socket."""

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
from typing import Any

import numpy as np
import onnxruntime as ort
from kittentts.onnx_model import KittenTTS_1_Onnx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neko.kittentts_config import (  # noqa: E402
    DEFAULT_MAX_CHARS,
    DEFAULT_PROFILE,
    DEFAULT_SENTENCE_GAP_MS,
    DEFAULT_SPEED,
    DEFAULT_THREADS,
    DEFAULT_VOICE,
    MODEL_PROFILES,
    SAMPLE_RATE,
)
from neko.tts_chunking import chunk_text  # noqa: E402
from neko.tts_protocol import DEFAULT_SOCKET, MAX_HEADER_BYTES, write_json  # noqa: E402


MAX_TEXT_CHARS = 4_000


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_profile(name: str) -> None:
    profile = MODEL_PROFILES[name]
    for filename, expected in profile.hashes.items():
        path = profile.model_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"missing pinned KittenTTS artifact: {path}")
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(f"SHA-256 mismatch for {path}: {actual}")


def notify_systemd(message: str) -> None:
    notify_socket = os.environ.get("NOTIFY_SOCKET")
    if not notify_socket:
        return
    if notify_socket.startswith("@"):
        notify_socket = "\0" + notify_socket[1:]
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as notifier:
        notifier.connect(notify_socket)
        notifier.sendall(message.encode("utf-8"))


class SpeechEngine:
    def __init__(self, profile_name: str, threads: int) -> None:
        verify_profile(profile_name)
        profile = MODEL_PROFILES[profile_name]
        config = json.loads((profile.model_dir / "config.json").read_text())
        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.model = KittenTTS_1_Onnx(
            model_path=str(profile.model_dir / config["model_file"]),
            voices_path=str(profile.model_dir / config["voices"]),
            speed_priors=config.get("speed_priors", {}),
            voice_aliases=config.get("voice_aliases", {}),
            session_options=options,
            providers=["CPUExecutionProvider"],
        )
        self.profile_name = profile_name
        self.threads = threads

    def prepare(self, text: str) -> list[str]:
        cleaned = self.model.preprocessor(text)
        return chunk_text(cleaned, max_len=DEFAULT_MAX_CHARS)

    def pcm(self, text: str, include_gap: bool) -> bytes:
        audio = self.model.generate_single_chunk(
            text,
            voice=DEFAULT_VOICE,
            speed=DEFAULT_SPEED,
        ).squeeze()
        if not np.all(np.isfinite(audio)):
            raise RuntimeError("KittenTTS produced non-finite audio")
        pcm = np.rint(np.clip(audio, -1.0, 1.0) * 32767.0).astype("<i2")
        if include_gap:
            gap_samples = round(DEFAULT_SENTENCE_GAP_MS * SAMPLE_RATE / 1000)
            pcm = np.concatenate((pcm, np.zeros(gap_samples, dtype="<i2")))
        return pcm.tobytes()


class TtsServer(socketserver.UnixStreamServer):
    allow_reuse_address = True

    def __init__(self, socket_path: Path, engine: SpeechEngine):
        self.engine = engine
        super().__init__(str(socket_path), TtsHandler)


class TtsHandler(socketserver.StreamRequestHandler):
    server: TtsServer

    def handle(self) -> None:
        started = time.perf_counter()
        try:
            line = self.rfile.readline(MAX_HEADER_BYTES + 1)
            if not line or len(line) > MAX_HEADER_BYTES:
                raise ValueError("invalid or oversized TTS request")
            request = json.loads(line)
            text = request.get("text") if isinstance(request, dict) else None
            if not isinstance(text, str) or not text.strip():
                raise ValueError("TTS request requires non-empty text")
            if len(text) > MAX_TEXT_CHARS:
                raise ValueError(f"TTS text exceeds {MAX_TEXT_CHARS} characters")
            chunks = self.server.engine.prepare(text)
            if not chunks:
                raise ValueError("TTS text produced no speakable chunks")
            write_json(
                self.wfile,
                {
                    "event": "start",
                    "chunks": len(chunks),
                    "profile": self.server.engine.profile_name,
                    "sample_rate": SAMPLE_RATE,
                    "sample_format": "s16le",
                    "voice": DEFAULT_VOICE,
                    "speed": DEFAULT_SPEED,
                },
            )
            total_samples = 0
            first_audio_seconds: float | None = None
            for index, chunk in enumerate(chunks):
                generated_at = time.perf_counter()
                pcm = self.server.engine.pcm(chunk, index < len(chunks) - 1)
                elapsed = time.perf_counter() - generated_at
                if first_audio_seconds is None:
                    first_audio_seconds = time.perf_counter() - started
                total_samples += len(pcm) // 2
                write_json(
                    self.wfile,
                    {
                        "event": "audio",
                        "index": index,
                        "bytes": len(pcm),
                        "characters": len(chunk),
                        "generate_seconds": round(elapsed, 3),
                    },
                )
                self.wfile.write(pcm)
                self.wfile.flush()
            total_seconds = time.perf_counter() - started
            write_json(
                self.wfile,
                {
                    "event": "complete",
                    "audio_seconds": round(total_samples / SAMPLE_RATE, 3),
                    "chunks": len(chunks),
                    "first_audio_seconds": round(first_audio_seconds or total_seconds, 3),
                    "profile": self.server.engine.profile_name,
                    "peak_rss_mib": round(
                        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1
                    ),
                    "sample_rate": SAMPLE_RATE,
                    "total_seconds": round(total_seconds, 3),
                    "voice": DEFAULT_VOICE,
                    "speed": DEFAULT_SPEED,
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
    parser.add_argument("--profile", choices=tuple(MODEL_PROFILES), default=DEFAULT_PROFILE)
    parser.add_argument("--threads", type=int, default=DEFAULT_THREADS)
    parser.add_argument("--no-warmup", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 1 <= args.threads <= (os.cpu_count() or 1):
        raise ValueError("threads must be between 1 and the logical CPU count")
    args.socket.parent.mkdir(parents=True, exist_ok=True)
    args.socket.unlink(missing_ok=True)
    load_started = time.perf_counter()
    engine = SpeechEngine(args.profile, args.threads)
    load_seconds = time.perf_counter() - load_started
    warmup_seconds = 0.0
    if not args.no_warmup:
        warm_started = time.perf_counter()
        engine.pcm("Hi!", False)
        warmup_seconds = time.perf_counter() - warm_started
    with TtsServer(args.socket, engine) as server:
        os.chmod(args.socket, 0o660)
        status = (
            f"READY=1\nSTATUS={args.profile}/{DEFAULT_VOICE}/{DEFAULT_SPEED}x ready; "
            f"load={load_seconds:.3f}s warmup={warmup_seconds:.3f}s"
        )
        notify_systemd(status)
        print(
            json.dumps(
                {
                    "event": "ready",
                    "load_seconds": round(load_seconds, 3),
                    "profile": args.profile,
                    "socket": str(args.socket),
                    "threads": args.threads,
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
    raise SystemExit(main())
