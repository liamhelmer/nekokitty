"""Deterministic local maintenance commands for Neko's voice transport."""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import json
import subprocess
from typing import Callable, Literal, Sequence

from .behavior import normalize_phrase


LocalCommandKind = Literal["ip_address", "reboot", "online", "health"]


@dataclass(frozen=True, slots=True)
class LocalCommand:
    kind: LocalCommandKind


@dataclass(frozen=True, slots=True)
class ServiceCheck:
    unit: str
    label: str
    user_unit: bool = False


@dataclass(frozen=True, slots=True)
class ServiceProblem:
    unit: str
    label: str
    issue: Literal["inactive", "failed", "recent_errors", "check_failed"]


@dataclass(frozen=True, slots=True)
class HealthReport:
    problems: tuple[ServiceProblem, ...]

    @property
    def healthy(self) -> bool:
        return not self.problems

    def spoken_text(self) -> str:
        if self.healthy:
            return "I feel healthy, but you should check me for worms!"
        details: list[str] = []
        for problem in self.problems:
            if problem.issue == "inactive":
                details.append(f"my {problem.label} is down")
            elif problem.issue == "failed":
                details.append(f"my {problem.label} has failed")
            elif problem.issue == "recent_errors":
                details.append(f"my {problem.label} has recent errors")
            else:
                details.append(f"I couldn't check my {problem.label}")
        if len(details) == 1:
            summary = details[0]
        else:
            summary = ", ".join(details[:-1]) + f", and {details[-1]}"
        return f"I don't feel completely healthy: {summary}."


ESSENTIAL_SERVICES: tuple[ServiceCheck, ...] = (
    ServiceCheck("docker.service", "model container runtime"),
    ServiceCheck("neko-llm.service", "local language service"),
    ServiceCheck("neko-tts-fast.service", "fast voice service"),
    ServiceCheck("neko-tts.service", "Kiki voice service"),
    ServiceCheck("neko-what-if-refresh.timer", "schedule refresh timer"),
    ServiceCheck("pipewire.service", "audio service", user_unit=True),
    ServiceCheck(
        "neko-bluetooth-reconnect.service",
        "Bluetooth speaker service",
        user_unit=True,
    ),
    ServiceCheck("neko-audio-policy.service", "audio routing service", user_unit=True),
    ServiceCheck("neko-voice-assistant.service", "voice assistant", user_unit=True),
    ServiceCheck("neko-git-sync.timer", "Git sync timer", user_unit=True),
)


_PHRASES: dict[str, LocalCommandKind] = {
    "tell me your ip address": "ip_address",
    "what is your ip address": "ip_address",
    "what s your ip address": "ip_address",
    "full reboot": "reboot",
    "do a full reboot": "reboot",
    "reboot the jetson": "reboot",
    "are you online": "online",
    "are you healthy": "health",
    "health check": "health",
}


def parse_local_command(text: str) -> LocalCommand | None:
    """Recognize only exact, bounded local command phrases."""

    normalized = normalize_phrase(text)
    for name in ("neko neko", "nekko nekko", "neko", "nekko"):
        if normalized.startswith(f"{name} "):
            normalized = normalized[len(name) :].strip()
            break
    kind = _PHRASES.get(normalized)
    return LocalCommand(kind) if kind is not None else None


def primary_ip_address(
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> str | None:
    """Return the preferred non-loopback source address for the default route."""

    try:
        completed = run(
            ["/usr/sbin/ip", "-j", "route", "get", "8.8.8.8"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        if completed.returncode != 0:
            return None
        routes = json.loads(completed.stdout)
        candidate = routes[0].get("prefsrc") if routes else None
        address = ipaddress.ip_address(candidate) if candidate else None
        if address is not None and not address.is_loopback:
            return str(address)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError, ValueError, TypeError):
        return None
    return None


def speakable_ip_address(address: str) -> str:
    """Spell an address so TTS reads digits and separators unambiguously."""

    parsed = ipaddress.ip_address(address)
    if parsed.version != 4:
        return str(parsed).replace(":", " colon ")
    digits = {
        "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
        "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine",
    }
    return " dot ".join(" ".join(digits[digit] for digit in octet) for octet in address.split("."))


def _systemctl_command(service: ServiceCheck) -> list[str]:
    command = ["/usr/bin/systemctl"]
    if service.user_unit:
        command.append("--user")
    command.extend([
        "show", "--property=ActiveState", "--property=SubState",
        "--property=Result", "--property=ActiveEnterTimestamp", service.unit,
    ])
    return command


def _journal_command(service: ServiceCheck, since: str | None) -> list[str]:
    command = ["/usr/bin/journalctl"]
    if service.user_unit:
        command.append("--user")
    command.extend(["--quiet", "--no-pager", "--boot"])
    if since is not None:
        command.extend(["--since", since])
    command.extend(["--priority", "0..3", "--unit", service.unit, "--lines", "1"])
    return command


def check_services(
    services: Sequence[ServiceCheck] = ESSENTIAL_SERVICES,
    *,
    since: str | None = None,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> HealthReport:
    """Check essential state and errors from each unit's current active run."""

    problems: list[ServiceProblem] = []
    for service in services:
        try:
            state = run(
                _systemctl_command(service),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            problems.append(ServiceProblem(service.unit, service.label, "check_failed"))
            continue
        values = dict(
            line.split("=", 1) for line in state.stdout.splitlines() if "=" in line
        )
        active = values.get("ActiveState") == "active"
        failed = values.get("ActiveState") == "failed" or values.get("Result") not in {
            None, "", "success",
        }
        if state.returncode != 0:
            problems.append(ServiceProblem(service.unit, service.label, "check_failed"))
            continue
        if failed:
            problems.append(ServiceProblem(service.unit, service.label, "failed"))
            continue
        if not active:
            problems.append(ServiceProblem(service.unit, service.label, "inactive"))
            continue
        try:
            active_since = values.get("ActiveEnterTimestamp")
            journal_since = since or (
                active_since if active_since and active_since != "n/a" else None
            )
            journal = run(
                _journal_command(service, journal_since),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=4,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            problems.append(ServiceProblem(service.unit, service.label, "check_failed"))
            continue
        if journal.returncode != 0:
            problems.append(ServiceProblem(service.unit, service.label, "check_failed"))
        elif journal.stdout.strip():
            problems.append(ServiceProblem(service.unit, service.label, "recent_errors"))
    return HealthReport(tuple(problems))


def request_reboot(
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> bool:
    """Request a real host reboot through the owner's existing noninteractive sudo."""

    try:
        completed = run(
            ["/usr/bin/sudo", "-n", "/usr/bin/systemctl", "reboot"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0
