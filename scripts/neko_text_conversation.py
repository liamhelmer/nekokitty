#!/usr/bin/env python3
"""Exercise Neko's deterministic wake policy and local Gemma conversation.

This is a text-first integration tool. It does not retain transcripts. Pass one
or more ``--utterance`` values for a non-interactive smoke test, or omit them to
use a terminal session. Speech synthesis/playback remains opt-in with ``--speak``.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neko.behavior import BehaviorController  # noqa: E402
from neko.events import (  # noqa: E402
    Acknowledge,
    CancelAudio,
    DialogueRequest,
    SetMuted,
    TranscriptEvent,
)
from neko.gemma_client import GemmaClient  # noqa: E402
from neko.tts_protocol import TtsClient  # noqa: E402


SUPERTONIC_CLI = Path("/home/neko/.local/share/neko/venvs/tts/bin/supertonic")
SUPERTONIC_MODEL_DIR = Path("/home/neko/models/supertonic-3")


def speak(text: str, language: str, voice: str) -> None:
    if language not in {"en", "fr", "es"}:
        language = "en"
    if language == "en":
        TtsClient().synthesize(text, play=True)
        return
    if not SUPERTONIC_CLI.is_file() or not SUPERTONIC_MODEL_DIR.is_dir():
        raise RuntimeError("the isolated Supertonic runtime is not installed")
    with tempfile.TemporaryDirectory(prefix="neko-tts-") as directory:
        output = Path(directory) / "reply.wav"
        env = {
            "PATH": "/usr/bin:/bin",
            "HOME": str(Path.home()),
            "SUPERTONIC_CACHE_DIR": str(SUPERTONIC_MODEL_DIR),
            "SUPERTONIC_INTRA_OP_THREADS": "4",
            "SUPERTONIC_INTER_OP_THREADS": "1",
        }
        generated = subprocess.run(
            [
                str(SUPERTONIC_CLI),
                "tts",
                text,
                "--output",
                str(output),
                "--voice",
                voice,
                "--lang",
                language,
                "--steps",
                "6",
            ],
            env=env,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if generated.returncode != 0:
            raise RuntimeError(generated.stderr.strip() or "Supertonic failed")
        player = next((p for p in ("/usr/bin/pw-play", "/usr/bin/aplay") if Path(p).is_file()), None)
        if player is None:
            raise RuntimeError("no local WAV player is installed")
        subprocess.run([player, str(output)], check=True, timeout=60)


def run_utterance(
    controller: BehaviorController,
    client: GemmaClient,
    utterance: str,
    language: str,
    audible: bool,
    voice: str,
) -> str | None:
    actions = controller.handle(
        TranscriptEvent(utterance, language, time.monotonic())  # type: ignore[arg-type]
    )
    answer: str | None = None
    for action in actions:
        if isinstance(action, Acknowledge):
            print("Neko: *prrt?*")
        elif isinstance(action, DialogueRequest):
            answer = client.reply(action.text, action.language)
            print(f"Neko: {answer}")
            if audible:
                speak(answer, action.language, voice)
        elif isinstance(action, CancelAudio):
            print(f"Neko: [audio cancelled: {action.reason}]")
        elif isinstance(action, SetMuted):
            print(f"Neko: [muted={action.muted}]")
    return answer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--utterance", action="append", default=[])
    parser.add_argument("--language", choices=("en", "fr", "es"), default="en")
    parser.add_argument("--speak", action="store_true", help="synthesize and play replies")
    parser.add_argument(
        "--voice",
        choices=tuple(f"F{i}" for i in range(1, 6)),
        default="F1",
        help="Supertonic voice used for French and Spanish; English uses Kiki",
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:9379")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    controller = BehaviorController()
    client = GemmaClient(base_url=args.base_url)
    if not client.ready():
        print("Gemma is not ready", file=sys.stderr)
        return 1
    utterances = args.utterance
    if utterances:
        for utterance in utterances:
            run_utterance(controller, client, utterance, args.language, args.speak, args.voice)
        return 0
    print("Type 'Neko Neko' plus a request. Ctrl-D exits; no transcript is saved.")
    while True:
        try:
            utterance = input("You: ")
        except EOFError:
            print()
            return 0
        run_utterance(controller, client, utterance, args.language, args.speak, args.voice)


if __name__ == "__main__":
    raise SystemExit(main())
