#!/usr/bin/env python3
"""Transcribe a WAV or bounded live ALSA capture with local streaming ASR.

Live capture is held only in process memory and is never written to disk. Run
this script with the dedicated ASR interpreter documented in the setup log.
"""

from __future__ import annotations

import argparse
from array import array
import json
from pathlib import Path
import resource
import subprocess
import sys
import time
import wave

DEFAULT_MODEL = Path(
    "/home/neko/models/sherpa-onnx-nemotron/extracted/"
    "sherpa-onnx-nemotron-3.5-asr-streaming-0.6b-560ms-int8-2026-06-11"
)


def pcm16_to_float(raw: bytes) -> list[float]:
    values = array("h")
    values.frombytes(raw)
    if sys.byteorder != "little":
        values.byteswap()
    return [value / 32768.0 for value in values]


def read_wav(path: Path) -> tuple[int, list[float]]:
    with wave.open(str(path), "rb") as source:
        if source.getnchannels() != 1 or source.getsampwidth() != 2:
            raise ValueError("input WAV must be mono 16-bit PCM")
        return source.getframerate(), pcm16_to_float(source.readframes(source.getnframes()))


def capture_alsa(device: str, seconds: float) -> tuple[int, list[float]]:
    command = [
        "/usr/bin/arecord",
        "--quiet",
        "--device",
        device,
        "--format",
        "S16_LE",
        "--rate",
        "16000",
        "--channels",
        "1",
        "--file-type",
        "raw",
        "--duration",
        str(max(1, round(seconds))),
        "-",
    ]
    captured = subprocess.run(command, capture_output=True, timeout=seconds + 10)
    if captured.returncode:
        detail = captured.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"ALSA capture failed for {device}: {detail}")
    return 16000, pcm16_to_float(captured.stdout)


def build_recognizer(model: Path, threads: int) -> object:
    import sherpa_onnx

    return sherpa_onnx.OnlineRecognizer.from_transducer(
        tokens=str(model / "tokens.txt"),
        encoder=str(model / "encoder.int8.onnx"),
        decoder=str(model / "decoder.int8.onnx"),
        joiner=str(model / "joiner.int8.onnx"),
        num_threads=threads,
        decoding_method="greedy_search",
        provider="cpu",
    )


def transcribe(
    recognizer: object,
    sample_rate: int,
    samples: list[float],
    language: str,
) -> tuple[str, int]:
    stream = recognizer.create_stream()
    stream.set_option("language", language)
    stream.accept_waveform(sample_rate, samples)
    stream.accept_waveform(sample_rate, [0.0] * int(sample_rate * 0.8))
    stream.input_finished()
    steps = 0
    while recognizer.is_ready(stream):
        recognizer.decode_stream(stream)
        steps += 1
    return recognizer.get_result_all(stream).text.strip(), steps


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", type=Path)
    source.add_argument("--microphone-seconds", type=float)
    parser.add_argument("--device", default="plughw:CARD=Webcam,DEV=0")
    parser.add_argument("--language", choices=("auto", "en", "fr", "es"), default="auto")
    parser.add_argument("--threads", type=int, choices=range(1, 7), default=4)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    started = time.monotonic()
    recognizer = build_recognizer(args.model, args.threads)
    load_s = time.monotonic() - started
    if args.file:
        rate, samples = read_wav(args.file)
        source = "file"
    else:
        rate, samples = capture_alsa(args.device, args.microphone_seconds)
        source = "live-memory-only"
    decode_started = time.monotonic()
    text, steps = transcribe(recognizer, rate, samples, args.language)
    decode_s = time.monotonic() - decode_started
    audio_s = len(samples) / rate
    print(
        json.dumps(
            {
                "source": source,
                "media_retained": False,
                "language_hint": args.language,
                "load_s": round(load_s, 3),
                "audio_s": round(audio_s, 3),
                "decode_s": round(decode_s, 3),
                "realtime_factor": round(decode_s / audio_s, 3) if audio_s else None,
                "steps": steps,
                "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                "text": text,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
