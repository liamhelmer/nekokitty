#!/usr/bin/env python3
"""Ephemeral webcam person/proximity smoke loop using RF-DETR TensorRT."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neko.proximity import DetectorTrack, GroundPlaneCalibration, ProximityEstimator
from neko.rfdetr import CentroidPersonTracker, decode_people, preprocess_rgb
from neko.tensorrt_engine import TensorRTEngine


DEFAULT_PLAN = Path("/home/neko/models/rfdetr-nano/export-384/rfdetr-nano-b1-384-fp16.plan")
DEFAULT_PLAN_SHA256 = "4b61a08b03cc63889ec590414c3b4d5fef696b4da33ede6bfb2b675a7b656c00"


def parse_calibration(value: str) -> GroundPlaneCalibration:
    points = []
    for pair in value.split(","):
        y_text, distance_text = pair.split(":", 1)
        points.append((float(y_text), float(distance_text)))
    return GroundPlaneCalibration(tuple(points))


def camera_process(device: str, width: int, height: int) -> subprocess.Popen[bytes]:
    command = [
        "gst-launch-1.0", "-q", "v4l2src", f"device={device}",
        "!", f"video/x-raw,width={width},height={height},framerate=30/1",
        "!", "videoconvert", "!", "video/x-raw,format=RGB",
        "!", "fdsink", "fd=1", "sync=false",
    ]
    return subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def read_exact(stream: object, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        chunk = stream.read(size - len(chunks))  # type: ignore[attr-defined]
        if not chunk:
            raise EOFError("camera stream ended")
        chunks.extend(chunk)
    return bytes(chunks)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", default="/dev/video0")
    parser.add_argument("--camera-id", default="smoke-camera")
    parser.add_argument("--seconds", type=float, default=15.0)
    parser.add_argument("--rate", type=float, default=5.0)
    parser.add_argument("--threshold", type=float, default=0.60)
    parser.add_argument(
        "--calibration",
        help="measured normalized-bottom-y:metres pairs, e.g. 0.25:3.05,0.90:1.20",
    )
    args = parser.parse_args()
    if args.seconds <= 0 or args.rate <= 0:
        parser.error("seconds and rate must be positive")

    width, height = 640, 360
    process = camera_process(args.device, width, height)
    assert process.stdout is not None
    calibration = parse_calibration(args.calibration) if args.calibration else None
    estimator = ProximityEstimator({args.camera_id: calibration} if calibration else {})
    tracker = CentroidPersonTracker()
    deadline = time.monotonic() + args.seconds
    next_inference = 0.0
    try:
        with TensorRTEngine(DEFAULT_PLAN, DEFAULT_PLAN_SHA256) as engine:
            while time.monotonic() < deadline:
                raw = read_exact(process.stdout, width * height * 3)
                now = time.monotonic()
                if now < next_inference:
                    continue
                next_inference = now + 1.0 / args.rate
                frame = np.frombuffer(raw, dtype=np.uint8).reshape(height, width, 3)
                outputs = engine.infer("input", preprocess_rgb(frame))
                people = decode_people(outputs["dets"], outputs["labels"], args.threshold)
                tracked = tracker.update(people)
                observations = estimator.observe_many(
                    DetectorTrack(
                        args.camera_id,
                        item.track_id,
                        item.detection.confidence,
                        now,
                        item.detection.bottom_y_normalized,
                    )
                    for item in tracked
                )
                print(json.dumps({
                    "monotonic_s": round(now, 3),
                    "people": [
                        {
                            "track_id": item.track_id,
                            "confidence": round(item.confidence, 3),
                            "bottom_y_normalized": (
                                None
                                if item.bottom_y_normalized is None
                                else round(item.bottom_y_normalized, 3)
                            ),
                            "distance_m": None if item.estimated_distance_m is None else round(item.estimated_distance_m, 2),
                            "approaching": item.approaching,
                        }
                        for item in observations
                    ],
                    "distance_gate": "calibrated" if calibration else "disabled",
                }), flush=True)
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
