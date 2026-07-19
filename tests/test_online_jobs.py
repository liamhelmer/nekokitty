from __future__ import annotations

from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock

from neko.online_jobs import (
    CodexOnlineJobRunner,
    ConnectivityMonitor,
    OnlineCommand,
    parse_online_command,
)


class OnlineCommandTests(unittest.TestCase):
    def test_search_phrases_extract_the_subject(self) -> None:
        self.assertEqual(
            parse_online_command("please search the web for why cats chirp"),
            OnlineCommand("web_search", "why cats chirp"),
        )
        self.assertEqual(
            parse_online_command("web search moon jellyfish"),
            OnlineCommand("web_search", "moon jellyfish"),
        )

    def test_compose_variants_extract_the_story_request(self) -> None:
        for phrase in (
            "compose story about a disco lynx",
            "compose a story about a disco lynx",
            "compose a new story about a disco lynx",
        ):
            with self.subTest(phrase=phrase):
                self.assertEqual(
                    parse_online_command(phrase),
                    OnlineCommand("compose_story", "a disco lynx"),
                )

    def test_local_story_request_is_not_an_online_command(self) -> None:
        self.assertIsNone(parse_online_command("tell me another cat story"))


class ConnectivityMonitorTests(unittest.TestCase):
    def test_each_probe_changes_mode_immediately_without_grace(self) -> None:
        answers = iter((True, False, True))
        changes: list[bool] = []
        monitor = ConnectivityMonitor(
            interval_s=120,
            check=lambda: next(answers),
            on_change=changes.append,
        )
        self.assertTrue(monitor.probe_once())
        self.assertFalse(monitor.probe_once())
        self.assertTrue(monitor.probe_once())
        self.assertEqual(changes, [True, False, True])

    def test_unchanged_probe_does_not_duplicate_transition_event(self) -> None:
        changes: list[bool] = []
        monitor = ConnectivityMonitor(check=lambda: True, on_change=changes.append)
        monitor.probe_once()
        monitor.probe_once()
        self.assertEqual(changes, [True])


class CodexCommandTests(unittest.TestCase):
    def make_runner(self, directory: str) -> CodexOnlineJobRunner:
        return CodexOnlineJobRunner(
            lambda _result: None,
            codex_path=Path("/opt/codex"),
            repo_root=Path(directory),
            job_root=Path(directory) / "jobs",
        )

    def test_web_search_uses_luna_low_plan_read_only_and_search(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runner = self.make_runner(directory)
            argv, prompt = runner._command_line(
                OnlineCommand("web_search", "cat whiskers"),
                Path(directory) / "answer.txt",
            )
        self.assertIn("gpt-5.6-luna", argv)
        self.assertIn('model_reasoning_effort="low"', argv)
        self.assertIn("read-only", argv)
        self.assertIn("--search", argv)
        self.assertIn("Operate in Plan mode", prompt)
        self.assertEqual(argv[-1], "-")
        self.assertNotIn("cat whiskers", " ".join(argv))
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", argv)

    def test_story_uses_terra_low_yolo_with_tightly_scoped_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runner = self.make_runner(directory)
            argv, prompt = runner._command_line(
                OnlineCommand("compose_story", "a dancing kitten"),
                Path(directory) / "answer.txt",
            )
        self.assertIn("gpt-5.6-terra", argv)
        self.assertIn('model_reasoning_effort="low"', argv)
        self.assertIn("--dangerously-bypass-approvals-and-sandbox", argv)
        self.assertIn("content/stories/originals", prompt)
        self.assertIn("paragraph at or below 350 characters", prompt)
        self.assertIn("500 to 650 words", prompt)
        self.assertEqual(argv[-1], "-")
        self.assertNotIn("a dancing kitten", " ".join(argv))

    def test_runner_rejects_a_second_concurrent_job(self) -> None:
        release = threading.Event()
        runner = CodexOnlineJobRunner(lambda _result: None)
        with mock.patch.object(runner, "_run", side_effect=lambda _command: release.wait(1)):
            self.assertTrue(runner.start(OnlineCommand("web_search", "cats")))
            self.assertFalse(runner.start(OnlineCommand("web_search", "dogs")))
            release.set()


if __name__ == "__main__":
    unittest.main()
