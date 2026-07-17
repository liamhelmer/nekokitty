#!/usr/bin/env python3
"""Build and verify Neko's lossless P0 cat-sound bench candidates.

The checked-in originals are never modified. Recipes define all excerpts and
filters; FFmpeg performs decoding/DSP, linear loudness gain, dither, and PCM
delivery. Every output remains runtime-disabled until derived listening and
physical speaker/transducer acceptance are recorded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any
import wave


REPO_ROOT = Path(__file__).resolve().parents[1]
RECIPES_PATH = REPO_ROOT / "config/cat-sounds/derived-assets-recipes.json"
SOURCE_MANIFEST_PATH = REPO_ROOT / "config/cat-sounds/curated-freesound.json"
REVIEW_LEDGER_PATH = (
    REPO_ROOT / "config/cat-sounds/curated-freesound-listening-review.json"
)
ORIGINAL_ROOT = REPO_ROOT / "assets/cat-sounds/originals"
DERIVED_ROOT = REPO_ROOT / "assets/cat-sounds/derived"
MANIFEST_PATH = DERIVED_ROOT / "manifest.json"
ATTRIBUTION_PATH = REPO_ROOT / "assets/cat-sounds/ATTRIBUTION.md"
FFMPEG = Path("/usr/bin/ffmpeg")
FFPROBE = Path("/usr/bin/ffprobe")


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, text=True, capture_output=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tool_version(tool: Path) -> str:
    first_line = run([str(tool), "-version"]).stdout.splitlines()[0]
    return first_line.removeprefix(f"{tool.name} version ")


def probe(path: Path) -> dict[str, Any]:
    result = run(
        [
            str(FFPROBE),
            "-v",
            "error",
            "-show_entries",
            "stream=codec_name,sample_fmt,sample_rate,channels,channel_layout,"
            "bits_per_raw_sample,duration_ts,time_base:format=duration,size",
            "-of",
            "json",
            str(path),
        ]
    )
    return json.loads(result.stdout)


def mono_filter(channels: int) -> str:
    if channels == 1:
        return "aformat=channel_layouts=mono"
    if channels == 2:
        return "pan=mono|c0=0.5*c0+0.5*c1"
    raise ValueError(f"unsupported source channel count: {channels}")


def base_filter(entry: dict[str, Any], channels: int, policy: dict[str, Any]) -> str:
    output_filter = policy[f"{entry['target_output']}_filter"]
    return ",".join(
        [
            f"atrim=start={entry['start_seconds']}:end={entry['end_seconds']}",
            "asetpts=PTS-STARTPTS",
            mono_filter(channels),
            "aresample=48000:resampler=soxr:precision=28",
            output_filter,
        ]
    )


def render_float_candidate(
    source: Path,
    target: Path,
    entry: dict[str, Any],
    policy: dict[str, Any],
    channels: int,
) -> list[str]:
    base = base_filter(entry, channels, policy)
    command = [str(FFMPEG), "-hide_banner", "-loglevel", "error", "-nostdin", "-y"]
    command += ["-i", str(source)]

    if entry["variant"] == "loop":
        duration = entry["end_seconds"] - entry["start_seconds"]
        crossfade = entry["loop_crossfade_seconds"]
        if duration <= 2.0 * crossfade:
            raise ValueError(f"loop is too short for its crossfade: {entry['asset_id']}")
        middle_end = duration - crossfade
        graph = (
            f"[0:a]{base}[base];"
            "[base]asplit=3[mid_src][tail_src][head_src];"
            f"[mid_src]atrim=start={crossfade}:end={middle_end},"
            "asetpts=PTS-STARTPTS[mid];"
            f"[tail_src]atrim=start={middle_end}:end={duration},"
            "asetpts=PTS-STARTPTS[tail];"
            f"[head_src]atrim=start=0:end={crossfade},"
            "asetpts=PTS-STARTPTS[head];"
            f"[tail][head]acrossfade=d={crossfade}:c1=qsin:c2=qsin[seam];"
            "[mid][seam]concat=n=2:v=0:a=1[out]"
        )
        command += ["-filter_complex", graph, "-map", "[out]"]
    else:
        duration = entry["end_seconds"] - entry["start_seconds"]
        filters = [base]
        fade_in = float(entry.get("fade_in_seconds", 0.0))
        fade_out = float(entry.get("fade_out_seconds", 0.0))
        if fade_in:
            filters.append(f"afade=t=in:st=0:d={fade_in}:curve=qsin")
        if fade_out:
            filters.append(
                f"afade=t=out:st={duration - fade_out}:d={fade_out}:curve=qsin"
            )
        command += ["-af", ",".join(filters)]

    command += [
        "-map_metadata",
        "-1",
        "-fflags",
        "+bitexact",
        "-flags:a",
        "+bitexact",
        "-c:a",
        "pcm_f32le",
        str(target),
    ]
    run(command)
    return command


def loudnorm_measure(path: Path, policy: dict[str, Any]) -> dict[str, float | str]:
    target_i = policy["target_lufs_i"]
    target_tp = policy["max_true_peak_dbtp"]
    result = subprocess.run(
        [
            str(FFMPEG),
            "-hide_banner",
            "-nostats",
            "-nostdin",
            "-i",
            str(path),
            "-af",
            f"loudnorm=I={target_i}:TP={target_tp}:LRA=11:print_format=json",
            "-f",
            "null",
            "-",
        ],
        check=True,
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    matches = re.findall(r"\{\s*\"input_i\".*?\}", result.stderr, re.DOTALL)
    if not matches:
        raise RuntimeError(f"FFmpeg loudnorm emitted no JSON for {path}")
    raw = json.loads(matches[-1])
    numeric = {key: float(value) for key, value in raw.items() if key != "normalization_type"}
    numeric["normalization_type"] = raw["normalization_type"]
    return numeric


def ebur128_measure(path: Path) -> dict[str, float]:
    result = subprocess.run(
        [
            str(FFMPEG),
            "-hide_banner",
            "-nostats",
            "-nostdin",
            "-i",
            str(path),
            "-af",
            "ebur128=peak=sample+true",
            "-f",
            "null",
            "-",
        ],
        check=True,
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    text = result.stderr
    patterns = {
        "integrated_lufs": r"Integrated loudness:\s+I:\s+(-?[\d.]+) LUFS",
        "loudness_range_lu": r"Loudness range:\s+LRA:\s+(-?[\d.]+) LU",
        "sample_peak_dbfs": r"Sample peak:\s+Peak:\s+(-?[\d.]+) dBFS",
        "true_peak_dbtp": r"True peak:\s+Peak:\s+(-?[\d.]+) dBFS",
    }
    measured: dict[str, float] = {}
    for key, pattern in patterns.items():
        matches = re.findall(pattern, text, re.DOTALL)
        if not matches:
            raise RuntimeError(f"FFmpeg ebur128 omitted {key} for {path}")
        measured[key] = float(matches[-1])
    return measured


def render_master(pre_master: Path, target: Path, gain_db: float) -> list[str]:
    command = [
        str(FFMPEG),
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-i",
        str(pre_master),
        "-af",
        f"volume={gain_db:.6f}dB,aresample=48000:osf=s32:dither_method=triangular_hp",
        "-map_metadata",
        "-1",
        "-fflags",
        "+bitexact",
        "-flags:a",
        "+bitexact",
        "-c:a",
        "pcm_s24le",
        str(target),
    ]
    run(command)
    return command


def decode_pcm24(raw: bytes) -> list[int]:
    if len(raw) % 3:
        raise ValueError("24-bit PCM payload is not sample-aligned")
    values: list[int] = []
    for offset in range(0, len(raw), 3):
        value = raw[offset] | raw[offset + 1] << 8 | raw[offset + 2] << 16
        if value & 0x800000:
            value -= 1 << 24
        values.append(value)
    return values


def wav_stats(path: Path, *, loop: bool) -> dict[str, float | int]:
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        width = handle.getsampwidth()
        frames = handle.getnframes()
        rate = handle.getframerate()
        raw = handle.readframes(frames)
    if channels != 1 or width != 3 or rate != 48000:
        raise ValueError(f"unexpected canonical WAV format for {path}")
    values = decode_pcm24(raw)
    scale = float(1 << 23)
    peak = max(abs(value) for value in values) / scale
    dc_offset = sum(values) / (len(values) * scale)
    stats: dict[str, float | int] = {
        "sample_frames": frames,
        "duration_seconds": round(frames / rate, 6),
        "sample_peak_linear": round(peak, 9),
        "dc_offset": round(dc_offset, 9),
        "clipped_sample_count": sum(abs(value) >= (1 << 23) - 1 for value in values),
    }
    if loop:
        stats["loop_boundary_amplitude_delta"] = round(
            abs(values[0] - values[-1]) / scale, 9
        )
        start_slope = values[1] - values[0]
        end_slope = values[-1] - values[-2]
        stats["loop_boundary_slope_delta"] = round(
            abs(start_slope - end_slope) / scale, 9
        )
    return stats


def attribution_text(manifest: dict[str, Any]) -> str:
    by_source: dict[str, dict[str, Any]] = {}
    for entry in manifest["entries"]:
        source = entry["sources"][0]
        record = by_source.setdefault(
            source["source_id"],
            {
                "source": source,
                "changes": set(),
                "files": [],
            },
        )
        record["changes"].add(entry["rights"]["changes_notice"])
        record["files"].append(Path(entry["repo_path"]).name)

    lines = [
        "# Cat-sound attribution and modification notices",
        "",
        "The audio files listed here are third-party Creative Commons works or",
        "derivatives. They are not covered by Neko's root MIT licence. Inclusion",
        "does not imply creator endorsement, and it is not model-training clearance.",
        "",
        "All derivatives are currently bench candidates. They are not approved for",
        "unattended playback until derived listening and final output-hardware tests pass.",
        "",
    ]
    for source_id in sorted(by_source):
        record = by_source[source_id]
        source = record["source"]
        lines += [
            f"## {source['title']} — {source['creator']}",
            "",
            f"- Source: [{source_id}]({source['source_url']})",
            f"- Licence: [{source['license']}]({source['license_url']})",
            f"- Original SHA-256: `{source['source_sha256']}`",
            "- Derived files:",
        ]
        lines += [f"  - `{filename}`" for filename in sorted(record["files"])]
        lines += ["- Changes:"]
        lines += [f"  - {notice}" for notice in sorted(record["changes"])]
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build(temp_root: Path) -> tuple[dict[str, Any], str]:
    recipes = json.loads(RECIPES_PATH.read_text(encoding="utf-8"))
    sources = json.loads(SOURCE_MANIFEST_PATH.read_text(encoding="utf-8"))
    source_by_id = {entry["id"]: entry for entry in sources["entries"]}
    policy = recipes["policy"]
    ffmpeg_version = tool_version(FFMPEG)
    ffprobe_version = tool_version(FFPROBE)
    output_root = temp_root / "derived"
    output_root.mkdir(parents=True)
    entries: list[dict[str, Any]] = []

    for recipe in recipes["entries"]:
        source_record = source_by_id[recipe["source_id"]]
        source_path = ORIGINAL_ROOT / source_record["filename"]
        if sha256_file(source_path) != source_record["sha256"]:
            raise ValueError(f"source hash mismatch: {source_path}")
        source_probe = probe(source_path)
        source_stream = source_probe["streams"][0]
        pre_master = temp_root / f"{recipe['asset_id']}.float.wav"
        target = output_root / recipe["filename"]
        render_float_candidate(
            source_path,
            pre_master,
            recipe,
            policy,
            int(source_stream["channels"]),
        )
        before = loudnorm_measure(pre_master, policy)
        requested_gain = policy["target_lufs_i"] - float(before["input_i"])
        peak_safe_gain = policy["max_true_peak_dbtp"] - float(before["input_tp"])
        applied_gain = min(requested_gain, peak_safe_gain)
        render_master(pre_master, target, applied_gain)
        after_loudnorm = loudnorm_measure(target, policy)
        after_ebur128 = ebur128_measure(target)
        media = wav_stats(target, loop=recipe["variant"] == "loop")
        target_reached = (
            abs(float(after_loudnorm["input_i"]) - policy["target_lufs_i"])
            <= policy["loudness_tolerance_lu"]
        )
        rights = {
            "license": source_record["license"],
            "license_url": source_record["license_url"],
            "creator": source_record["creator"],
            "title": source_record["title"],
            "source_url": source_record["source_url"],
            "attribution_text": (
                f"{source_record['title']} by {source_record['creator']}, "
                f"{source_record['license']}; modified for Neko."
            ),
            "changes_notice": recipe["changes_notice"],
            "commercial_use_allowed": "-NC-" not in source_record["license"],
            "root_mit_license_applies": False,
        }
        source_duration = float(source_probe["format"]["duration"])
        source_info = {
            "source_id": source_record["id"],
            "source_sha256": source_record["sha256"],
            "source_url": source_record["source_url"],
            "creator": source_record["creator"],
            "title": source_record["title"],
            "license": source_record["license"],
            "license_url": source_record["license_url"],
            "decoder": "ffmpeg",
            "decoder_version": ffmpeg_version,
            "decoded_timeline_note": (
                "Times refer to FFmpeg's decoded timeline; compressed-source delay/padding "
                "may differ from the source manifest duration."
            ),
            "source_duration_seconds_probed": round(source_duration, 6),
            "decoded_sample_rate_hz": 48000,
            "start_frame": round(recipe["start_seconds"] * 48000),
            "end_frame": round(recipe["end_seconds"] * 48000),
            "start_seconds": recipe["start_seconds"],
            "end_seconds": recipe["end_seconds"],
        }
        processing = [
            {
                "operation": "trim",
                "parameters": {
                    "start_seconds": recipe["start_seconds"],
                    "end_seconds": recipe["end_seconds"],
                },
            },
            {
                "operation": "downmix",
                "parameters": {"method": mono_filter(int(source_stream["channels"]))},
            },
            {
                "operation": "resample",
                "parameters": {"rate_hz": 48000, "resampler": "soxr", "precision": 28},
            },
            {
                "operation": "output_filter",
                "parameters": {"ffmpeg_filter": policy[f"{recipe['target_output']}_filter"]},
            },
        ]
        if recipe["variant"] == "loop":
            processing.append(
                {
                    "operation": "cyclic_crossfade",
                    "parameters": {
                        "duration_seconds": recipe["loop_crossfade_seconds"],
                        "curves": "qsin/qsin",
                    },
                }
            )
        else:
            processing.append(
                {
                    "operation": "edge_fade",
                    "parameters": {
                        "fade_in_seconds": recipe.get("fade_in_seconds", 0.0),
                        "fade_out_seconds": recipe.get("fade_out_seconds", 0.0),
                        "curve": "qsin",
                    },
                }
            )
        processing += [
            {
                "operation": "linear_gain",
                "parameters": {
                    "requested_gain_db": round(requested_gain, 3),
                    "peak_safe_gain_db": round(peak_safe_gain, 3),
                    "applied_gain_db": round(applied_gain, 3),
                    "peak_limited": applied_gain < requested_gain - 1e-9,
                },
            },
            {
                "operation": "quantize_and_dither",
                "parameters": {
                    "sample_format": "signed_24_bit_pcm",
                    "dither": "ffmpeg_aresample_triangular_hp",
                },
            },
        ]
        for operation in processing:
            operation["tool"] = "ffmpeg"
            operation["tool_version"] = ffmpeg_version
        entry = {
            "asset_id": recipe["asset_id"],
            "recipe_id": recipe["asset_id"],
            "revision": 1,
            "repo_path": f"assets/cat-sounds/derived/{recipe['filename']}",
            "sha256": sha256_file(target),
            "byte_size": target.stat().st_size,
            "container": "wav",
            "codec": "pcm_s24le",
            "sample_rate_hz": 48000,
            "channels": 1,
            "sample_format": "signed_24_bit_pcm",
            **media,
            "semantic_action": recipe["semantic_action"],
            "variant": recipe["variant"],
            "target_output": recipe["target_output"],
            "character_tags": recipe["character_tags"],
            "intensity": recipe["intensity"],
            "sources": [source_info],
            "processing": processing,
            "measured_mastering": {
                "integrated_lufs": float(after_loudnorm["input_i"]),
                "loudness_range_lu": float(after_loudnorm["input_lra"]),
                "true_peak_dbtp": float(after_loudnorm["input_tp"]),
                "independent_ebur128": after_ebur128,
                "target_lufs_i": policy["target_lufs_i"],
                "target_reached": target_reached,
                "target_miss_reason": (
                    None
                    if target_reached
                    else "true_peak_limited_without_destructive_dynamics_processing"
                ),
                "true_peak_ceiling_dbtp": policy["max_true_peak_dbtp"],
                "true_peak_method": "ffmpeg_loudnorm_analysis",
                "independent_method": "ffmpeg_ebur128_peak_sample_and_true",
            },
            "rights": rights,
            "approvals": {
                "source_content_review": "owner_accepted",
                "derived_content_review": "pending",
                "bench_listen": "pending",
                "hardware_acceptance": "pending",
                "release_status": "bench_candidate",
            },
        }
        if recipe["variant"] == "loop":
            entry["loop"] = {
                "loop_start_frame": 0,
                "loop_end_frame": media["sample_frames"],
                "crossfade_frames": round(recipe["loop_crossfade_seconds"] * 48000),
                "listening_approval": "pending",
            }
        entries.append(entry)

    manifest = {
        "schema_version": 1,
        "created_at": recipes["created_at"],
        "asset_root": "assets/cat-sounds/derived",
        "source_manifest": str(SOURCE_MANIFEST_PATH.relative_to(REPO_ROOT)),
        "review_ledger": str(REVIEW_LEDGER_PATH.relative_to(REPO_ROOT)),
        "recipe_file": str(RECIPES_PATH.relative_to(REPO_ROOT)),
        "mastering_policy": {
            **policy,
            "analyzer": "FFmpeg loudnorm plus independent ebur128 peak=sample+true",
            "ffmpeg_version": ffmpeg_version,
            "ffprobe_version": ffprobe_version,
            "ffmpeg_sha256": sha256_file(FFMPEG),
            "true_peak_method_note": (
                "FFmpeg's filters report true peak; this build does not expose an "
                "oversampling-factor field, so no factor is asserted."
            ),
        },
        "root_mit_license_applies": False,
        "runtime_default": "disabled",
        "asset_count": len(entries),
        "content_bytes": sum(entry["byte_size"] for entry in entries),
        "entries": entries,
    }
    return manifest, attribution_text(manifest)


def write_or_check(check: bool) -> None:
    if not FFMPEG.is_file() or not FFPROBE.is_file():
        raise RuntimeError("/usr/bin/ffmpeg and /usr/bin/ffprobe are required")
    with tempfile.TemporaryDirectory(prefix="neko-cat-master-") as directory:
        temp_root = Path(directory)
        manifest, attribution = build(temp_root)
        manifest_text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
        generated_root = temp_root / "derived"
        if check:
            if MANIFEST_PATH.read_text(encoding="utf-8") != manifest_text:
                raise SystemExit("derived manifest differs from a deterministic rebuild")
            if ATTRIBUTION_PATH.read_text(encoding="utf-8") != attribution:
                raise SystemExit("cat-sound attribution differs from a deterministic rebuild")
            expected = {entry["repo_path"] for entry in manifest["entries"]}
            actual = {
                str(path.relative_to(REPO_ROOT))
                for path in DERIVED_ROOT.glob("*.wav")
            }
            if actual != expected:
                raise SystemExit("derived file set differs from the manifest")
            for entry in manifest["entries"]:
                committed = REPO_ROOT / entry["repo_path"]
                generated = generated_root / committed.name
                if sha256_file(committed) != sha256_file(generated):
                    raise SystemExit(f"derived rebuild differs: {committed}")
            print(f"verified {len(manifest['entries'])} deterministic derived assets")
            return

        DERIVED_ROOT.mkdir(parents=True, exist_ok=True)
        expected_names = {entry["repo_path"].split("/")[-1] for entry in manifest["entries"]}
        for stale in DERIVED_ROOT.glob("*.wav"):
            if stale.name not in expected_names:
                stale.unlink()
        for generated in generated_root.glob("*.wav"):
            shutil.copyfile(generated, DERIVED_ROOT / generated.name)
        MANIFEST_PATH.write_text(manifest_text, encoding="utf-8")
        ATTRIBUTION_PATH.write_text(attribution, encoding="utf-8")
        print(
            f"built {len(manifest['entries'])} assets, "
            f"{manifest['content_bytes']} bytes, runtime remains disabled"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="rebuild in a temporary directory and compare with committed outputs",
    )
    return parser.parse_args()


if __name__ == "__main__":
    write_or_check(parse_args().check)
