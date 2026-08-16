# career/job_engine/adapters/__init__.py — Job Adapters Subsystem Package
from __future__ import annotations

from .base import BasePlatformAdapter
from .greenhouse import GreenhouseAdapter
from .lever import LeverAdapter
from .ashby import AshbyAdapter
from .generic_browser import GenericBrowserAdapter
from .company_site import CompanySiteAdapter

__all__ = [
    "BasePlatformAdapter",
    "GreenhouseAdapter",
    "LeverAdapter",
    "AshbyAdapter",
    "GenericBrowserAdapter",
    "CompanySiteAdapter",
]
