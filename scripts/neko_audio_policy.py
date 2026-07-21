#!/usr/bin/env python3
"""Keep Neko's ReSpeaker/Bluetooth PipeWire routing policy active."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neko.audio_policy import run_daemon  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(run_daemon())
