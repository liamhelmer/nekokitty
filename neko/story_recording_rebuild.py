"""Bounded, low-priority rebuild queue for stale prerecorded stories."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess


QUEUE_ROOT = Path("/var/tmp/neko-story-recording-rebuild")
WORKER = Path(__file__).resolve().parents[1] / "scripts/neko_story_recording_worker.py"
PYTHON = Path("/home/neko/.local/share/neko/venvs/kittentts/bin/python")


def enqueue_story_rebuild(
    story_id: str,
    reason: str,
    *,
    queue_root: Path = QUEUE_ROOT,
    launch: bool = True,
) -> bool:
    """Atomically queue one story and start an inherited low-priority worker."""

    if not story_id or len(story_id) > 200:
        raise ValueError("invalid story ID for rebuild")
    queue_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(queue_root, 0o700)
    request_name = hashlib.sha256(story_id.encode("utf-8")).hexdigest()
    request_path = queue_root / f"request-{request_name}.json"
    temporary = queue_root / f".{request_name}.{os.getpid()}.tmp"
    request = {"schema_version": 1, "story_id": story_id, "reason": reason[:200]}
    newly_queued = not request_path.exists()
    if newly_queued:
        temporary.write_text(json.dumps(request, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(temporary, 0o600)
        try:
            temporary.replace(request_path)
        finally:
            temporary.unlink(missing_ok=True)
    if launch:
        subprocess.Popen(
            [
                "/usr/bin/nice",
                "-n",
                "19",
                "/usr/bin/ionice",
                "-c",
                "3",
                str(PYTHON),
                str(WORKER),
                "--queue-root",
                str(queue_root),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
    return newly_queued
