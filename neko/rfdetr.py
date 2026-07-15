"""RF-DETR preprocessing, decoding, and short-lived person tracking."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

import numpy as np
from PIL import Image


IMAGENET_MEAN = np.asarray((0.485, 0.456, 0.406), dtype=np.float32)
IMAGENET_STD = np.asarray((0.229, 0.224, 0.225), dtype=np.float32)
COCO_PERSON_CLASS_ID = 1


@dataclass(frozen=True, slots=True)
class PersonDetection:
    confidence: float
    xyxy_normalized: tuple[float, float, float, float]

    @property
    def bottom_y_normalized(self) -> float:
        return self.xyxy_normalized[3]

    @property
    def center(self) -> tuple[float, float]:
        left, top, right, bottom = self.xyxy_normalized
        return ((left + right) / 2.0, (top + bottom) / 2.0)


@dataclass(frozen=True, slots=True)
class TrackedPerson:
    track_id: str
    detection: PersonDetection


def preprocess_rgb(frame: np.ndarray, size: int = 384) -> np.ndarray:
    """Match RF-DETR's exported PIL bilinear/ImageNet NCHW input contract."""

    if frame.ndim != 3 or frame.shape[2] != 3 or frame.dtype != np.uint8:
        raise ValueError("frame must be an HWC uint8 RGB array")
    resized = np.asarray(
        Image.fromarray(frame, mode="RGB").resize(
            (size, size), Image.Resampling.BILINEAR
        ),
        dtype=np.float32,
    )
    normalized = (resized / 255.0 - IMAGENET_MEAN) / IMAGENET_STD
    return np.ascontiguousarray(normalized.transpose(2, 0, 1)[None], dtype=np.float32)


def decode_people(
    boxes_cxcywh: np.ndarray,
    logits: np.ndarray,
    threshold: float = 0.60,
) -> tuple[PersonDetection, ...]:
    """Decode sparse-COCO person detections from RF-DETR TensorRT outputs."""

    boxes = np.asarray(boxes_cxcywh)
    scores_raw = np.asarray(logits)
    if boxes.shape != (1, 300, 4) or scores_raw.shape != (1, 300, 91):
        raise ValueError(
            f"unexpected RF-DETR output shapes: {boxes.shape}, {scores_raw.shape}"
        )
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be in [0, 1]")

    # Slot 90 is RF-DETR's no-object slot. COCO category ID 1 is person.
    person_logits = np.clip(scores_raw[0, :, COCO_PERSON_CLASS_ID], -88.0, 88.0)
    scores = 1.0 / (1.0 + np.exp(-person_logits))
    people: list[PersonDetection] = []
    for box, score in zip(boxes[0], scores):
        if float(score) < threshold:
            continue
        cx, cy, width, height = (float(value) for value in box)
        xyxy = (
            max(0.0, min(1.0, cx - width / 2.0)),
            max(0.0, min(1.0, cy - height / 2.0)),
            max(0.0, min(1.0, cx + width / 2.0)),
            max(0.0, min(1.0, cy + height / 2.0)),
        )
        people.append(PersonDetection(float(score), xyxy))
    return tuple(sorted(people, key=lambda item: item.confidence, reverse=True))


@dataclass(slots=True)
class _Track:
    center: tuple[float, float]
    last_frame: int


class CentroidPersonTracker:
    """Small metadata-only tracker for the low-rate parked greeting pipeline."""

    def __init__(self, max_center_distance: float = 0.20, stale_frames: int = 5) -> None:
        if max_center_distance <= 0 or stale_frames < 1:
            raise ValueError("tracker limits must be positive")
        self.max_center_distance = max_center_distance
        self.stale_frames = stale_frames
        self.frame_number = 0
        self.next_id = 1
        self._tracks: dict[str, _Track] = {}

    def update(self, detections: Iterable[PersonDetection]) -> tuple[TrackedPerson, ...]:
        self.frame_number += 1
        detections = tuple(detections)
        unmatched_tracks = set(self._tracks)
        assigned: list[TrackedPerson] = []

        for detection in sorted(detections, key=lambda item: item.confidence, reverse=True):
            center = detection.center
            candidates = []
            for track_id in unmatched_tracks:
                old = self._tracks[track_id].center
                distance = math.hypot(center[0] - old[0], center[1] - old[1])
                if distance <= self.max_center_distance:
                    candidates.append((distance, track_id))
            if candidates:
                _, track_id = min(candidates)
                unmatched_tracks.remove(track_id)
            else:
                track_id = f"person-{self.next_id}"
                self.next_id += 1
            self._tracks[track_id] = _Track(center, self.frame_number)
            assigned.append(TrackedPerson(track_id, detection))

        for track_id, track in tuple(self._tracks.items()):
            if self.frame_number - track.last_frame > self.stale_frames:
                del self._tracks[track_id]
        return tuple(assigned)
