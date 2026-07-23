"""Deterministic reconnect policy for Neko's paired Bluetooth speakers."""

from __future__ import annotations

import json
import os
import re
import signal
import socket
import subprocess
import threading
from typing import Callable, Sequence


_ADDRESS = re.compile(r"^(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")


def configured_addresses(value: str) -> tuple[str, ...]:
    """Parse an ordered, comma-separated address list without logging it."""

    addresses = tuple(item.strip().upper() for item in value.split(",") if item.strip())
    if not addresses or any(not _ADDRESS.fullmatch(item) for item in addresses):
        raise ValueError("invalid Bluetooth speaker configuration")
    return addresses


def info_is_connected(output: str) -> bool:
    return any(line.strip() == "Connected: yes" for line in output.splitlines())


class BluetoothBackend:
    def __init__(
        self,
        run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self.run = run

    def _run(self, action: str, address: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.pop("NOTIFY_SOCKET", None)
        return self.run(
            ["/usr/bin/bluetoothctl", action, address],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            env=environment,
            timeout=12,
            check=False,
        )

    def connected(self, address: str) -> bool:
        result = self._run("info", address)
        return result.returncode == 0 and info_is_connected(result.stdout)

    def connect(self, address: str) -> bool:
        result = self._run("connect", address)
        return result.returncode == 0 and self.connected(address)


def ensure_speaker(
    addresses: Sequence[str],
    backend: BluetoothBackend,
) -> tuple[str, int | None]:
    """Keep an existing connection or connect the first available speaker."""

    for index, address in enumerate(addresses):
        if backend.connected(address):
            return "connected", index
    for index, address in enumerate(addresses):
        if backend.connect(address):
            return "reconnected", index
    return "unavailable", None


def notify_ready() -> None:
    address = os.environ.get("NOTIFY_SOCKET")
    if not address:
        return
    if address.startswith("@"):
        address = "\0" + address[1:]
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
        sock.connect(address)
        sock.sendall(b"READY=1\nSTATUS=Bluetooth speaker reconnect policy active")


def emit(state: str, slot: int | None) -> None:
    payload: dict[str, object] = {"event": "bluetooth_speaker", "state": state}
    if slot is not None:
        payload["slot"] = slot + 1
    print(json.dumps(payload), flush=True)


def run_daemon(*, interval_s: float = 10.0) -> int:
    addresses = configured_addresses(os.environ.get("NEKO_BLUETOOTH_SPEAKERS", ""))
    backend = BluetoothBackend()
    stop = threading.Event()
    signal.signal(signal.SIGINT, lambda *_args: stop.set())
    signal.signal(signal.SIGTERM, lambda *_args: stop.set())
    last_result: tuple[str, int | None] | None = None
    ready = False
    while not stop.is_set():
        try:
            result = ensure_speaker(addresses, backend)
            if result != last_result:
                emit(*result)
                last_result = result
            if not ready:
                notify_ready()
                ready = True
        except Exception as error:
            result = ("error", None)
            if result != last_result:
                print(json.dumps({
                    "event": "bluetooth_speaker_error",
                    "error_type": type(error).__name__,
                }), flush=True)
                last_result = result
            if not ready:
                notify_ready()
                ready = True
        stop.wait(interval_s)
    return 0
