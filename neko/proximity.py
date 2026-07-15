"""Frame-free proximity metadata conversion for ephemeral detector tracks."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Iterable

from .events import PersonGone, PersonObservation


@dataclass(frozen=True, slots=True)
class DetectorTrack:
    camera_id: str
    track_id: str
    confidence: float
    monotonic_s: float
    bottom_y_normalized: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be in [0, 1]")
        if not 0.0 <= self.bottom_y_normalized <= 1.0:
            raise ValueError("bottom y must be in [0, 1]")


@dataclass(frozen=True, slots=True)
class GroundPlaneCalibration:
    """Piecewise-linear distance lookup for one fixed, parked camera pose."""

    points: tuple[tuple[float, float], ...]

    def __post_init__(self) -> None:
        if len(self.points) < 2:
            raise ValueError("at least two calibration points are required")
        ys = [point[0] for point in self.points]
        distances = [point[1] for point in self.points]
        if any(not 0.0 <= value <= 1.0 for value in ys):
            raise ValueError("calibration y values must be normalized")
        if ys != sorted(ys) or len(set(ys)) != len(ys):
            raise ValueError("calibration y values must be unique and increasing")
        if any(value <= 0 for value in distances):
            raise ValueError("calibration distances must be positive")

    def estimate_m(self, bottom_y_normalized: float) -> float | None:
        if bottom_y_normalized < self.points[0][0] or bottom_y_normalized > self.points[-1][0]:
            return None
        for (left_y, left_m), (right_y, right_m) in zip(self.points, self.points[1:]):
            if left_y <= bottom_y_normalized <= right_y:
                fraction = (bottom_y_normalized - left_y) / (right_y - left_y)
                return left_m + fraction * (right_m - left_m)
        return None


@dataclass(slots=True)
class _TrackState:
    first_seen_s: float
    last_seen_s: float
    observations: int = 0
    recent_distances_m: deque[float] = field(default_factory=lambda: deque(maxlen=5))


class ProximityEstimator:
    """Converts tracker metadata to policy events without storing imagery."""

    def __init__(
        self,
        calibrations: dict[str, GroundPlaneCalibration],
        approach_delta_m: float = 0.25,
        stale_after_s: float = 2.0,
    ) -> None:
        if approach_delta_m <= 0 or stale_after_s <= 0:
            raise ValueError("approach delta and stale timeout must be positive")
        self.calibrations = dict(calibrations)
        self.approach_delta_m = approach_delta_m
        self.stale_after_s = stale_after_s
        self._tracks: dict[tuple[str, str], _TrackState] = {}

    def observe(self, detection: DetectorTrack) -> PersonObservation:
        key = (detection.camera_id, detection.track_id)
        state = self._tracks.get(key)
        if state is None:
            state = _TrackState(detection.monotonic_s, detection.monotonic_s)
            self._tracks[key] = state
        if detection.monotonic_s < state.last_seen_s:
            raise ValueError("track observations must be monotonic")
        state.last_seen_s = detection.monotonic_s
        state.observations += 1
        calibration = self.calibrations.get(detection.camera_id)
        distance = (
            calibration.estimate_m(detection.bottom_y_normalized) if calibration else None
        )
        if distance is not None:
            state.recent_distances_m.append(distance)
        approaching = (
            len(state.recent_distances_m) >= 3
            and state.recent_distances_m[0] - state.recent_distances_m[-1]
            >= self.approach_delta_m
        )
        return PersonObservation(
            camera_id=detection.camera_id,
            track_id=detection.track_id,
            confidence=detection.confidence,
            monotonic_s=detection.monotonic_s,
            stable_observations=state.observations,
            dwell_s=detection.monotonic_s - state.first_seen_s,
            estimated_distance_m=distance,
            approaching=approaching,
        )

    def expire(self, monotonic_s: float) -> tuple[PersonGone, ...]:
        gone: list[PersonGone] = []
        for key, state in tuple(self._tracks.items()):
            if monotonic_s - state.last_seen_s >= self.stale_after_s:
                camera_id, track_id = key
                gone.append(PersonGone(camera_id, track_id, monotonic_s))
                del self._tracks[key]
        return tuple(gone)

    def observe_many(self, detections: Iterable[DetectorTrack]) -> tuple[PersonObservation, ...]:
        return tuple(self.observe(detection) for detection in detections)
