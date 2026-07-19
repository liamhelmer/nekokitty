#!/usr/bin/env python3
"""Drain Neko's story rebuild queue; caller supplies nice/ionice inheritance."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neko.repository_lock import repository_write_lock  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILDER = REPO_ROOT / "scripts/build_story_recordings.py"
PYTHON = Path("/home/neko/.local/share/neko/venvs/kittentts/bin/python")
DEFAULT_QUEUE_ROOT = Path("/var/tmp/neko-story-recording-rebuild")


def log(queue_root: Path, value: dict[str, object]) -> None:
    value = {"timestamp": int(time.time()), **value}
    with (queue_root / "worker.log").open("a", encoding="utf-8") as target:
        target.write(json.dumps(value, sort_keys=True) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue-root", type=Path, default=DEFAULT_QUEUE_ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.queue_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock_path = args.queue_root / "worker.lock"
    with lock_path.open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        log(
            args.queue_root,
            {
                "event": "worker_started",
                "io_priority": subprocess.check_output(
                    ["/usr/bin/ionice", "-p", str(os.getpid())],
                    text=True,
                ).strip(),
                "nice": os.getpriority(os.PRIO_PROCESS, 0),
                "threads": 1,
            },
        )
        empty_passes = 0
        while empty_passes < 2:
            requests = sorted(args.queue_root.glob("request-*.json"))
            if not requests:
                empty_passes += 1
                time.sleep(1)
                continue
            empty_passes = 0
            request_path = requests[0]
            try:
                request = json.loads(request_path.read_text(encoding="utf-8"))
                if request.get("schema_version") != 1:
                    raise ValueError("unsupported rebuild request")
                story_id = request["story_id"]
                if not isinstance(story_id, str) or not story_id:
                    raise ValueError("invalid rebuild story ID")
                with repository_write_lock():
                    completed = subprocess.run(
                        [
                            str(PYTHON),
                            str(BUILDER),
                            "--story-id",
                            story_id,
                            "--incremental",
                            "--threads",
                            "1",
                        ],
                        cwd=REPO_ROOT,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        timeout=3600,
                        check=False,
                    )
                if completed.returncode != 0:
                    log(
                        args.queue_root,
                        {
                            "event": "rebuild_failed",
                            "story_id": story_id,
                            "returncode": completed.returncode,
                            "output_tail": completed.stdout[-2000:],
                        },
                    )
                    return completed.returncode
                request_path.unlink()
                log(
                    args.queue_root,
                    {"event": "rebuild_complete", "story_id": story_id},
                )
            except Exception as error:
                log(
                    args.queue_root,
                    {"event": "request_failed", "message": str(error)},
                )
                return 1
        log(args.queue_root, {"event": "worker_idle_exit"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
