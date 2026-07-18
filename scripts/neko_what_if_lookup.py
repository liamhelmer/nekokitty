#!/usr/bin/env python3
"""Query Neko's local What If cache without invoking a language model."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neko.event_schedule import DEFAULT_DB, EventSchedule, PACIFIC  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query")
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    parser.add_argument("--now", help="override Pacific reference time as ISO-8601")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    now = datetime.fromisoformat(args.now).replace(tzinfo=PACIFIC) if args.now else None
    schedule = EventSchedule(args.database)
    matches = schedule.search(args.query, now=now, limit=args.limit)
    if args.json:
        print(
            json.dumps(
                [
                    {
                        "source": item.source,
                        "title": item.title,
                        "performer": item.performer,
                        "location": item.location,
                        "start": item.start.isoformat() if item.start else None,
                        "end": item.end.isoformat() if item.end else None,
                        "active": item.active,
                        "score": round(item.score, 6),
                    }
                    for item in matches
                ],
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(schedule.answer(args.query, now=now, limit=args.limit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
