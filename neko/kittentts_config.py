"""Pinned local KittenTTS profiles and Neko's accepted English voice."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class KittenProfile:
    model_dir: Path
    hashes: dict[str, str]


MODEL_PROFILES = {
    "mini": KittenProfile(
        model_dir=Path(
            "/home/neko/models/kittentts/mini-0.8/"
            "c02725660cea441db4c383af69f1f26f5cd00947"
        ),
        hashes={
            "config.json": "6b160bc9b19e24ecb21e84bc14f8a7da21fdf47ec72d42450bc5cf514b61804a",
            "kitten_tts_mini_v0_8.onnx": "0f5bbae4fc4800c98dbc544a87ecfa79510de2fb8222db30d12e5bfe9177df91",
            "voices.npz": "40ad2638952b77b7b2f30127e2608e169fc69dd256b53bd8aaa3409a33193c42",
        },
    ),
    "micro": KittenProfile(
        model_dir=Path(
            "/home/neko/models/kittentts/micro-0.8/"
            "1ccf72b2c2048fd17efac7de2fab32d10e225084"
        ),
        hashes={
            "config.json": "1f0bd2208348f9211cb0da64fcd1536eb28228571cc6b09e767eb6e203a0a532",
            "kitten_tts_micro_v0_8.onnx": "95481626fee1ba70ce683e69c534fc7cb38433c46ce42d3abbeafb4b9f1a4123",
            "voices.npz": "112710c1be8ad0e967c190fb0fd95cbe5848ec4791b93209f20b28b7da20dac1",
        },
    ),
    "nano-int8": KittenProfile(
        model_dir=Path(
            "/home/neko/models/kittentts/nano-0.8-int8/"
            "84781d74e29ee25217551556398b42f80593a813"
        ),
        hashes={
            "config.json": "b66006ccbeccd4de5fc3c9272059c47f5725df7215fd889785c03602652fab64",
            "kitten_tts_nano_v0_8.onnx": "f7b0afcbee92870b32b8e0276d855b954dc25470c9f051b376ac7eee537c76fc",
            "voices.npz": "8aa7cee235abb0739cb51e6559685f65a4dacd95568833d05699b1633f519b3f",
        },
    ),
}

DEFAULT_PROFILE = "micro"
DEFAULT_VOICE = "Kiki"
DEFAULT_SPEED = 1.2
DEFAULT_THREADS = 4
DEFAULT_MAX_CHARS = 120
DEFAULT_SENTENCE_GAP_MS = 120
SAMPLE_RATE = 24_000
