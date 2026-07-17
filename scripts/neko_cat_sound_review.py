#!/usr/bin/env python3
"""List, verify, and play the curated cat recordings at normalized loudness."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from neko.cat_audio import playback_multiplier


DEFAULT_MANIFEST = REPO_ROOT / "config/cat-sounds/curated-freesound.json"
DEFAULT_NORMALIZATION = (
    REPO_ROOT / "config/cat-sounds/curated-freesound-normalization.json"
)


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def load_library(
    manifest_path: Path, normalization_path: Path
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    manifest = load_json(manifest_path)
    normalization = load_json(normalization_path)
    if normalization.get("source_library_id") != manifest.get("library_id"):
        raise ValueError("normalization data does not match the source library")

    measured = {entry["id"]: entry for entry in normalization["entries"]}
    joined: list[dict[str, Any]] = []
    for position, source in enumerate(manifest["entries"], start=1):
        analysis = measured.get(source["id"])
        if analysis is None or analysis["filename"] != source["filename"]:
            raise ValueError(f"missing or mismatched normalization for {source['id']}")
        joined.append({"position": position, "source": source, "analysis": analysis})
    if len(joined) != len(measured):
        raise ValueError("normalization data has entries absent from the manifest")
    return manifest, normalization, joined


def select_entry(entries: list[dict[str, Any]], selector: str) -> dict[str, Any]:
    if selector.isdecimal():
        position = int(selector)
        if 1 <= position <= len(entries):
            return entries[position - 1]
    for entry in entries:
        if selector in (entry["source"]["id"], entry["source"]["filename"]):
            return entry
    raise ValueError(f"unknown sound selector: {selector}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def play_file(
    path: Path, multiplier: float, *, preroll_seconds: float = 2.0, repeats: int = 1
) -> None:
    try:
        import gi

        gi.require_version("Gst", "1.0")
        from gi.repository import Gst
    except (ImportError, ValueError) as exc:
        raise RuntimeError("Python GStreamer bindings are required for playback") from exc

    Gst.init(None)
    if preroll_seconds < 0.0:
        raise ValueError("pre-roll must not be negative")
    if repeats < 1:
        raise ValueError("repeats must be at least one")

    # Keep one sink stream alive from the silent pre-roll through every repeat.
    # This prevents sub-second sounds from finishing while Bluetooth wakes up.
    caps = "audio/x-raw,format=F32LE,rate=48000,channels=2"
    branches: list[str] = []
    if preroll_seconds:
        buffers = max(1, math.ceil(preroll_seconds * 48000.0 / 1024.0))
        branches.append(
            f"audiotestsrc wave=silence num-buffers={buffers} ! {caps} ! c."
        )
    for repeat in range(repeats):
        if repeat:
            branches.append(f"audiotestsrc wave=silence num-buffers=47 ! {caps} ! c.")
        branches.append(
            f'uridecodebin uri="{path.as_uri()}" ! audioconvert ! audioresample ! '
            f"{caps} ! c."
        )

    # volume-full-range permits safe multipliers above 10 for very quiet sources.
    pipeline = Gst.parse_launch(
        f"concat name=c ! volume volume-full-range={multiplier:.9f} ! "
        f"audioconvert ! audioresample ! autoaudiosink {' '.join(branches)}"
    )
    bus = pipeline.get_bus()
    pipeline.set_state(Gst.State.PLAYING)
    try:
        while True:
            message = bus.timed_pop_filtered(
                Gst.CLOCK_TIME_NONE, Gst.MessageType.ERROR | Gst.MessageType.EOS
            )
            if message.type == Gst.MessageType.ERROR:
                error, debug = message.parse_error()
                raise RuntimeError(f"GStreamer playback failed: {error}; {debug}")
            if message.type == Gst.MessageType.EOS:
                return
    finally:
        pipeline.set_state(Gst.State.NULL)


def list_entries(
    entries: list[dict[str, Any]], normalization: dict[str, Any], master: float
) -> None:
    ceiling = float(normalization["policy"]["sample_peak_ceiling_dbfs"])
    for entry in entries:
        source = entry["source"]
        analysis = entry["analysis"]
        multiplier, applied_db, predicted_peak = playback_multiplier(
            float(analysis["track_gain_db"]),
            float(analysis["sample_peak"]),
            master,
            peak_ceiling_dbfs=ceiling,
        )
        limited = " peak-limited" if applied_db < float(analysis["track_gain_db"]) else ""
        print(
            f'{entry["position"]:02d} {source["id"]} {source["duration_seconds"]:7.2f}s '
            f"gain={applied_db:+6.2f}dB player={multiplier:7.3f} "
            f"peak={predicted_peak:.3f}{limited}  {source['title']}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--normalization", type=Path, default=DEFAULT_NORMALIZATION)
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="show normalized review levels")
    list_parser.add_argument("--master", type=float)

    play_parser = subparsers.add_parser("play", help="play one complete sound and exit")
    play_parser.add_argument("selector", help="1-based position, Freesound ID, or filename")
    play_parser.add_argument("--master", type=float)
    play_parser.add_argument("--preroll", type=float, default=2.0)
    play_parser.add_argument("--repeat", type=int, default=1)
    play_parser.add_argument("--skip-hash-check", action="store_true")

    args = parser.parse_args()
    manifest, normalization, entries = load_library(args.manifest, args.normalization)
    master = (
        float(args.master)
        if args.master is not None
        else float(normalization["policy"]["review_master_linear"])
    )
    if master <= 0.0:
        raise ValueError("master must be positive")

    if args.command == "list":
        list_entries(entries, normalization, master)
        return 0

    entry = select_entry(entries, args.selector)
    source = entry["source"]
    analysis = entry["analysis"]
    source_path = Path(manifest["source_root"]) / source["filename"]
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    if not args.skip_hash_check and sha256_file(source_path) != source["sha256"]:
        raise ValueError(f"source hash changed: {source_path}")

    ceiling = float(normalization["policy"]["sample_peak_ceiling_dbfs"])
    multiplier, applied_db, predicted_peak = playback_multiplier(
        float(analysis["track_gain_db"]),
        float(analysis["sample_peak"]),
        master,
        peak_ceiling_dbfs=ceiling,
    )
    limited = applied_db < float(analysis["track_gain_db"])
    print(
        f'PLAY {entry["position"]:02d}/{len(entries):02d} {source["id"]} '
        f'{source["duration_seconds"]:.2f}s {source["title"]}\n'
        f"track_gain={analysis['track_gain_db']:+.2f}dB "
        f"applied_gain={applied_db:+.2f}dB master={master:.3f} "
        f"player_multiplier={multiplier:.3f} predicted_peak={predicted_peak:.3f}"
        + (" peak-limited" if limited else ""),
        flush=True,
    )
    play_file(
        source_path,
        multiplier,
        preroll_seconds=args.preroll,
        repeats=args.repeat,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
