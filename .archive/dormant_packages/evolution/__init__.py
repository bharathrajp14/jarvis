# evolution/__init__.py — Self-Upgrade & Autonomous Evolution Engine
"""
Self-Upgrade Subsystem for BR JARVIS.
Handles automated error/lesson proposal, blast-radius classification, sandbox testing, and deployment.
"""
from evolution.classifier import ChangeClassifier, RiskLevel
from evolution.proposer import PatchProposer
from evolution.sandbox import SandboxRunner
from evolution.digest import ChangeDigest
from evolution.deployer import AutoDeployer

__all__ = [
    "ChangeClassifier",
    "RiskLevel",
    "PatchProposer",
    "SandboxRunner",
    "ChangeDigest",
    "AutoDeployer",
]
