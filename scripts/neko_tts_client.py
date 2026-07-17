#!/usr/bin/env python3
"""Synthesize or play English speech through Neko's resident TTS worker."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neko.tts_protocol import DEFAULT_SOCKET, TtsClient  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text", required=True)
    parser.add_argument("--socket", type=Path, default=DEFAULT_SOCKET)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--play", action="store_true")
    args = parser.parse_args()
    result = TtsClient(args.socket).synthesize(
        args.text,
        output=args.output,
        play=args.play,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
