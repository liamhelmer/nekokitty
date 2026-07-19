#!/usr/bin/env python3
"""Pre-render approved Neko stories with pinned KittenTTS Mini and fixed cues."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import resource
import sys
import time

import numpy as np
import onnxruntime as ort
import soundfile as sf
from kittentts.onnx_model import KittenTTS_1_Onnx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neko.kittentts_config import (  # noqa: E402
    DEFAULT_SPEED,
    DEFAULT_THREADS,
    DEFAULT_VOICE,
    MODEL_PROFILES,
    SAMPLE_RATE,
)
from neko.story_library import StoryLibrary  # noqa: E402
from neko.tts_protocol import prepare_tts_text  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "content/stories/recordings/mini-kiki-v1"
DEFAULT_SEED = "neko-story-audio-mini-kiki-v1"
DEFAULT_MAX_SECTION_CHARS = 380
DEFAULT_CUE_RATE = 0.35
ALLOWED_CUES = ("meow_general", "meow_thank_you")

# These are editorial decisions, not runtime randomness. Every current story has
# a happy ending; Luna's brisk fetch ending stays purr-free for audible variety.
ENDING_PURR_BY_STORY = {
    "original.magic-girl-gummy-worm-moon": True,
    "original.luna-stick-garden": False,
    "original.heidi-ravens-muddy-masterpiece": True,
    "original.neko-great-gummy-worm-parade": True,
    "fan.elsa-wacky-wand-concert": True,
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_profile(profile_name: str) -> None:
    profile = MODEL_PROFILES[profile_name]
    for filename, expected in profile.hashes.items():
        path = profile.model_dir / filename
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"pinned KittenTTS artifact failed integrity: {path}")


def story_sections(text: str, max_chars: int) -> tuple[str, ...]:
    """Group whole Markdown paragraphs into large, model-safe spoken sections."""

    paragraphs = tuple(
        " ".join(paragraph.split())
        for paragraph in text.split("\n\n")
        if paragraph.strip()
    )
    sections: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            raise ValueError(
                f"story paragraph exceeds {max_chars} characters; edit it naturally"
            )
        combined = f"{current} {paragraph}".strip()
        if current and len(combined) > max_chars:
            sections.append(current)
            current = paragraph
        else:
            current = combined
    if current:
        sections.append(current)
    return tuple(sections)


def story_rng(seed: str, story_id: str) -> random.Random:
    digest = hashlib.sha256(f"{seed}:{story_id}".encode("utf-8")).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def cue_plan(section_count: int, rng: random.Random, rate: float) -> dict[int, str]:
    """Choose fixed one-time cue positions between sections, never back-to-back."""

    if section_count < 2:
        return {}
    choices: dict[int, str] = {}
    previous = False
    for section_index in range(section_count - 1):
        selected = not previous and rng.random() < rate
        if selected:
            action = "meow_thank_you" if rng.random() < 0.25 else "meow_general"
            choices[section_index] = action
        previous = selected
    if not choices and section_count >= 3:
        choices[(section_count - 1) // 2] = "meow_general"
    return choices


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--profile", choices=tuple(MODEL_PROFILES), default="mini")
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--speed", type=float, default=DEFAULT_SPEED)
    parser.add_argument("--threads", type=int, default=DEFAULT_THREADS)
    parser.add_argument("--max-section-chars", type=int, default=DEFAULT_MAX_SECTION_CHARS)
    parser.add_argument("--cue-rate", type=float, default=DEFAULT_CUE_RATE)
    parser.add_argument("--seed", default=DEFAULT_SEED)
    parser.add_argument("--story-id", action="append", default=[])
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Reuse exact text/hash matches and regenerate only stale sections.",
    )
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 0.5 <= args.speed <= 2.0:
        raise ValueError("speed must be between 0.5 and 2.0")
    if not 1 <= args.threads <= (os.cpu_count() or 1):
        raise ValueError("invalid thread count")
    if not 200 <= args.max_section_chars <= 400:
        raise ValueError("max section characters must be between 200 and 400")
    if not 0 <= args.cue_rate <= 1:
        raise ValueError("cue rate must be between zero and one")

    verify_profile(args.profile)
    profile = MODEL_PROFILES[args.profile]
    config = json.loads((profile.model_dir / "config.json").read_text())
    options = ort.SessionOptions()
    options.intra_op_num_threads = args.threads
    options.inter_op_num_threads = 1
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    load_started = time.perf_counter()
    model = KittenTTS_1_Onnx(
        model_path=str(profile.model_dir / config["model_file"]),
        voices_path=str(profile.model_dir / config["voices"]),
        speed_priors=config.get("speed_priors", {}),
        voice_aliases=config.get("voice_aliases", {}),
        session_options=options,
        providers=["CPUExecutionProvider"],
    )
    load_seconds = time.perf_counter() - load_started

    # The repair path must remain able to rebuild a malformed recording
    # manifest, so source selection deliberately ignores recorded state.
    library = StoryLibrary(recording_manifest_path=None)
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / "manifest.json"
    previous_manifest: dict[str, object] = {}
    if manifest_path.is_file():
        previous_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    previous_entries = {
        item["story_id"]: item
        for item in previous_manifest.get("stories", [])
        if isinstance(item, dict) and isinstance(item.get("story_id"), str)
    }
    updated_entries = previous_entries.copy() if args.story_id else {}
    build_started = time.perf_counter()
    all_stories = library.search("story", limit=100)
    requested_ids = set(args.story_id)
    unknown_ids = requested_ids - {story.story_id for story in all_stories}
    if unknown_ids:
        raise ValueError(f"unknown or unapproved story IDs: {sorted(unknown_ids)}")
    stories = tuple(
        story for story in all_stories if not requested_ids or story.story_id in requested_ids
    )
    for story_number, story in enumerate(stories, start=1):
        source_entry = next(item for item in library.entries if item["id"] == story.story_id)
        source_path = (REPO_ROOT / source_entry["path"]).resolve()
        spoken = library.spoken_text(story)
        sections = story_sections(spoken, args.max_section_chars)
        cues = cue_plan(
            len(sections),
            story_rng(args.seed, story.story_id),
            args.cue_rate,
        )
        story_dir = output_root / story.story_id.replace(".", "_")
        story_dir.mkdir(parents=True, exist_ok=True)
        rendered_sections: list[dict[str, object]] = []
        previous_entry = previous_entries.get(story.story_id, {})
        previous_sections = {
            item.get("index"): item
            for item in previous_entry.get("sections", [])
            if isinstance(item, dict)
        }
        print(
            json.dumps(
                {
                    "event": "story_started",
                    "index": story_number,
                    "story_id": story.story_id,
                    "sections": len(sections),
                }
            ),
            flush=True,
        )
        for index, section in enumerate(sections):
            output = story_dir / f"section-{index + 1:02d}.flac"
            section_text_hash = sha256_bytes(section.encode("utf-8"))
            previous = previous_sections.get(index)
            reusable = (
                args.incremental
                and isinstance(previous, dict)
                and previous.get("text_sha256") == section_text_hash
                and previous.get("path") == str(output.relative_to(REPO_ROOT))
                and output.is_file()
                and previous.get("sha256") == sha256(output)
            )
            if reusable:
                preserved = dict(previous)
                preserved["cue_after"] = cues.get(index)
                rendered_sections.append(preserved)
                print(
                    json.dumps(
                        {
                            "event": "section_reused",
                            "story_id": story.story_id,
                            "section": index + 1,
                            "sections": len(sections),
                        }
                    ),
                    flush=True,
                )
                continue
            if output.exists() and not (args.force or args.incremental):
                raise FileExistsError(f"refusing to overwrite without --force: {output}")
            tts_text = model.preprocessor(prepare_tts_text(section))
            section_started = time.perf_counter()
            audio = model.generate_single_chunk(
                tts_text,
                voice=args.voice,
                speed=args.speed,
            ).squeeze()
            if audio.ndim != 1 or not len(audio) or not np.all(np.isfinite(audio)):
                raise RuntimeError(f"invalid generated audio for {story.story_id}/{index}")
            peak = float(np.max(np.abs(audio)))
            if not math.isfinite(peak) or peak > 1.25:
                raise RuntimeError(f"unsafe generated peak for {story.story_id}/{index}: {peak}")
            temporary = output.with_suffix(".tmp.flac")
            sf.write(temporary, np.clip(audio, -1.0, 1.0), SAMPLE_RATE, subtype="PCM_16")
            temporary.replace(output)
            duration = len(audio) / SAMPLE_RATE
            rendered_sections.append(
                {
                    "index": index,
                    "path": str(output.relative_to(REPO_ROOT)),
                    "sha256": sha256(output),
                    "text_sha256": section_text_hash,
                    "characters": len(section),
                    "contains_neko": "neko" in section.casefold(),
                    "duration_seconds": round(duration, 3),
                    "cue_after": cues.get(index),
                }
            )
            print(
                json.dumps(
                    {
                        "event": "section_complete",
                        "story_id": story.story_id,
                        "section": index + 1,
                        "sections": len(sections),
                        "audio_seconds": round(duration, 3),
                        "generate_seconds": round(time.perf_counter() - section_started, 3),
                    }
                ),
                flush=True,
            )
        referenced = {Path(item["path"]).name for item in rendered_sections}
        for stale_path in story_dir.glob("section-*.flac"):
            if stale_path.name not in referenced:
                stale_path.unlink()
        updated_entries[story.story_id] = {
            "story_id": story.story_id,
            "source_path": str(source_path.relative_to(REPO_ROOT)),
            "source_sha256": sha256(source_path),
            "spoken_text_sha256": sha256_bytes(spoken.encode("utf-8")),
            "sections": rendered_sections,
            # Newly composed owner-approved stories default to a warm ending.
            # Existing shelf decisions remain explicit above.
            "ending_purr": ENDING_PURR_BY_STORY.get(story.story_id, True),
        }

    entries = [
        updated_entries[story.story_id]
        for story in all_stories
        if story.story_id in updated_entries
    ]

    run_record = {
        "builder": "scripts/build_story_recordings.py",
        "profile": args.profile,
        "model_revision": profile.model_dir.name,
        "model_hashes": profile.hashes,
        "voice": args.voice,
        "speed": args.speed,
        "sample_rate": SAMPLE_RATE,
        "sample_format": "FLAC/PCM_16",
        "threads": args.threads,
        "max_section_characters": args.max_section_chars,
        "cue_rate": args.cue_rate,
        "cue_seed": args.seed,
        "allowed_cues": list(ALLOWED_CUES),
        "incremental": args.incremental,
        "scope": sorted(requested_ids) if requested_ids else "all",
        "load_seconds": round(load_seconds, 3),
        "render_seconds": round(time.perf_counter() - build_started, 3),
        "peak_rss_mib": round(
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
            1,
        ),
    }
    manifest = {
        "schema_version": 1,
        "build": (
            previous_manifest["build"]
            if args.incremental and isinstance(previous_manifest.get("build"), dict)
            else run_record
        ),
        "stories": entries,
    }
    if args.incremental:
        manifest["last_refresh"] = run_record
    temporary_manifest = manifest_path.with_suffix(".tmp.json")
    temporary_manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary_manifest.replace(manifest_path)
    print(
        json.dumps(
            {
                "event": "complete",
                "manifest": str(manifest_path),
                "stories": len(entries),
                "render_seconds": run_record["render_seconds"],
            }
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
