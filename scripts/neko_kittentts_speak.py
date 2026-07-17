#!/usr/bin/env python3
"""Generate a pinned KittenTTS sample without network access."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import sys
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
import soundfile as sf
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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_model(model_dir: Path, expected_hashes: dict[str, str]) -> None:
    for name, expected in expected_hashes.items():
        path = model_dir / name
        if not path.is_file():
            raise FileNotFoundError(f"missing pinned KittenTTS artifact: {path}")
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(f"SHA-256 mismatch for {path}: {actual}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--speed", type=float, default=DEFAULT_SPEED)
    parser.add_argument("--profile", choices=tuple(MODEL_PROFILES), default=DEFAULT_PROFILE)
    parser.add_argument("--threads", type=int, default=DEFAULT_THREADS)
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    parser.add_argument("--sentence-gap-ms", type=int, default=DEFAULT_SENTENCE_GAP_MS)
    parser.add_argument(
        "--no-clean-text",
        action="store_true",
        help="Disable KittenTTS number/unit text normalization.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not 0.5 <= args.speed <= 2.0:
        raise ValueError("speed must be between 0.5 and 2.0")
    if not 1 <= args.threads <= (os.cpu_count() or 1):
        raise ValueError("threads must be between 1 and the logical CPU count")
    if args.max_chars < 20:
        raise ValueError("max-chars must be at least 20")
    if not 0 <= args.sentence_gap_ms <= 1000:
        raise ValueError("sentence-gap-ms must be between 0 and 1000")

    profile = MODEL_PROFILES[args.profile]
    model_dir = profile.model_dir
    verify_model(model_dir, profile.hashes)
    config = json.loads((model_dir / "config.json").read_text())
    session_options = ort.SessionOptions()
    session_options.intra_op_num_threads = args.threads
    session_options.inter_op_num_threads = 1
    session_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

    started = time.perf_counter()
    model = KittenTTS_1_Onnx(
        model_path=str(model_dir / config["model_file"]),
        voices_path=str(model_dir / config["voices"]),
        speed_priors=config.get("speed_priors", {}),
        voice_aliases=config.get("voice_aliases", {}),
        session_options=session_options,
        providers=["CPUExecutionProvider"],
    )
    loaded = time.perf_counter()
    cleaned_text = model.preprocessor(args.text) if not args.no_clean_text else args.text
    text_chunks = chunk_text(cleaned_text, max_len=args.max_chars)
    if not text_chunks:
        raise ValueError("text produced no speakable chunks")
    audio_chunks: list[np.ndarray] = []
    chunk_metrics: list[dict[str, float | int]] = []
    gap_samples = round(args.sentence_gap_ms * SAMPLE_RATE / 1000)
    for index, text_chunk in enumerate(text_chunks):
        chunk_started = time.perf_counter()
        chunk_audio = model.generate_single_chunk(
            text_chunk,
            voice=args.voice,
            speed=args.speed,
        ).squeeze()
        chunk_finished = time.perf_counter()
        audio_chunks.append(chunk_audio)
        chunk_metrics.append(
            {
                "audio_seconds": round(len(chunk_audio) / SAMPLE_RATE, 3),
                "characters": len(text_chunk),
                "generate_seconds": round(chunk_finished - chunk_started, 3),
                "index": index,
            }
        )
        if gap_samples and index < len(text_chunks) - 1:
            audio_chunks.append(np.zeros(gap_samples, dtype=np.float32))
    audio = np.concatenate(audio_chunks)
    generated = time.perf_counter()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    sf.write(args.output, audio, SAMPLE_RATE)
    duration = len(audio) / SAMPLE_RATE
    print(
        json.dumps(
            {
                "audio_seconds": round(duration, 3),
                "chunk_count": len(text_chunks),
                "chunks": chunk_metrics,
                "first_chunk_seconds": chunk_metrics[0]["generate_seconds"],
                "generate_seconds": round(generated - loaded, 3),
                "input_characters": len(args.text),
                "load_seconds": round(loaded - started, 3),
                "max_chars": args.max_chars,
                "output": str(args.output),
                "peak_rss_mib": round(
                    resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1
                ),
                "profile": args.profile,
                "realtime_factor": round((generated - loaded) / duration, 3),
                "sample_rate": SAMPLE_RATE,
                "sentence_gap_ms": args.sentence_gap_ms,
                "speed": args.speed,
                "threads": args.threads,
                "voice": args.voice,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
