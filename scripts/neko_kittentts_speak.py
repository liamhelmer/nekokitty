#!/usr/bin/env python3
"""Generate a pinned KittenTTS sample without network access."""

from __future__ import annotations

import argparse
import hashlib
import json
import resource
import time
from pathlib import Path

import soundfile as sf
from kittentts.onnx_model import KittenTTS_1_Onnx


DEFAULT_MODEL_DIR = Path(
    "/home/neko/models/kittentts/mini-0.8/"
    "c02725660cea441db4c383af69f1f26f5cd00947"
)
EXPECTED_HASHES = {
    "config.json": "6b160bc9b19e24ecb21e84bc14f8a7da21fdf47ec72d42450bc5cf514b61804a",
    "kitten_tts_mini_v0_8.onnx": "0f5bbae4fc4800c98dbc544a87ecfa79510de2fb8222db30d12e5bfe9177df91",
    "voices.npz": "40ad2638952b77b7b2f30127e2608e169fc69dd256b53bd8aaa3409a33193c42",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_model(model_dir: Path) -> None:
    for name, expected in EXPECTED_HASHES.items():
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
    parser.add_argument("--voice", default="Kiki")
    parser.add_argument("--speed", type=float, default=1.2)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument(
        "--no-clean-text",
        action="store_true",
        help="Disable KittenTTS number/unit text normalization.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    verify_model(args.model_dir)
    config = json.loads((args.model_dir / "config.json").read_text())

    started = time.perf_counter()
    model = KittenTTS_1_Onnx(
        model_path=str(args.model_dir / config["model_file"]),
        voices_path=str(args.model_dir / config["voices"]),
        speed_priors=config.get("speed_priors", {}),
        voice_aliases=config.get("voice_aliases", {}),
    )
    loaded = time.perf_counter()
    audio = model.generate(
        args.text,
        voice=args.voice,
        speed=args.speed,
        clean_text=not args.no_clean_text,
    ).squeeze()
    generated = time.perf_counter()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    sf.write(args.output, audio, 24_000)
    duration = len(audio) / 24_000
    print(
        json.dumps(
            {
                "audio_seconds": round(duration, 3),
                "generate_seconds": round(generated - loaded, 3),
                "load_seconds": round(loaded - started, 3),
                "output": str(args.output),
                "peak_rss_mib": round(
                    resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1
                ),
                "realtime_factor": round((generated - loaded) / duration, 3),
                "sample_rate": 24_000,
                "speed": args.speed,
                "voice": args.voice,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
