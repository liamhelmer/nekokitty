#!/usr/bin/env python3
"""Transcribe a WAV or bounded live ALSA/PipeWire capture with local streaming ASR.

Live capture is held only in process memory and is never written to disk. Run
this script with the dedicated ASR interpreter documented in the setup log.
"""

from __future__ import annotations

import argparse
from array import array
import json
import math
import os
from pathlib import Path
import resource
import signal
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


def pcm_levels_db(samples: list[float]) -> tuple[float | None, float | None]:
    """Return RMS and peak dBFS without retaining or exposing audio samples."""

    if not samples:
        return None, None
    peak = max(abs(sample) for sample in samples)
    rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
    rms_db = 20.0 * math.log10(rms) if rms > 0 else None
    peak_db = 20.0 * math.log10(peak) if peak > 0 else None
    return rms_db, peak_db


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


def capture_pipewire(seconds: float, target: str | None = None) -> tuple[int, list[float]]:
    """Capture the PipeWire default/selected source to memory as raw PCM."""

    if seconds <= 0:
        raise ValueError("PipeWire capture duration must be positive")

    command = [
        "/usr/bin/pw-record",
        "--rate",
        "16000",
        "--channels",
        "1",
        "--format",
        "s16",
        "--latency",
        "100ms",
    ]
    if target:
        command.extend(("--target", target))
    command.append("-")
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    interrupted = False
    try:
        stdout, stderr = process.communicate(timeout=seconds)
    except subprocess.TimeoutExpired:
        interrupted = True
        os.killpg(process.pid, signal.SIGINT)
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired as error:
            os.killpg(process.pid, signal.SIGTERM)
            process.communicate(timeout=5)
            raise RuntimeError("PipeWire capture did not stop cleanly") from error
    detail = stderr.decode("utf-8", errors="replace").strip()
    # PipeWire 1.0.5 pw-record exits 1 with empty stderr after a clean SIGINT,
    # even though it flushes valid PCM. Accept that observed bounded-stop
    # contract only when this process sent the interrupt and audio is present.
    clean_stop = process.returncode in {0, -signal.SIGINT, 128 + signal.SIGINT}
    clean_interrupted_stop = interrupted and process.returncode == 1 and not detail
    if not (clean_stop or clean_interrupted_stop):
        raise RuntimeError(
            f"PipeWire capture failed with status {process.returncode}: {detail}"
        )
    # pw-record emits headerless PCM when stdout has no filename extension.
    if len(stdout) % 2:
        raise RuntimeError("PipeWire returned a truncated 16-bit PCM sample")
    minimum_bytes = int(seconds * 16000 * 2 * 0.5)
    if len(stdout) < minimum_bytes:
        raise RuntimeError(
            f"PipeWire returned only {len(stdout)} PCM bytes; expected at least {minimum_bytes}"
        )
    stdout = stdout[: int(seconds * 16000 * 2)]
    return 16000, pcm16_to_float(stdout)


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
    source.add_argument("--pipewire-seconds", type=float)
    parser.add_argument("--device", default="plughw:CARD=Webcam,DEV=0")
    parser.add_argument(
        "--pipewire-target",
        help="optional PipeWire node name/serial; the current default source is used otherwise",
    )
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
    elif args.microphone_seconds is not None:
        rate, samples = capture_alsa(args.device, args.microphone_seconds)
        source = "live-memory-only"
    else:
        rate, samples = capture_pipewire(args.pipewire_seconds, args.pipewire_target)
        source = "live-pipewire-memory-only"
    decode_started = time.monotonic()
    text, steps = transcribe(recognizer, rate, samples, args.language)
    decode_s = time.monotonic() - decode_started
    audio_s = len(samples) / rate
    input_rms_db, input_peak_db = pcm_levels_db(samples)
    print(
        json.dumps(
            {
                "source": source,
                "media_retained": False,
                "language_hint": args.language,
                "load_s": round(load_s, 3),
                "audio_s": round(audio_s, 3),
                "input_rms_db": (
                    None if input_rms_db is None else round(input_rms_db, 2)
                ),
                "input_peak_db": (
                    None if input_peak_db is None else round(input_peak_db, 2)
                ),
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
