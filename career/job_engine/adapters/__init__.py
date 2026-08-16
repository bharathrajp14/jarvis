# career/job_engine/adapters/__init__.py — Job Adapters Subsystem Package
from __future__ import annotations

from career.job_engine.adapters.base import BasePlatformAdapter
from career.job_engine.adapters.greenhouse import GreenhouseAdapter
from career.job_engine.adapters.lever import LeverAdapter
from career.job_engine.adapters.ashby import AshbyAdapter
from career.job_engine.adapters.generic_browser import GenericBrowserAdapter
from career.job_engine.adapters.company_site import CompanySiteAdapter

__all__ = [
    "BasePlatformAdapter",
    "GreenhouseAdapter",
    "LeverAdapter",
    "AshbyAdapter",
    "GenericBrowserAdapter",
    "CompanySiteAdapter",
]
