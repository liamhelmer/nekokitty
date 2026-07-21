"""Dynamic ReSpeaker-first PipeWire routing with Bluetooth mirroring/fallback."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import signal
import socket
import subprocess
import threading
import time
from typing import Callable, Literal, Sequence


MIRROR_SINK = "neko_mirror"
PROCESSED_SOURCE = "neko_respeaker_processed"


@dataclass(frozen=True, slots=True)
class AudioNode:
    name: str
    description: str
    properties: dict[str, str]


@dataclass(frozen=True, slots=True)
class RouteChoice:
    output_mode: Literal["mirror", "respeaker", "bluetooth", "unmanaged"]
    output_names: tuple[str, ...]
    source_name: str | None
    source_kind: Literal["respeaker", "bluetooth", "webcam", "unmanaged"]


def _haystack(node: AudioNode) -> str:
    fields = [node.name, node.description]
    fields.extend(
        node.properties.get(key, "")
        for key in (
            "alsa.card_name",
            "alsa.long_card_name",
            "device.description",
            "device.name",
            "device.nick",
            "device.product.name",
            "device.serial",
        )
    )
    return " ".join(fields).casefold()


def is_respeaker(node: AudioNode) -> bool:
    """Match Seeed's board by USB IDs or stable product/card text."""

    vendor = node.properties.get("device.vendor.id", "").casefold()
    product = node.properties.get("device.product.id", "").casefold()
    return (
        (vendor in {"0x2886", "2886"} and product in {"0x0018", "0018"})
        or "respeaker" in _haystack(node)
        or "re speaker" in _haystack(node)
    )


def is_bluetooth(node: AudioNode) -> bool:
    return (
        node.name.startswith(("bluez_output.", "bluez_input."))
        or node.properties.get("device.api") == "bluez5"
        or node.properties.get("device.bus") == "bluetooth"
    )


def is_webcam(node: AudioNode) -> bool:
    return (
        node.properties.get("device.form_factor") == "webcam"
        or "c922" in _haystack(node)
        or "webcam" in _haystack(node)
    )


def choose_routes(sinks: Sequence[AudioNode], sources: Sequence[AudioNode]) -> RouteChoice:
    """Apply ReSpeaker > Bluetooth > C922 input and mirror-capable output policy."""

    real_sources = [
        node
        for node in sources
        if not node.name.endswith(".monitor") and not node.name.startswith("neko_")
    ]
    respeaker_sink = next((node for node in sinks if is_respeaker(node)), None)
    bluetooth_sink = next((node for node in sinks if is_bluetooth(node)), None)
    respeaker_source = next((node for node in real_sources if is_respeaker(node)), None)
    bluetooth_source = next((node for node in real_sources if is_bluetooth(node)), None)
    webcam_source = next((node for node in real_sources if is_webcam(node)), None)

    if respeaker_sink is not None and bluetooth_sink is not None:
        output_mode = "mirror"
        output_names = (respeaker_sink.name, bluetooth_sink.name)
    elif respeaker_sink is not None:
        output_mode = "respeaker"
        output_names = (respeaker_sink.name,)
    elif bluetooth_sink is not None:
        output_mode = "bluetooth"
        output_names = (bluetooth_sink.name,)
    else:
        output_mode = "unmanaged"
        output_names = ()

    if respeaker_source is not None:
        source = respeaker_source
        source_kind = "respeaker"
    elif bluetooth_source is not None:
        source = bluetooth_source
        source_kind = "bluetooth"
    elif webcam_source is not None:
        source = webcam_source
        source_kind = "webcam"
    else:
        source = None
        source_kind = "unmanaged"
    return RouteChoice(output_mode, output_names, source.name if source else None, source_kind)


