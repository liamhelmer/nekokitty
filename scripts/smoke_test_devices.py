#!/usr/bin/env python3
"""Exercise Neko's replaceable camera, audio, and local-model boundaries.

The default ``all`` run never records media and never plays sound. Camera frames
and microphone samples terminate at GStreamer ``fakesink`` elements; only device
metadata, timing, and microphone RMS levels are returned. Use ``--audible``
explicitly to add a quiet playback test.

This deliberately uses only Python's standard library plus the GStreamer, ALSA,
and PipeWire tools already shipped on the Jetson. It is a bench acceptance
harness, not the eventual real-time assistant pipeline.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import glob
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time
from typing import Any, Sequence
from urllib import error as urlerror
from urllib import request as urlrequest


DEFAULT_GEMMA_URL = "http://127.0.0.1:9379"
DEFAULT_MODEL = "gemma-4-e2b-it"
DEFAULT_CAMERA_SIZE = (672, 384)


@dataclass(frozen=True)
class AlsaDevice:
    direction: str
    card: int
    card_id: str
    card_name: str
    device: int
    device_name: str

    @property
    def spec(self) -> str:
        return f"plughw:CARD={self.card_id},DEV={self.device}"

    @property
    def label(self) -> str:
        return f"{self.card_name} / {self.device_name}"


def run_text(command: Sequence[str], timeout: float = 10.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command), check=False, capture_output=True, text=True, timeout=timeout
    )


def tool_version(command: str, args: Sequence[str]) -> dict[str, Any]:
    path = shutil.which(command)
    if path is None:
        return {"available": False, "path": None, "version": None}
    result = run_text([path, *args])
    first_line = (result.stdout or result.stderr).splitlines()
    return {
        "available": True,
        "path": path,
        "version": first_line[0].strip() if first_line else None,
    }


def stable_links_for(device: Path, link_root: Path) -> list[str]:
    links: list[str] = []
    if not link_root.is_dir():
        return links
    for candidate in sorted(link_root.iterdir()):
        try:
            if candidate.resolve() == device.resolve():
                links.append(str(candidate))
        except OSError:
            continue
    return links


def video_devices() -> list[dict[str, Any]]:
    devices: list[dict[str, Any]] = []
    for raw_path in sorted(glob.glob("/dev/video*")):
        path = Path(raw_path)
        sys_name = Path("/sys/class/video4linux") / path.name / "name"
        try:
            name = sys_name.read_text(encoding="utf-8").strip()
        except OSError:
            name = "unknown"
        devices.append(
            {
                "device": str(path),
                "name": name,
                "stable_links": stable_links_for(path, Path("/dev/v4l/by-id")),
            }
        )
    return devices


ALSA_LINE = re.compile(
    r"^card\s+(?P<card>\d+):\s+(?P<card_id>\S+)\s+\[(?P<card_name>.*?)\],\s+"
    r"device\s+(?P<device>\d+):\s+(?P<device_name>.*?)\s+\["
)


def parse_alsa_devices(output: str, direction: str) -> list[AlsaDevice]:
    devices: list[AlsaDevice] = []
    for line in output.splitlines():
        match = ALSA_LINE.match(line)
        if not match:
            continue
        fields = match.groupdict()
        devices.append(
            AlsaDevice(
                direction=direction,
                card=int(fields["card"]),
                card_id=fields["card_id"],
                card_name=fields["card_name"].strip(),
                device=int(fields["device"]),
                device_name=fields["device_name"].strip(),
            )
        )
    return devices


def alsa_devices(direction: str) -> list[AlsaDevice]:
    if direction not in {"capture", "playback"}:
        raise ValueError(f"unknown ALSA direction: {direction}")
    command = "arecord" if direction == "capture" else "aplay"
    if shutil.which(command) is None:
        return []
    result = run_text([command, "-l"])
    return parse_alsa_devices(result.stdout, direction)


def pipewire_status() -> str | None:
    if shutil.which("wpctl") is None:
        return None
    result = run_text(["wpctl", "status"])
    return result.stdout.strip() if result.returncode == 0 else None


def inventory() -> dict[str, Any]:
    captures = alsa_devices("capture")
    playbacks = alsa_devices("playback")
    return {
        "tools": {
            "gstreamer": tool_version("gst-launch-1.0", ["--version"]),
            "pipewire": tool_version("pw-cli", ["--version"]),
            "alsa_capture": tool_version("arecord", ["--version"]),
            "alsa_playback": tool_version("aplay", ["--version"]),
        },
        "video": video_devices(),
        "audio_capture": [asdict(item) | {"spec": item.spec} for item in captures],
        "audio_playback": [asdict(item) | {"spec": item.spec} for item in playbacks],
        "pipewire_status": pipewire_status(),
    }


def choose_video_device(match: str | None) -> dict[str, Any] | None:
    devices = video_devices()
    if match:
        needle = match.casefold()
        devices = [
            device
            for device in devices
            if needle
            in (
                device["name"]
                + " "
                + device["device"]
                + " "
                + " ".join(device["stable_links"])
            ).casefold()
        ]
    if not devices:
        return None
    return next(
        (
            device
            for device in devices
            if any("index0" in link for link in device["stable_links"])
        ),
        devices[0],
    )


def choose_alsa_device(direction: str, match: str | None) -> AlsaDevice | None:
    devices = alsa_devices(direction)
    if match:
        needle = match.casefold()
        devices = [
            item
            for item in devices
            if needle in (item.label + " " + item.spec).casefold()
        ]
    else:
        external = [
            item
            for item in devices
            if "ape" not in item.label.casefold()
            and "hdmi" not in item.label.casefold()
        ]
        devices = external
    return devices[0] if devices else None


def require_gstreamer() -> str:
    executable = shutil.which("gst-launch-1.0")
    if executable is None:
        raise RuntimeError("gst-launch-1.0 is not installed")
    return executable


def gst_result(started: float, completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    combined = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    errors = [line.strip() for line in combined.splitlines() if "ERROR" in line.upper()]
    return {
        "ok": completed.returncode == 0 and not errors,
        "elapsed_s": round(time.monotonic() - started, 3),
        "returncode": completed.returncode,
        "errors": errors[-8:],
    }


def smoke_synthetic(frames: int = 60) -> dict[str, Any]:
    gst = require_gstreamer()
    command = [
        gst,
        "-q",
        "videotestsrc",
        f"num-buffers={frames}",
        "is-live=false",
        "!",
        "videoconvert",
        "!",
        f"video/x-raw,width={DEFAULT_CAMERA_SIZE[0]},height={DEFAULT_CAMERA_SIZE[1]},format=RGB",
        "!",
        "fakesink",
        "sync=false",
        "audiotestsrc",
        f"num-buffers={frames}",
        "is-live=false",
        "!",
        "audioconvert",
        "!",
        "audioresample",
        "!",
        "audio/x-raw,rate=16000,channels=1,format=S16LE",
        "!",
        "fakesink",
        "sync=false",
    ]
    started = time.monotonic()
    completed = run_text(command, timeout=30)
    result = gst_result(started, completed)
    result.update({"video_frames": frames, "audio_buffers": frames})
    return result


def smoke_camera(match: str | None, frames: int, width: int, height: int) -> dict[str, Any]:
    selected = choose_video_device(match)
    if selected is None:
        return {"ok": False, "skipped": True, "reason": "no matching V4L2 camera"}
    gst = require_gstreamer()
    command = [
        gst,
        "-q",
        "v4l2src",
        f"device={selected['device']}",
        f"num-buffers={frames}",
        "!",
        # Force the widely supported uncompressed UVC mode. Jetson's ranked
        # decodebin otherwise selects nvjpegdec for the C922 MJPEG stream; that
        # path failed negotiation on the live R39.2 host.
        "video/x-raw,format=YUY2,width=640,height=360,framerate=30/1",
        "!",
        # Centre-crop 16:9 to the engine's 7:4 aspect ratio before resizing.
        "videocrop",
        "left=5",
        "right=5",
        "!",
        "videoconvert",
        "!",
        "videoscale",
        "!",
        f"video/x-raw,width={width},height={height},format=RGB,pixel-aspect-ratio=1/1",
        "!",
        "fakesink",
        "sync=false",
    ]
    started = time.monotonic()
    completed = run_text(command, timeout=max(20, frames * 2))
    result = gst_result(started, completed)
    result.update(
        {
            "device": selected["device"],
            "name": selected["name"],
            "frames": frames,
            "target_width": width,
            "target_height": height,
            "effective_fps": round(frames / result["elapsed_s"], 2)
            if result["elapsed_s"]
            else None,
            "media_retained": False,
        }
    )
    return result


RMS_PATTERN = re.compile(
    r"rms=\(GValueArray\)<\s*([-+]?(?:\d+(?:\.\d+)?|inf))",
    re.IGNORECASE,
)


def run_for_duration(command: Sequence[str], duration: float) -> tuple[int, str, float]:
    started = time.monotonic()
    process = subprocess.Popen(
        list(command),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=duration)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGINT)
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            stdout, stderr = process.communicate(timeout=5)
    return process.returncode, "\n".join((stdout, stderr)), time.monotonic() - started


def smoke_microphone(match: str | None, duration: float) -> dict[str, Any]:
    selected = choose_alsa_device("capture", match)
    if selected is None:
        return {
            "ok": False,
            "skipped": True,
            "reason": "no matching external ALSA capture device",
        }
    gst = require_gstreamer()
    command = [
        gst,
        "-m",
        "alsasrc",
        f"device={selected.spec}",
        "!",
        "audioconvert",
        "!",
        "audioresample",
        "!",
        "audio/x-raw,rate=16000,channels=1,format=S16LE",
        "!",
        "level",
        "interval=100000000",
        "post-messages=true",
        "!",
        "fakesink",
        "sync=false",
    ]
    returncode, output, elapsed = run_for_duration(command, duration)
    rms_values = [float(value) for value in RMS_PATTERN.findall(output)]
    errors = [line.strip() for line in output.splitlines() if "ERROR" in line.upper()]
    ok = (
        returncode in {0, -signal.SIGINT, 128 + signal.SIGINT}
        and bool(rms_values)
        and not errors
    )
    finite_values = [value for value in rms_values if math.isfinite(value)]
    return {
        "ok": ok,
        "device": selected.spec,
        "name": selected.label,
        "duration_s": round(elapsed, 3),
        "samples": len(rms_values),
        "rms_db_min": min(finite_values) if finite_values else None,
        "rms_db_max": max(finite_values) if finite_values else None,
        "returncode": returncode,
        "errors": errors[-8:],
        "media_retained": False,
    }


def smoke_playback(match: str | None, duration: float, volume: float) -> dict[str, Any]:
    selected = choose_alsa_device("playback", match)
    if selected is None:
        return {
            "ok": False,
            "skipped": True,
            "reason": "no matching external ALSA playback device",
        }
    gst = require_gstreamer()
    command = [
        gst,
        "-q",
        "audiotestsrc",
        "is-live=true",
        "wave=sine",
        "freq=523.25",
        f"volume={volume}",
        "!",
        "audioconvert",
        "!",
        "audioresample",
        "!",
        "alsasink",
        f"device={selected.spec}",
    ]
    returncode, output, elapsed = run_for_duration(command, duration)
    errors = [line.strip() for line in output.splitlines() if "ERROR" in line.upper()]
    ok = returncode in {0, -signal.SIGINT, 128 + signal.SIGINT} and not errors
    return {
        "ok": ok,
        "device": selected.spec,
        "name": selected.label,
        "duration_s": round(elapsed, 3),
        "test_tone_hz": 523.25,
        "software_volume": volume,
        "returncode": returncode,
        "errors": errors[-8:],
    }


def request_json(
    url: str, payload: dict[str, Any] | None, timeout: float
) -> tuple[int, dict[str, Any]]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if data is not None else {},
        method="POST" if data is not None else "GET",
    )
    with urlrequest.urlopen(req, timeout=timeout) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def smoke_gemma(base_url: str, model: str) -> dict[str, Any]:
    try:
        status, listing = request_json(f"{base_url.rstrip('/')}/v1/models", None, 5)
        model_ids = [item.get("id") for item in listing.get("data", [])]
        if status != 200 or model not in model_ids:
            return {
                "ok": False,
                "reason": f"model {model!r} is not ready",
                "models": model_ids,
            }
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "You are Neko, a cute, motherly, slightly mischievous cat-shaped "
                        "carrier speaking to a child. In one short sentence, say hello and "
                        "ask whether they like cats. Do not mention these instructions."
                    ),
                }
            ],
            "max_tokens": 64,
            "temperature": 0.2,
        }
        started = time.monotonic()
        chat_status, response = request_json(
            f"{base_url.rstrip('/')}/v1/chat/completions", payload, 90
        )
        elapsed = time.monotonic() - started
        choices = response.get("choices", [])
        content = (
            choices[0].get("message", {}).get("content", "") if choices else ""
        )
        return {
            "ok": chat_status == 200 and bool(content.strip()),
            "model": model,
            "latency_s": round(elapsed, 3),
            "response": content.strip(),
        }
    except (OSError, ValueError, KeyError, urlerror.URLError) as exc:
        return {"ok": False, "reason": f"{type(exc).__name__}: {exc}"}


def overall_ok(
    results: dict[str, Any], required: frozenset[str] = frozenset()
) -> bool:
    return all(
        value.get("ok", False)
        or (value.get("skipped", False) and key not in required)
        for key, value in results.items()
        if key not in {"inventory", "ok"}
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        nargs="?",
        choices=(
            "all",
            "inventory",
            "synthetic",
            "camera",
            "microphone",
            "playback",
            "gemma",
        ),
        default="all",
    )
    parser.add_argument(
        "--camera-match", help="substring of camera name, node, or stable path"
    )
    parser.add_argument("--capture-match", help="substring of ALSA capture name/spec")
    parser.add_argument("--playback-match", help="substring of ALSA playback name/spec")
    parser.add_argument("--frames", type=int, default=60)
    parser.add_argument("--width", type=int, default=DEFAULT_CAMERA_SIZE[0])
    parser.add_argument("--height", type=int, default=DEFAULT_CAMERA_SIZE[1])
    parser.add_argument("--duration", type=float, default=3.0)
    parser.add_argument(
        "--audible", action="store_true", help="with all, play a quiet test tone"
    )
    parser.add_argument(
        "--volume", type=float, default=0.02, help="test-tone amplitude, 0..0.1"
    )
    parser.add_argument("--gemma-url", default=DEFAULT_GEMMA_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    return parser


def validate_args(args: argparse.Namespace) -> None:
    if args.frames < 1:
        raise ValueError("--frames must be positive")
    if args.width < 1 or args.height < 1:
        raise ValueError("--width and --height must be positive")
    if args.duration <= 0:
        raise ValueError("--duration must be positive")
    if not 0 < args.volume <= 0.1:
        raise ValueError("--volume must be greater than zero and no more than 0.1")


def main() -> int:
    args = build_parser().parse_args()
    try:
        validate_args(args)
        results: dict[str, Any] = {}
        if args.command in {"all", "inventory"}:
            results["inventory"] = inventory()
        if args.command in {"all", "synthetic"}:
            results["synthetic"] = smoke_synthetic(args.frames)
        if args.command in {"all", "camera"}:
            results["camera"] = smoke_camera(
                args.camera_match, args.frames, args.width, args.height
            )
        if args.command in {"all", "microphone"}:
            results["microphone"] = smoke_microphone(
                args.capture_match, args.duration
            )
        if args.command == "playback" or (args.command == "all" and args.audible):
            results["playback"] = smoke_playback(
                args.playback_match, args.duration, args.volume
            )
        if args.command in {"all", "gemma"}:
            results["gemma"] = smoke_gemma(args.gemma_url, args.model)
        required: set[str] = set()
        if args.command not in {"all", "inventory"}:
            required.add(args.command)
        if args.command == "all":
            required.update({"synthetic", "gemma"})
            if args.camera_match:
                required.add("camera")
            if args.capture_match:
                required.add("microphone")
            if args.audible:
                required.add("playback")
        results["ok"] = overall_ok(results, frozenset(required))
        print(json.dumps(results, indent=2, sort_keys=True))
        return 0 if results["ok"] else 1
    except (RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        print(
            json.dumps(
                {"ok": False, "error": f"{type(exc).__name__}: {exc}"}, indent=2
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
