"""Cross-process lock for repository writers and Git synchronization."""

from __future__ import annotations

from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
from typing import Iterator, TextIO


LOCK_PATH = Path("/home/neko/.local/state/neko/repository-write.lock")


@contextmanager
def repository_write_lock(
    *,
    blocking: bool = True,
    path: Path = LOCK_PATH,
) -> Iterator[TextIO | None]:
    """Serialize story generation/rendering and Git; nonblocking yields None."""

    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    handle = path.open("a+", encoding="utf-8")
    os.chmod(path, 0o600)
    flags = fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB)
    try:
        try:
            fcntl.flock(handle, flags)
        except BlockingIOError:
            handle.close()
            yield None
            return
        yield handle
    finally:
        if not handle.closed:
            fcntl.flock(handle, fcntl.LOCK_UN)
            handle.close()
