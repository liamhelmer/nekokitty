from __future__ import annotations

import json
import subprocess
import unittest

from neko.local_commands import (
    HealthReport,
    ServiceCheck,
    ServiceProblem,
    check_services,
    parse_local_command,
    primary_ip_address,
    request_reboot,
    speakable_ip_address,
)


def completed(command: list[str], returncode: int = 0, stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(command, returncode, stdout, "")


class LocalCommandParsingTests(unittest.TestCase):
    def test_exact_local_phrases_are_recognized(self) -> None:
        expected = {
            "Tell me your IP address": "ip_address",
            "what's your IP address?": "ip_address",
            "Neko, full reboot": "reboot",
            "Are you online?": "online",
            "Are you healthy?": "health",
        }
        for phrase, kind in expected.items():
            with self.subTest(phrase=phrase):
                command = parse_local_command(phrase)
                self.assertIsNotNone(command)
                assert command is not None
                self.assertEqual(command.kind, kind)

    def test_similar_general_questions_do_not_trigger_maintenance(self) -> None:
        for phrase in (
            "tell me about IP addresses",
            "are cats healthy",
            "reboot the story",
            "I wonder whether you're online today",
        ):
            with self.subTest(phrase=phrase):
                self.assertIsNone(parse_local_command(phrase))


class LocalCommandOperationTests(unittest.TestCase):
    def test_primary_ip_uses_preferred_route_source(self) -> None:
        def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            return completed(command, stdout=json.dumps([{"prefsrc": "192.168.4.21"}]))

        self.assertEqual(primary_ip_address(fake_run), "192.168.4.21")
        self.assertEqual(
            speakable_ip_address("192.168.4.21"),
            "one nine two dot one six eight dot four dot two one",
        )

    def test_reboot_uses_only_noninteractive_exact_systemctl_command(self) -> None:
        seen: list[list[str]] = []

        def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            seen.append(command)
            return completed(command)

        self.assertTrue(request_reboot(fake_run))
        self.assertEqual(
            seen,
            [["/usr/bin/sudo", "-n", "/usr/bin/systemctl", "reboot"]],
        )

    def test_health_checks_active_state_and_recent_error_priority(self) -> None:
        services = (
            ServiceCheck("good.service", "good"),
            ServiceCheck("error.service", "erroring", user_unit=True),
            ServiceCheck("down.service", "down"),
        )

        def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            if "journalctl" in command[0]:
                unit = command[command.index("--unit") + 1]
                output = "recent error\n" if unit == "error.service" else ""
                return completed(command, stdout=output)
            unit = command[-1]
            state = "inactive" if unit == "down.service" else "active"
            return completed(command, stdout=f"ActiveState={state}\nSubState=running\nResult=success\n")

        report = check_services(services, run=fake_run)
        self.assertFalse(report.healthy)
        self.assertEqual(
            [(problem.unit, problem.issue) for problem in report.problems],
            [("error.service", "recent_errors"), ("down.service", "inactive")],
        )
        self.assertIn("recent errors", report.spoken_text())
        self.assertIn("is down", report.spoken_text())

    def test_healthy_reply_is_owner_specified_text(self) -> None:
        self.assertEqual(
            HealthReport(()).spoken_text(),
            "I feel healthy, but you should check me for worms!",
        )

    def test_problem_details_never_include_journal_text(self) -> None:
        report = HealthReport((ServiceProblem("x.service", "voice", "recent_errors"),))
        self.assertEqual(
            report.spoken_text(),
            "I don't feel completely healthy: my voice has recent errors.",
        )


if __name__ == "__main__":
    unittest.main()
