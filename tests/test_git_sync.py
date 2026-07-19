from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest

from neko.repository_lock import repository_write_lock
from scripts.neko_git_sync import sync_repository


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["/usr/bin/git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )
    return completed.stdout.strip()


class GitSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.remote = self.root / "remote.git"
        subprocess.run(
            ["/usr/bin/git", "init", "--bare", "--initial-branch=main", str(self.remote)],
            check=True,
            capture_output=True,
        )
        self.local = self.root / "local"
        subprocess.run(
            ["/usr/bin/git", "clone", str(self.remote), str(self.local)],
            check=True,
            capture_output=True,
        )
        git(self.local, "config", "user.name", "Neko Test")
        git(self.local, "config", "user.email", "neko@example.invalid")
        (self.local / "README.md").write_text("start\n", encoding="utf-8")
        git(self.local, "add", "README.md")
        git(self.local, "commit", "-m", "Initial")
        git(self.local, "push", "origin", "main")
        self.initial = git(self.local, "rev-parse", "HEAD")
        self.state = self.root / "state" / "last-remote"
        self.state.parent.mkdir()
        self.state.write_text(self.initial + "\n", encoding="utf-8")
        self.lock = self.root / "state" / "lock"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_local_changes_are_committed_and_pushed_to_main(self) -> None:
        (self.local / "story.md").write_text("A local story.\n", encoding="utf-8")
        restarts: list[bool] = []
        result = sync_repository(
            self.local,
            self.state,
            restart=lambda: restarts.append(True),
            lock_path=self.lock,
        )
        self.assertTrue(result.local_commit_created)
        self.assertFalse(result.remote_changed)
        self.assertEqual(restarts, [])
        self.assertEqual(
            git(self.local, "rev-parse", "HEAD"),
            git(self.local, "rev-parse", "origin/main"),
        )
        self.assertEqual(git(self.local, "status", "--porcelain"), "")

    def test_remote_change_is_pulled_and_restarts_assistant(self) -> None:
        other = self.root / "other"
        subprocess.run(
            ["/usr/bin/git", "clone", str(self.remote), str(other)],
            check=True,
            capture_output=True,
        )
        git(other, "config", "user.name", "Remote Test")
        git(other, "config", "user.email", "remote@example.invalid")
        (other / "remote.md").write_text("remote change\n", encoding="utf-8")
        git(other, "add", "remote.md")
        git(other, "commit", "-m", "Remote change")
        git(other, "push", "origin", "main")

        restarts: list[bool] = []
        result = sync_repository(
            self.local,
            self.state,
            restart=lambda: restarts.append(True),
            lock_path=self.lock,
        )
        self.assertTrue(result.remote_changed)
        self.assertTrue(result.assistant_restarted)
        self.assertEqual(restarts, [True])
        self.assertEqual((self.local / "remote.md").read_text(), "remote change\n")

    def test_secret_like_file_fails_closed(self) -> None:
        (self.local / "private-token.txt").write_text("SECRET=value\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "secret-like"):
            sync_repository(self.local, self.state, lock_path=self.lock)

    def test_busy_writer_skips_cycle_without_touching_git(self) -> None:
        (self.local / "story.md").write_text("still writing\n", encoding="utf-8")
        with repository_write_lock(path=self.lock):
            result = sync_repository(self.local, self.state, lock_path=self.lock)
        self.assertEqual(result.status, "busy")
        self.assertEqual(git(self.local, "status", "--porcelain"), "?? story.md")


if __name__ == "__main__":
    unittest.main()
