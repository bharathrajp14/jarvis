"""Cleanup and Hygiene Script for BR JARVIS MK40.2+."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import sys

if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent


def cleanup():
    print("[CLEANUP] Starting BR JARVIS Repository Hygiene & Cleanup...")

    # 1. Remove %SystemDrive% errant directory
    sys_drive = ROOT / "%SystemDrive%"
    if sys_drive.exists():
        try:
            shutil.rmtree(sys_drive)
            print("  [CLEANED] Removed errant %SystemDrive% folder.")
        except Exception as e:
            print(f"  [NOTE] Could not remove %SystemDrive%: {e}")

    # 2. Clean lingering test folders in workspace/
    ws = ROOT / "workspace"
    if ws.exists():
        count = 0
        for item in ws.iterdir():
            if item.is_dir() and (item.name.startswith("test_temp_") or item.name.startswith("tmp_")):
                try:
                    shutil.rmtree(item)
                    count += 1
                except Exception:
                    pass
        if count > 0:
            print(f"  [CLEANED] Removed {count} lingering test temporary folders in workspace/.")

    # 3. Clean source-tree pollution in src/brjarvis/
    src_clean_targets = [
        ROOT / "src" / "brjarvis" / "logs",
        ROOT / "src" / "brjarvis" / "memory_db",
        ROOT / "src" / "brjarvis" / ".jarvis",
        ROOT / "src" / "brjarvis" / "captures",
        ROOT / "src" / "brjarvis" / "notes",
        ROOT / "src" / "brjarvis" / "reports",
        ROOT / "src" / "brjarvis" / "integrations" / "workspace",
        ROOT / "src" / "brjarvis" / "tasks",
        ROOT / "src" / "brjarvis" / "browser",
        ROOT / "src" / "brjarvis" / "BR_JARVIS_Career_Tracker.xlsx",
        ROOT / "src" / "brjarvis" / "test_generated_walkthrough.md",
        ROOT / "src" / "brjarvis" / ".guardian_hashes.json",
        ROOT / "src" / "brjarvis" / "memory" / "processed_messages.db",
        ROOT / "src" / "brjarvis" / "native" / ".fallback_active",
        ROOT / "memory" / "processed_messages.db",
        ROOT / "memory_db" / "lessons.db",
    ]

    for target in src_clean_targets:
        if target.exists():
            try:
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
                print(f"  [CLEANED] Removed {target.relative_to(ROOT)}")
            except Exception as e:
                print(f"  [NOTE] Could not remove {target.name}: {e}")

    # 4. Clean duplicate subdirectories in scripts/
    dup_script_dirs = [
        ROOT / "scripts" / "diagnostics",
        ROOT / "scripts" / "build",
        ROOT / "scripts" / "development",
        ROOT / "scripts" / "migration",
        ROOT / "scripts" / "release",
    ]
    for sdir in dup_script_dirs:
        if sdir.exists():
            try:
                shutil.rmtree(sdir)
                print(f"  [CLEANED] Removed redundant directory: {sdir.relative_to(ROOT)}")
            except Exception as e:
                print(f"  [NOTE] Could not remove {sdir.name}: {e}")

    print("[SUCCESS] Repository Hygiene & Cleanup Complete!\n")


if __name__ == "__main__":
    cleanup()
