"""Typed, media-free events exchanged by Neko's local workers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias


Language = Literal["en", "fr", "es", "unknown"]


@dataclass(frozen=True, slots=True)
class TranscriptEvent:
    """A final local transcript; raw audio is never part of this event."""

    text: str
    language: Language
    monotonic_s: float


@dataclass(frozen=True, slots=True)
class PersonObservation:
    """Ephemeral detector/tracker metadata with no image or identity payload."""

    camera_id: str
    track_id: str
    confidence: float
    monotonic_s: float
    stable_observations: int
    dwell_s: float
    estimated_distance_m: float | None
    approaching: bool


@dataclass(frozen=True, slots=True)
class PersonGone:
    camera_id: str
    track_id: str
    monotonic_s: float


@dataclass(frozen=True, slots=True)
class SetParked:
    parked: bool
    monotonic_s: float


InputEvent: TypeAlias = TranscriptEvent | PersonObservation | PersonGone | SetParked


@dataclass(frozen=True, slots=True)
class Acknowledge:
    sound_id: str = "wake-chirp"


@dataclass(frozen=True, slots=True)
class CancelAudio:
    reason: str


@dataclass(frozen=True, slots=True)
class SetMuted:
    muted: bool


@dataclass(frozen=True, slots=True)
class DialogueRequest:
    text: str
    language: Language


@dataclass(frozen=True, slots=True)
class SpeakText:
    text: str
    language: Language = "en"
    category: Literal["system", "greeting", "fallback"] = "system"


@dataclass(frozen=True, slots=True)
class GreetingRequest:
    camera_id: str
    track_id: str
    estimated_distance_m: float | None


OutputAction: TypeAlias = (
    Acknowledge | CancelAudio | SetMuted | DialogueRequest | SpeakText | GreetingRequest
)