class PactlBackend:
    def __init__(
        self,
        run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self.run = run

    def _run(self, args: list[str], *, timeout: float = 5.0) -> subprocess.CompletedProcess[str]:
        result = self.run(
            ["/usr/bin/pactl", *args],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError("pactl command failed")
        return result

    def nodes(self, kind: Literal["sinks", "sources"]) -> tuple[AudioNode, ...]:
        payload = json.loads(self._run(["--format=json", "list", kind]).stdout)
        return tuple(
            AudioNode(
                str(item.get("name", "")),
                str(item.get("description", "")),
                {str(key): str(value) for key, value in item.get("properties", {}).items()},
            )
            for item in payload
            if item.get("name")
        )

    def default(self, kind: Literal["sink", "source"]) -> str:
        return self._run([f"get-default-{kind}"]).stdout.strip()

    def set_default(self, kind: Literal["sink", "source"], name: str) -> None:
        if self.default(kind) != name:
            self._run([f"set-default-{kind}", name])

    def load_mirror(self, sink_names: tuple[str, str]) -> int:
        result = self._run([
            "load-module",
            "module-combine-sink",
            f"sink_name={MIRROR_SINK}",
            "sink_properties=device.description=Neko_Mirrored_Output",
            f"slaves={','.join(sink_names)}",
            "adjust_time=1",
        ])
        return int(result.stdout.strip())

    def load_processed_source(self, master: str) -> int:
        result = self._run([
            "load-module",
            "module-remap-source",
            f"source_name={PROCESSED_SOURCE}",
            f"master={master}",
            "channels=1",
            "master_channel_map=front-left",
            "channel_map=mono",
            "remix=no",
            "source_properties=device.description=Neko_ReSpeaker_Processed_Mic",
        ])
        return int(result.stdout.strip())

    def unload_module(self, module_id: int) -> None:
        self._run(["unload-module", str(module_id)])

    def stale_owned_modules(self) -> tuple[int, ...]:
        payload = json.loads(self._run(["--format=json", "list", "modules"]).stdout)
        return tuple(
            int(item["index"])
            for item in payload
            if (
                item.get("name") == "module-combine-sink"
                and f"sink_name={MIRROR_SINK}" in str(item.get("argument", "")).split()
            )
            or (
                item.get("name") == "module-remap-source"
                and f"source_name={PROCESSED_SOURCE}"
                in str(item.get("argument", "")).split()
            )
        )


class AudioPolicy:
    def __init__(
        self,
        backend: PactlBackend,
        *,
        restart_voice: Callable[[], None] | None = None,
    ) -> None:
        self.backend = backend
        self.restart_voice = restart_voice
        self.mirror_module: int | None = None
        self.mirror_members: tuple[str, str] | None = None
        self.source_module: int | None = None
        self.source_master: str | None = None
        self.last_choice: RouteChoice | None = None
        self.initialized = False

    def _remove_mirror(self) -> None:
        if self.mirror_module is not None:
            try:
                self.backend.unload_module(self.mirror_module)
            finally:
                self.mirror_module = None
                self.mirror_members = None

    def _remove_processed_source(self) -> None:
        if self.source_module is not None:
            try:
                self.backend.unload_module(self.source_module)
            finally:
                self.source_module = None
                self.source_master = None

    def reconcile(self) -> RouteChoice:
        if not self.initialized:
            for module_id in self.backend.stale_owned_modules():
                self.backend.unload_module(module_id)
            self.initialized = True
        choice = choose_routes(self.backend.nodes("sinks"), self.backend.nodes("sources"))
        if choice.output_mode == "mirror":
            members = (choice.output_names[0], choice.output_names[1])
            if self.mirror_module is None or self.mirror_members != members:
                self._remove_mirror()
                self.mirror_module = self.backend.load_mirror(members)
                self.mirror_members = members
            self.backend.set_default("sink", MIRROR_SINK)
        else:
            self._remove_mirror()
            if choice.output_names:
                self.backend.set_default("sink", choice.output_names[0])
        if choice.source_kind == "respeaker" and choice.source_name is not None:
            if self.source_module is None or self.source_master != choice.source_name:
                self._remove_processed_source()
                self.source_module = self.backend.load_processed_source(choice.source_name)
                self.source_master = choice.source_name
            self.backend.set_default("source", PROCESSED_SOURCE)
        else:
            self._remove_processed_source()
            if choice.source_name is not None:
                self.backend.set_default("source", choice.source_name)

        previous = self.last_choice
        self.last_choice = choice
        if (
            previous is not None
            and previous.source_name != choice.source_name
            and self.restart_voice is not None
        ):
            self.restart_voice()
        return choice

    def close(self) -> None:
        self._remove_processed_source()
        self._remove_mirror()


def notify_ready() -> None:
    address = os.environ.get("NOTIFY_SOCKET")
    if not address:
        return
    if address.startswith("@"):
        address = "\0" + address[1:]
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
        sock.connect(address)
        sock.sendall(b"READY=1\nSTATUS=Audio routing policy active")


def restart_voice_assistant() -> None:
    subprocess.run(
        [
            "/usr/bin/systemctl", "--user", "try-restart",
            "--no-block", "neko-voice-assistant.service",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=5,
        check=False,
    )


def emit(choice: RouteChoice) -> None:
    print(json.dumps({
        "event": "audio_route",
        "output_mode": choice.output_mode,
        "source_kind": choice.source_kind,
        "respeaker_present": choice.output_mode in {"respeaker", "mirror"}
        or choice.source_kind == "respeaker",
        "bluetooth_output_present": choice.output_mode in {"bluetooth", "mirror"},
    }), flush=True)


def run_daemon(*, interval_s: float = 2.0) -> int:
    stop = threading.Event()
    signal.signal(signal.SIGINT, lambda *_args: stop.set())
    signal.signal(signal.SIGTERM, lambda *_args: stop.set())
    policy = AudioPolicy(PactlBackend(), restart_voice=restart_voice_assistant)
    initialized = False
    last_emitted: RouteChoice | None = None
    last_error: str | None = None
    try:
        while not stop.is_set():
            try:
                choice = policy.reconcile()
                if choice != last_emitted:
                    emit(choice)
                    last_emitted = choice
                last_error = None
                if not initialized:
                    notify_ready()
                    initialized = True
            except Exception as error:
                error_type = type(error).__name__
                if error_type != last_error:
                    print(json.dumps({"event": "audio_policy_error", "error_type": error_type}), flush=True)
                    last_error = error_type
            stop.wait(interval_s)
    finally:
        policy.close()
    return 0
