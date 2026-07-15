"""Deterministic conversation and social policy shared by all transports."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from .events import (
    Acknowledge,
    CancelAudio,
    DialogueRequest,
    GreetingRequest,
    InputEvent,
    OutputAction,
    PersonGone,
    PersonObservation,
    SetMuted,
    SetParked,
    SpeakText,
    TranscriptEvent,
)


_SPACE = re.compile(r"\s+")
_PUNCTUATION = re.compile(r"[^\w\s]", re.UNICODE)


def normalize_phrase(text: str) -> str:
    return _SPACE.sub(" ", _PUNCTUATION.sub(" ", text.casefold())).strip()


@dataclass(frozen=True, slots=True)
class BehaviorConfig:
    wake_phrase: str = "neko neko"
    session_timeout_s: float = 30.0
    person_confidence_min: float = 0.60
    person_stable_observations_min: int = 3
    person_dwell_min_s: float = 1.5
    social_distance_min_m: float = 1.2
    social_distance_max_m: float = 3.05
    greeting_global_cooldown_s: float = 30.0
    greeting_track_cooldown_s: float = 300.0

    def __post_init__(self) -> None:
        positive = {
            "session_timeout_s": self.session_timeout_s,
            "person_dwell_min_s": self.person_dwell_min_s,
            "social_distance_min_m": self.social_distance_min_m,
            "social_distance_max_m": self.social_distance_max_m,
            "greeting_global_cooldown_s": self.greeting_global_cooldown_s,
            "greeting_track_cooldown_s": self.greeting_track_cooldown_s,
        }
        if any(value <= 0 for value in positive.values()):
            raise ValueError("behavior timing and distance values must be positive")
        if self.social_distance_min_m >= self.social_distance_max_m:
            raise ValueError("social distance minimum must be below maximum")
        if not 0 <= self.person_confidence_min <= 1:
            raise ValueError("person confidence must be in [0, 1]")
        if self.person_stable_observations_min < 1:
            raise ValueError("stable observation count must be positive")


class BehaviorController:
    """Pure state machine; callers perform I/O for returned actions."""

    def __init__(self, config: BehaviorConfig | None = None) -> None:
        self.config = config or BehaviorConfig()
        self.muted = False
        self.parked = False
        self.session_deadline_s: float | None = None
        self.last_global_greeting_s: float | None = None
        self.track_greetings_s: dict[tuple[str, str], float] = {}

    @property
    def session_active(self) -> bool:
        return self.session_deadline_s is not None

    def handle(self, event: InputEvent) -> tuple[OutputAction, ...]:
        if isinstance(event, TranscriptEvent):
            return self._handle_transcript(event)
        if isinstance(event, PersonObservation):
            return self._handle_person(event)
        if isinstance(event, PersonGone):
            return ()
        if isinstance(event, SetParked):
            self.parked = event.parked
            return ()
        raise TypeError(f"unsupported event: {type(event).__name__}")

    def _handle_transcript(self, event: TranscriptEvent) -> tuple[OutputAction, ...]:
        self._expire_session(event.monotonic_s)
        normalized = normalize_phrase(event.text)
        if not normalized:
            return ()
        if normalized in {"stop", "cancel", "stop talking", "be quiet"}:
            self.session_deadline_s = None
            return (CancelAudio(reason="voice-command"),)
        if normalized in {"mute", "mute microphone", "privacy mode"}:
            self.muted = True
            self.session_deadline_s = None
            return (CancelAudio(reason="mute"), SetMuted(muted=True))
        if normalized in {"unmute", "unmute microphone"}:
            self.muted = False
            return (SetMuted(muted=False), SpeakText("I'm listening again.", event.language))
        if self.muted:
            return ()

        wake = normalize_phrase(self.config.wake_phrase)
        if not self.session_active:
            if wake not in normalized:
                return ()
            self.session_deadline_s = event.monotonic_s + self.config.session_timeout_s
            remainder = normalized.replace(wake, "", 1).strip()
            if not remainder:
                return (Acknowledge(),)
            return (Acknowledge(), DialogueRequest(remainder, event.language))

        self.session_deadline_s = event.monotonic_s + self.config.session_timeout_s
        return (DialogueRequest(event.text.strip(), event.language),)

    def _handle_person(self, event: PersonObservation) -> tuple[OutputAction, ...]:
        self._expire_session(event.monotonic_s)
        if self.muted or not self.parked or self.session_active:
            return ()
        cfg = self.config
        if event.confidence < cfg.person_confidence_min:
            return ()
        if event.stable_observations < cfg.person_stable_observations_min:
            return ()
        if event.dwell_s < cfg.person_dwell_min_s or not event.approaching:
            return ()
        distance = event.estimated_distance_m
        if distance is None or not cfg.social_distance_min_m <= distance <= cfg.social_distance_max_m:
            return ()
        if (
            self.last_global_greeting_s is not None
            and event.monotonic_s - self.last_global_greeting_s
            < cfg.greeting_global_cooldown_s
        ):
            return ()
        key = (event.camera_id, event.track_id)
        previous = self.track_greetings_s.get(key)
        if previous is not None and event.monotonic_s - previous < cfg.greeting_track_cooldown_s:
            return ()
        self.last_global_greeting_s = event.monotonic_s
        self.track_greetings_s[key] = event.monotonic_s
        return (GreetingRequest(event.camera_id, event.track_id, distance),)

    def _expire_session(self, monotonic_s: float) -> None:
        if self.session_deadline_s is not None and monotonic_s > self.session_deadline_s:
            self.session_deadline_s = None

    def handle_many(self, events: Iterable[InputEvent]) -> tuple[OutputAction, ...]:
        actions: list[OutputAction] = []
        for event in events:
            actions.extend(self.handle(event))
        return tuple(actions)
