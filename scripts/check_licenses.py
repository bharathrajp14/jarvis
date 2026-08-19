"""Fail CI when installed distributions declare prohibited network-copyleft licenses."""
from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

DENIED_MARKERS = ("AGPL", "AFFERO", "SSPL", "SERVER SIDE PUBLIC LICENSE")


def main() -> int:
    completed = subprocess.run(
        [sys.executable, "-m", "piplicenses", "--format=json"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    packages: list[dict[str, Any]] = json.loads(completed.stdout)
    denied = [
        package
        for package in packages
        if any(marker in str(package.get("License", "")).upper() for marker in DENIED_MARKERS)
    ]
    if denied:
        print("Prohibited dependency licenses detected:")
        for package in denied:
            print(f"- {package.get('Name')} {package.get('Version')}: {package.get('License')}")
        return 1
    print(f"License policy passed for {len(packages)} installed distributions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
