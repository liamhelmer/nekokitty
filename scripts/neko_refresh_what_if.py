#!/usr/bin/env python3
"""Atomically refresh Neko's offline What If schedule cache."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neko.event_schedule import BASE_URL, DEFAULT_STATE_DIR, refresh_cache  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()
    try:
        database = refresh_cache(args.state_dir, base_url=args.base_url, timeout_s=args.timeout)
    except Exception as error:
        print(f"What If refresh failed; existing cache retained: {error}", file=sys.stderr)
        return 1
    print(database)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

