"""Fail-closed selection and playback for Neko's curated cat sounds."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import random
import re
import subprocess
import threading
import time
from typing import Callable, Literal


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "assets/cat-sounds/derived/manifest.json"
DEFAULT_ALLOWLIST = REPO_ROOT / "config/cat-sounds/runtime-allowlist.json"
MARKER_ACTIONS = {"meow": "meow_general", "purr": "purr_short"}
MARKER_RE = re.compile(r"\[(meow|purr)\]", re.IGNORECASE)
OutputName = Literal["speaker", "body_transducer"]


def db_to_linear(db: float) -> float:
    """Convert an amplitude gain in decibels to a linear multiplier."""

    if not math.isfinite(db):
        raise ValueError("gain must be finite")
    return 10.0 ** (db / 20.0)


def peak_limited_gain_db(
    track_gain_db: float,
    sample_peak: float,
    master_linear: float,
    *,
    peak_ceiling_dbfs: float = -1.0,
) -> float:
    """Return requested ReplayGain reduced only to respect the peak ceiling."""

    if not math.isfinite(track_gain_db):
        raise ValueError("track gain must be finite")
    if not math.isfinite(sample_peak) or not 0.0 < sample_peak <= 1.0:
        raise ValueError("sample peak must be finite and in (0, 1]")
    if not math.isfinite(master_linear) or master_linear <= 0.0:
        raise ValueError("master must be finite and positive")
    if not math.isfinite(peak_ceiling_dbfs) or peak_ceiling_dbfs > 0.0:
        raise ValueError("peak ceiling must be finite and no greater than 0 dBFS")
    ceiling_linear = db_to_linear(peak_ceiling_dbfs)
    safe_gain_db = 20.0 * math.log10(ceiling_linear / (master_linear * sample_peak))
    return min(track_gain_db, safe_gain_db)


def playback_multiplier(
    track_gain_db: float,
    sample_peak: float,
    master_linear: float,
    *,
    peak_ceiling_dbfs: float = -1.0,
) -> tuple[float, float, float]:
    """Return ``(multiplier, applied_gain_db, predicted_output_peak)``."""

    applied_gain_db = peak_limited_gain_db(
        track_gain_db,
        sample_peak,
        master_linear,
        peak_ceiling_dbfs=peak_ceiling_dbfs,
    )
    multiplier = master_linear * db_to_linear(applied_gain_db)
    return multiplier, applied_gain_db, sample_peak * multiplier


class CatAudioDenied(RuntimeError):
    """Raised when a sound request is not approved by deterministic policy."""


@dataclass(frozen=True)
class TextPart:
    text: str


@dataclass(frozen=True)
class CatSoundPart:
    action: str
    fallback_text: str


AudioPart = TextPart | CatSoundPart


@dataclass(frozen=True)
class CatSoundSelection:
    action: str
    asset_id: str
    path: Path
    output: OutputName
    gain_db: float
    duration_seconds: float
    interruptible: bool


def parse_audio_script(text: str, *, max_markers: int = 2) -> tuple[AudioPart, ...]:
    """Split strict expressive markers from text without treating prose as actions."""

    if max_markers < 0:
        raise ValueError("max_markers must not be negative")
    parts: list[AudioPart] = []
    cursor = 0
    markers = 0
    for match in MARKER_RE.finditer(text):
        if markers >= max_markers:
            break
        before = text[cursor : match.start()].strip()
        if before:
            parts.append(TextPart(before))
        name = match.group(1).lower()
        parts.append(CatSoundPart(MARKER_ACTIONS[name], name))
        markers += 1
        cursor = match.end()
    tail = text[cursor:].strip()
    if tail:
        parts.append(TextPart(tail))
    return tuple(parts) or (TextPart(text.strip()),)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class CatSoundCatalog:
    """Validate semantic requests and choose approved weighted variants."""

    def __init__(
        self,
        manifest_path: Path = DEFAULT_MANIFEST,
        allowlist_path: Path = DEFAULT_ALLOWLIST,
        *,
        repo_root: Path = REPO_ROOT,
        rng: random.Random | None = None,
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.allowlist = json.loads(allowlist_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if self.allowlist.get("default_policy") != "deny":
            raise ValueError("cat-sound policy must default to deny")
        self.runtime_enabled = self.allowlist.get("runtime_status") == "enabled"
        self.assets = {entry["asset_id"]: entry for entry in manifest["entries"]}
        if len(self.assets) != len(manifest["entries"]):
            raise ValueError("duplicate cat-sound asset ID")
        self.rng = rng or random.SystemRandom()
        self.last_asset: dict[tuple[str, str], str] = {}
        self.last_played: dict[tuple[str, str], float] = {}

    def select(
        self,
        action: str,
        output: OutputName,
        *,
        now: float | None = None,
        autonomous: bool = True,
    ) -> CatSoundSelection:
        policy = self.allowlist.get("actions", {}).get(action)
        if not self.runtime_enabled:
            raise CatAudioDenied("cat-sound runtime is disabled")
        if not isinstance(policy, dict):
            raise CatAudioDenied(f"unknown cat-sound action: {action}")
        if not policy.get("enabled"):
            raise CatAudioDenied(f"cat-sound action is disabled: {action}")
        if autonomous and not policy.get("autonomous_allowed"):
            raise CatAudioDenied(f"cat-sound action is not approved for autonomy: {action}")
        if output not in policy.get("allowed_outputs", []):
            raise CatAudioDenied(f"cat-sound output is denied: {output}")

        moment = time.monotonic() if now is None else now
        key = (action, output)
        cooldown = float(policy["cooldown_seconds"])
        if moment - self.last_played.get(key, -math.inf) < cooldown:
            raise CatAudioDenied(f"cat-sound action is cooling down: {action}")

        candidates: list[tuple[dict, dict]] = []
        for candidate in policy.get("candidates", []):
            asset = self.assets.get(candidate.get("asset_id"))
            if asset is None or asset.get("target_output") != output:
                continue
            approvals = asset.get("approvals", {})
            if approvals.get("derived_content_review") != "accepted":
                continue
            if approvals.get("hardware_acceptance") != "accepted":
                continue
            if approvals.get("release_status") != "accepted":
                continue
            if float(asset["duration_seconds"]) > float(policy["max_duration_seconds"]):
                continue
            weight = candidate.get("weight")
            if not isinstance(weight, (int, float)) or weight <= 0:
                continue
            candidates.append((candidate, asset))
        if not candidates:
            raise CatAudioDenied(f"no approved cat-sound candidate: {action}/{output}")

        previous = self.last_asset.get(key)
        nonrepeating = [item for item in candidates if item[1]["asset_id"] != previous]
        pool = nonrepeating or candidates
        chosen_candidate, chosen_asset = self.rng.choices(
            pool,
            weights=[float(item[0]["weight"]) for item in pool],
            k=1,
        )[0]
        del chosen_candidate

        path = (self.repo_root / chosen_asset["repo_path"]).resolve()
        try:
            path.relative_to(self.repo_root)
        except ValueError as error:
            raise CatAudioDenied("cat-sound asset escapes repository root") from error
        if not path.is_file() or _sha256(path) != chosen_asset["sha256"]:
            raise CatAudioDenied(f"cat-sound asset failed integrity: {chosen_asset['asset_id']}")

        gain_db = float(policy["default_gain_db"])
        if not float(policy["min_gain_db"]) <= gain_db <= float(policy["max_gain_db"]):
            raise CatAudioDenied(f"cat-sound fixed gain is outside policy: {action}")
        return CatSoundSelection(
            action=action,
            asset_id=chosen_asset["asset_id"],
            path=path,
            output=output,
            gain_db=gain_db,
            duration_seconds=float(chosen_asset["duration_seconds"]),
            interruptible=bool(policy["interruptible"]),
        )

    def mark_played(self, selection: CatSoundSelection, *, now: float | None = None) -> None:
        key = (selection.action, selection.output)
        self.last_asset[key] = selection.asset_id
        self.last_played[key] = time.monotonic() if now is None else now


class CatSoundPlayer:
    """Play a selected lossless asset through PipeWire with cancellation."""

    def __init__(self, targets: dict[OutputName, str | None] | None = None) -> None:
        self.targets = targets or {"speaker": None, "body_transducer": None}

    def play(
        self,
        selection: CatSoundSelection,
        *,
        cancel_event: threading.Event,
        on_started: Callable[[], None] | None = None,
    ) -> bool:
        if cancel_event.is_set():
            return False
        volume = min(1.0, 10 ** (selection.gain_db / 20.0))
        command = [
            "/usr/bin/pw-play",
            "--volume",
            f"{volume:.6f}",
            "--latency",
            "100ms",
        ]
        target = self.targets.get(selection.output)
        if target:
            command.extend(["--target", target])
        command.append(str(selection.path))
        process = subprocess.Popen(command)
        if on_started is not None:
            on_started()
        while process.poll() is None:
            if cancel_event.wait(0.02):
                process.terminate()
                try:
                    process.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=1.0)
                return False
        if process.returncode != 0:
            raise RuntimeError(f"cat-sound player exited {process.returncode}")
        return True
