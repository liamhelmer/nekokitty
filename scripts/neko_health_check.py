#!/usr/bin/env python3
"""Print a privacy-safe JSON health report for Neko's essential services."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neko.local_commands import check_services  # noqa: E402


def main() -> int:
    report = check_services()
    print(json.dumps({
        "healthy": report.healthy,
        "problems": [
            {"unit": problem.unit, "issue": problem.issue}
            for problem in report.problems
        ],
    }))
    return 0 if report.healthy else 1


if __name__ == "__main__":
    raise SystemExit(main())
