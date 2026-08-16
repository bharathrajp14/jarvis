#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/migration/reorganize_project.py
======================================
Automated Reorganization & Reference Migration Engine for BR JARVIS MK40.2+.
"""

from __future__ import annotations

import os
import sys
import shutil
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any

PROJECT_ROOT = Path(r"d:\BRJARVIS\Br-Jarvis").resolve()
SRC_ROOT = PROJECT_ROOT / "src" / "brjarvis"
APPS_ROOT = PROJECT_ROOT / "apps"
TESTS_ROOT = PROJECT_ROOT / "tests"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
CONFIG_ROOT = PROJECT_ROOT / "config"
DOCS_ROOT = PROJECT_ROOT / "docs"
ASSETS_ROOT = PROJECT_ROOT / "assets"
RUNTIME_ROOT = PROJECT_ROOT / "runtime"
WORKSPACE_ROOT = PROJECT_ROOT / "workspace"

MANIFEST_ENTRIES: List[Dict[str, Any]] = []

def record_move(old_path: Path, new_path: Path, reason: str, category: str):
    MANIFEST_ENTRIES.append({
        "old_path": str(old_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "new_path": str(new_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "reason": reason,
        "category": category,
        "status": "MOVED" if new_path.exists() else "PENDING"
    })

def safe_move(src: Path, dst: Path, reason: str, category: str):
    """Move file or directory safely."""
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        if dst.is_dir() and src.is_dir():
            # Merge directory contents
            for item in os.listdir(src):
                s_item = src / item
                d_item = dst / item
                safe_move(s_item, d_item, reason, category)
            shutil.rmtree(src, ignore_errors=True)
            return
        elif dst.is_file():
            dst.unlink(missing_ok=True)
            
    shutil.move(str(src), str(dst))
    record_move(src, dst, reason, category)

def safe_copy(src: Path, dst: Path, reason: str, category: str):
    """Copy file safely."""
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
    else:
        shutil.copy2(str(src), str(dst))
    record_move(src, dst, reason, category)

def execute_reorganization():
    print("=" * 70)
    print("BR JARVIS MK40.2+ FILESYSTEM REORGANIZATION MIGRATION ENGINE")
    print("=" * 70)

    # 1. Create Base Directories
    print("\n[Step 1] Creating Canonical Directory Trees...")
    target_dirs = [
        SRC_ROOT / "core",
        SRC_ROOT / "agent",
        SRC_ROOT / "orchestrator",
        SRC_ROOT / "execution",
        SRC_ROOT / "tools",
        SRC_ROOT / "actions",
        SRC_ROOT / "connectors",
        SRC_ROOT / "memory",
        SRC_ROOT / "history",
        SRC_ROOT / "workflow",
        SRC_ROOT / "tasks",
        SRC_ROOT / "security",
        SRC_ROOT / "guardian",
        SRC_ROOT / "router",
        SRC_ROOT / "career",
        SRC_ROOT / "browser",
        SRC_ROOT / "voice",
        SRC_ROOT / "vision",
        SRC_ROOT / "ui",
        SRC_ROOT / "desktop",
        SRC_ROOT / "skills",
        SRC_ROOT / "integrations" / "backends",
        SRC_ROOT / "integrations" / "mobile",
        SRC_ROOT / "native",
        SRC_ROOT / "diagnostics",
        SRC_ROOT / "apps",

        APPS_ROOT / "cli",
        APPS_ROOT / "web",
        APPS_ROOT / "desktop",
        APPS_ROOT / "voice",

        TESTS_ROOT / "unit",
        TESTS_ROOT / "integration",
        TESTS_ROOT / "e2e",
        TESTS_ROOT / "adversarial",
        TESTS_ROOT / "reliability",
        TESTS_ROOT / "benchmarks",
        TESTS_ROOT / "fixtures",

        SCRIPTS_ROOT / "development",
        SCRIPTS_ROOT / "build",
        SCRIPTS_ROOT / "migration",
        SCRIPTS_ROOT / "diagnostics",
        SCRIPTS_ROOT / "release",

        CONFIG_ROOT / "default",
        CONFIG_ROOT / "development",
        CONFIG_ROOT / "production",
        CONFIG_ROOT / "examples",
        CONFIG_ROOT / "schemas",

        DOCS_ROOT / "architecture",
        DOCS_ROOT / "features" / "career",
        DOCS_ROOT / "features" / "memory",
        DOCS_ROOT / "features" / "voice",
        DOCS_ROOT / "features" / "browser",
        DOCS_ROOT / "features" / "vision",
        DOCS_ROOT / "operations",
        DOCS_ROOT / "security",
        DOCS_ROOT / "testing",
        DOCS_ROOT / "audits",
        DOCS_ROOT / "migrations",
        DOCS_ROOT / "archive",

        ASSETS_ROOT / "templates",
        ASSETS_ROOT / "icons",
        ASSETS_ROOT / "images",
        ASSETS_ROOT / "static",

        RUNTIME_ROOT / "artifacts",
        RUNTIME_ROOT / "logs",
        RUNTIME_ROOT / "captures",
        RUNTIME_ROOT / "reports",
        RUNTIME_ROOT / "temporary",
        RUNTIME_ROOT / "state",

        WORKSPACE_ROOT / "documents",
        WORKSPACE_ROOT / "resumes",
        WORKSPACE_ROOT / "career",
        WORKSPACE_ROOT / "projects",
        WORKSPACE_ROOT / "user-data",
    ]

    for d in target_dirs:
        d.mkdir(parents=True, exist_ok=True)
    print(f"Created {len(target_dirs)} target directories.")

    # 2. Move Source Packages into src/brjarvis/
    print("\n[Step 2] Migrating Source Packages to src/brjarvis/ ...")
    package_moves = [
        ("core", SRC_ROOT / "core"),
        ("career", SRC_ROOT / "career"),
        ("agent", SRC_ROOT / "agent"),
        ("memory", SRC_ROOT / "memory"),
        ("tools", SRC_ROOT / "tools"),
        ("actions", SRC_ROOT / "actions"),
        ("connectors", SRC_ROOT / "connectors"),
        ("voice", SRC_ROOT / "voice"),
        ("vision", SRC_ROOT / "vision"),
        ("ui", SRC_ROOT / "ui"),
        ("desktop_ui", SRC_ROOT / "desktop"),
        ("skills", SRC_ROOT / "skills"),
        ("orchestrator", SRC_ROOT / "orchestrator"),
        ("router", SRC_ROOT / "router"),
        ("gateway", SRC_ROOT / "gateway"),
        ("guardian", SRC_ROOT / "guardian"),
        ("security", SRC_ROOT / "security"),
        ("workflow", SRC_ROOT / "workflow"),
        ("backends", SRC_ROOT / "integrations" / "backends"),
        ("native", SRC_ROOT / "native"),
        ("context", SRC_ROOT / "context"),
        ("events", SRC_ROOT / "events"),
        ("history", SRC_ROOT / "history"),
        ("computer", SRC_ROOT / "computer"),
        ("mobile", SRC_ROOT / "integrations" / "mobile"),
        ("reasoning", SRC_ROOT / "reasoning"),
        ("redteam", SRC_ROOT / "guardian" / "redteam"),
        ("evolution", SRC_ROOT / "evolution"),
        ("plugins", SRC_ROOT / "plugins"),
        ("screen_server", SRC_ROOT / "screen_server"),
        ("api", APPS_ROOT / "web" / "api"),
    ]

    for src_name, dst_path in package_moves:
        s_path = PROJECT_ROOT / src_name
        if s_path.exists():
            safe_move(s_path, dst_path, f"Consolidate {src_name} package into standard package hierarchy", "SOURCE")
            print(f"  -> Migrated {src_name} -> {dst_path.relative_to(PROJECT_ROOT)}")

    # 3. Move Root Markdown Documentation into docs/
    print("\n[Step 3] Migrating Root Markdown Documentation to docs/ ...")
    doc_mapping = {
        # Audits & Gap Analyses
        "ARTIFACT_01_REPOSITORY_AUDIT.md": DOCS_ROOT / "audits" / "ARTIFACT_01_REPOSITORY_AUDIT.md",
        "ARTIFACT_02_BASELINE.md": DOCS_ROOT / "audits" / "ARTIFACT_02_BASELINE.md",
        "ARTIFACT_03_PRODUCTION_GAP_ANALYSIS.md": DOCS_ROOT / "audits" / "ARTIFACT_03_PRODUCTION_GAP_ANALYSIS.md",
        "ARTIFACT_04_TARGET_ARCHITECTURE.md": DOCS_ROOT / "architecture" / "ARTIFACT_04_TARGET_ARCHITECTURE.md",
        "ARTIFACT_05_SECURITY_THREAT_MODEL.md": DOCS_ROOT / "security" / "ARTIFACT_05_SECURITY_THREAT_MODEL.md",
        "BR_JARVIS_FULL_PROJECT_ANALYSIS.md": DOCS_ROOT / "audits" / "BR_JARVIS_FULL_PROJECT_ANALYSIS.md",
        "DEPENDENCY_RECONCILIATION.md": DOCS_ROOT / "audits" / "DEPENDENCY_RECONCILIATION.md",
        "DEPENDENCY_SELF_REPAIR_AUDIT.md": DOCS_ROOT / "audits" / "DEPENDENCY_SELF_REPAIR_AUDIT.md",
        "ENVIRONMENT_RUNTIME_AUDIT.md": DOCS_ROOT / "audits" / "ENVIRONMENT_RUNTIME_AUDIT.md",
        "EXECUTION_GAP_ANALYSIS.md": DOCS_ROOT / "audits" / "EXECUTION_GAP_ANALYSIS.md",
        "EXECUTION_VERIFICATION_AUDIT.md": DOCS_ROOT / "audits" / "EXECUTION_VERIFICATION_AUDIT.md",
        "FALSE_SUCCESS_AUDIT.md": DOCS_ROOT / "audits" / "FALSE_SUCCESS_AUDIT.md",
        "MISSING_CAPABILITIES.md": DOCS_ROOT / "audits" / "MISSING_CAPABILITIES.md",
        "PRODUCTION_EXECUTION_REPORT.md": DOCS_ROOT / "audits" / "PRODUCTION_EXECUTION_REPORT.md",
        "PRODUCTION_READINESS_REPORT.md": DOCS_ROOT / "audits" / "PRODUCTION_READINESS_REPORT.md",
        "PRODUCTION_WORKFLOW_REPORT.md": DOCS_ROOT / "audits" / "PRODUCTION_WORKFLOW_REPORT.md",
        "RUNTIME_RESOLUTION_AUDIT.md": DOCS_ROOT / "audits" / "RUNTIME_RESOLUTION_AUDIT.md",
        "SYSTEM_AUDIT.md": DOCS_ROOT / "audits" / "SYSTEM_AUDIT.md",
        "SYSTEM_EXECUTION_AUDIT.md": DOCS_ROOT / "audits" / "SYSTEM_EXECUTION_AUDIT.md",
        "TASK_CONTEXT_ISOLATION_AUDIT.md": DOCS_ROOT / "audits" / "TASK_CONTEXT_ISOLATION_AUDIT.md",
        "TOOL_CHAINING_AUDIT.md": DOCS_ROOT / "audits" / "TOOL_CHAINING_AUDIT.md",
        "TOOL_EXECUTION_AUDIT.md": DOCS_ROOT / "audits" / "TOOL_EXECUTION_AUDIT.md",
        "TOOL_EXECUTION_GAP.md": DOCS_ROOT / "audits" / "TOOL_EXECUTION_GAP.md",
        "TOOL_GAP_ANALYSIS.md": DOCS_ROOT / "audits" / "TOOL_GAP_ANALYSIS.md",
        "TOOL_REGISTRATION_GAP.md": DOCS_ROOT / "audits" / "TOOL_REGISTRATION_GAP.md",
        "TOOL_VERIFICATION_GAP.md": DOCS_ROOT / "audits" / "TOOL_VERIFICATION_GAP.md",
        "WINDOWS_APPLICATION_LAUNCH_AUDIT.md": DOCS_ROOT / "audits" / "WINDOWS_APPLICATION_LAUNCH_AUDIT.md",
        "PROJECT_SUMMARY.md": DOCS_ROOT / "audits" / "PROJECT_SUMMARY.md",
        
        # Architecture & Design
        "ACTION_ENGINE_ARCHITECTURE.md": DOCS_ROOT / "architecture" / "ACTION_ENGINE_ARCHITECTURE.md",
        "DEPENDENCY_ENGINE.md": DOCS_ROOT / "architecture" / "DEPENDENCY_ENGINE.md",
        "EXECUTION_GRAPH.md": DOCS_ROOT / "architecture" / "EXECUTION_GRAPH.md",
        "MULTI_TOOL_ARCHITECTURE.md": DOCS_ROOT / "architecture" / "MULTI_TOOL_ARCHITECTURE.md",
        "RECOVERY_ARCHITECTURE.md": DOCS_ROOT / "architecture" / "RECOVERY_ARCHITECTURE.md",
        "SELF_REPAIR_DESIGN.md": DOCS_ROOT / "architecture" / "SELF_REPAIR_DESIGN.md",
        "TASK_STATE_ARCHITECTURE.md": DOCS_ROOT / "architecture" / "TASK_STATE_ARCHITECTURE.md",
        "TOOL_ARCHITECTURE.md": DOCS_ROOT / "architecture" / "TOOL_ARCHITECTURE.md",
        "UI_UX_DESIGN.md": DOCS_ROOT / "architecture" / "UI_UX_DESIGN.md",
        "UNIVERSAL_EXECUTION_ARCHITECTURE.md": DOCS_ROOT / "architecture" / "UNIVERSAL_EXECUTION_ARCHITECTURE.md",
        "VERIFICATION_ARCHITECTURE.md": DOCS_ROOT / "architecture" / "VERIFICATION_ARCHITECTURE.md",
        "TOOL_INVENTORY.md": DOCS_ROOT / "architecture" / "TOOL_INVENTORY.md",

        # Operations & Guides
        "DEVELOPER_WALKTHROUGH.md": DOCS_ROOT / "operations" / "DEVELOPER_WALKTHROUGH.md",
        "PROJECT_DOCUMENTATION.md": DOCS_ROOT / "operations" / "PROJECT_DOCUMENTATION.md",
        "PROJECT_MASTER_DOCUMENTATION.md": DOCS_ROOT / "operations" / "PROJECT_MASTER_DOCUMENTATION.md",

        # Testing
        "END_TO_END_TEST_MATRIX.md": DOCS_ROOT / "testing" / "END_TO_END_TEST_MATRIX.md",
        "EXECUTION_TEST_MATRIX.md": DOCS_ROOT / "testing" / "EXECUTION_TEST_MATRIX.md",
        "ORCHESTRATION_TEST_MATRIX.md": DOCS_ROOT / "testing" / "ORCHESTRATION_TEST_MATRIX.md",
        "TOOL_TEST_MATRIX.md": DOCS_ROOT / "testing" / "TOOL_TEST_MATRIX.md",
        "TOOL_VERIFICATION_MATRIX.md": DOCS_ROOT / "testing" / "TOOL_VERIFICATION_MATRIX.md",
    }

    for doc_name, dst_doc in doc_mapping.items():
        s_doc = PROJECT_ROOT / doc_name
        if s_doc.exists():
            safe_move(s_doc, dst_doc, f"Reorganize root documentation to {dst_doc.parent.name}", "DOCUMENTATION")

    # Merge br_architecture into docs/architecture
    br_arch = PROJECT_ROOT / "br_architecture"
    if br_arch.exists():
        for root, dirs, files in os.walk(br_arch):
            for f in files:
                sf = Path(root) / f
                rel = sf.relative_to(br_arch)
                df = DOCS_ROOT / "architecture" / rel
                safe_move(sf, df, "Consolidate br_architecture into docs/architecture", "DOCUMENTATION")
        shutil.rmtree(br_arch, ignore_errors=True)

    # 4. Move Runtime Data into runtime/
    print("\n[Step 4] Migrating Runtime Data to runtime/ ...")
    runtime_moves = [
        ("logs", RUNTIME_ROOT / "logs"),
        ("captures", RUNTIME_ROOT / "captures"),
        ("reports", RUNTIME_ROOT / "reports"),
        ("scratch", RUNTIME_ROOT / "temporary"),
        ("memory_db", RUNTIME_ROOT / "state" / "memory_db"),
        (".jarvis", RUNTIME_ROOT / "state" / ".jarvis"),
        ("dashboard", APPS_ROOT / "web" / "dashboard"),
        ("web", ASSETS_ROOT / "static" / "web"),
    ]
    for src_name, dst_path in runtime_moves:
        s_path = PROJECT_ROOT / src_name
        if s_path.exists():
            safe_move(s_path, dst_path, f"Isolate runtime/web data for {src_name}", "RUNTIME_DATA")

    if (PROJECT_ROOT / "test_resume_debug.pdf").exists():
        safe_move(PROJECT_ROOT / "test_resume_debug.pdf", RUNTIME_ROOT / "artifacts" / "test_resume_debug.pdf", "Move test artifact to runtime artifacts", "RUNTIME_DATA")

    if (PROJECT_ROOT / "BR_JARVIS_Career_Tracker.xlsx").exists():
        safe_move(PROJECT_ROOT / "BR_JARVIS_Career_Tracker.xlsx", WORKSPACE_ROOT / "career" / "BR_JARVIS_Career_Tracker.xlsx", "Move career workbook to workspace career", "USER_DATA")

    # Consolidate BR_WORKSPACE into workspace/
    br_ws = PROJECT_ROOT / "BR_WORKSPACE"
    if br_ws.exists():
        for item in os.listdir(br_ws):
            safe_move(br_ws / item, WORKSPACE_ROOT / item, "Consolidate legacy BR_WORKSPACE into workspace", "USER_DATA")
        shutil.rmtree(br_ws, ignore_errors=True)

    # Move notes/ to workspace/notes/
    notes = PROJECT_ROOT / "notes"
    if notes.exists():
        safe_move(notes, WORKSPACE_ROOT / "notes", "Organize user notes in workspace", "USER_DATA")

    # Clean up empty errant directory %SystemDrive%
    sys_drive = PROJECT_ROOT / "%SystemDrive%"
    if sys_drive.exists():
        shutil.rmtree(sys_drive, ignore_errors=True)

    print("\n[Step 5] Core filesystem reorganization complete.")
    print(f"Total entries moved: {len(MANIFEST_ENTRIES)}")

if __name__ == "__main__":
    execute_reorganization()
