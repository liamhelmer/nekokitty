#!/usr/bin/env python3
"""Commit local Neko changes, synchronize main, and reload on remote change."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Callable, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neko.repository_lock import LOCK_PATH, repository_write_lock  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = Path("/home/neko/.local/state/neko/git-sync-last-remote")
SENSITIVE_BASENAME_RE = re.compile(
    r"(?:^|[._-])(?:secret|token|credential|password|private[-_]?recording)(?:[._-]|$)",
    re.IGNORECASE,
)
SENSITIVE_SUFFIXES = {".key", ".pem", ".p12", ".pfx"}


@dataclass(frozen=True, slots=True)
class SyncResult:
    status: str
    local_commit_created: bool = False
    remote_changed: bool = False
    assistant_restarted: bool = False
    head: str | None = None


def run_git(
    repo: Path,
    args: Sequence[str],
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/usr/bin/git", *args],
        cwd=repo,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=120,
        check=check,
    )


def git_output(repo: Path, *args: str) -> str:
    return run_git(repo, args).stdout.strip()


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(text, encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def staged_paths(repo: Path) -> tuple[str, ...]:
    output = run_git(repo, ["diff", "--cached", "--name-only", "-z"]).stdout
    return tuple(item for item in output.split("\0") if item)


def reject_sensitive_paths(paths: Sequence[str]) -> None:
    rejected = []
    for value in paths:
        name = Path(value).name
        if name == ".env" or Path(name).suffix.casefold() in SENSITIVE_SUFFIXES:
            rejected.append(value)
        elif SENSITIVE_BASENAME_RE.search(name):
            rejected.append(value)
    if rejected:
        raise RuntimeError(f"refusing to publish secret-like paths: {rejected}")


def repository_is_busy(repo: Path) -> bool:
    git_dir = Path(git_output(repo, "rev-parse", "--absolute-git-dir"))
    return any(
        (git_dir / marker).exists()
        for marker in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply")
    )


def default_restart() -> None:
    subprocess.run(
        ["/usr/bin/systemctl", "--user", "daemon-reload"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=True,
    )
    subprocess.run(
        ["/usr/bin/systemctl", "--user", "restart", "neko-voice-assistant.service"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=True,
    )


def sync_repository(
    repo: Path,
    state_path: Path,
    *,
    restart: Callable[[], None] = default_restart,
    lock_path: Path = LOCK_PATH,
) -> SyncResult:
    repo = repo.resolve()
    if not (repo / ".git").exists():
        raise RuntimeError(f"not a Git worktree: {repo}")
    with repository_write_lock(blocking=False, path=lock_path) as lock:
        if lock is None:
            return SyncResult("busy")
        branch = git_output(repo, "branch", "--show-current")
        if branch != "main":
            raise RuntimeError(f"automatic sync requires main, found {branch or 'detached HEAD'}")
        if repository_is_busy(repo):
            raise RuntimeError("repository has an in-progress Git operation")

        run_git(repo, ["add", "-A"])
        paths = staged_paths(repo)
        reject_sensitive_paths(paths)
        local_commit_created = bool(paths)
        if local_commit_created:
            timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
            run_git(repo, ["commit", "-m", f"Automated Neko sync {timestamp}"])

        previous_remote = state_path.read_text(encoding="utf-8").strip() if state_path.is_file() else ""
        run_git(repo, ["fetch", "--prune", "origin", "main"])
        fetched_remote = git_output(repo, "rev-parse", "origin/main")
        remote_changed = bool(previous_remote and previous_remote != fetched_remote)
        head = git_output(repo, "rev-parse", "HEAD")

        if head != fetched_remote:
            remote_is_ancestor = run_git(
                repo,
                ["merge-base", "--is-ancestor", "origin/main", "HEAD"],
                check=False,
            ).returncode == 0
            head_is_ancestor = run_git(
                repo,
                ["merge-base", "--is-ancestor", "HEAD", "origin/main"],
                check=False,
            ).returncode == 0
            if head_is_ancestor:
                run_git(repo, ["merge", "--ff-only", "origin/main"])
            elif not remote_is_ancestor:
                rebased = run_git(repo, ["rebase", "origin/main"], check=False)
                if rebased.returncode != 0:
                    run_git(repo, ["rebase", "--abort"], check=False)
                    raise RuntimeError("automatic rebase conflicted; local commit was preserved")

        head = git_output(repo, "rev-parse", "HEAD")
        run_git(repo, ["push", "origin", "HEAD:main"])
        atomic_write(state_path, head + "\n")
        restarted = False
        if remote_changed:
            restart()
            restarted = True
        return SyncResult(
            "synchronized",
            local_commit_created,
            remote_changed,
            restarted,
            head,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    parser.add_argument("--state-path", type=Path, default=STATE_PATH)
    parser.add_argument("--lock-path", type=Path, default=LOCK_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = sync_repository(
            args.repo,
            args.state_path,
            lock_path=args.lock_path,
        )
    except Exception as error:
        print(
            json.dumps(
                {"event": "git_sync_failed", "error_type": type(error).__name__, "message": str(error)},
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps({"event": "git_sync", **asdict(result)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
