"""Deprecated adapter for the installable :mod:`brjarvis.web.api` package."""

from __future__ import annotations

import warnings

from brjarvis.web import api as _canonical_api

warnings.warn(
    "apps.web.api is deprecated; import brjarvis.web.api instead",
    DeprecationWarning,
    stacklevel=2,
)

# Redirect legacy submodule imports (apps.web.api.server/routes/...) to the
# canonical package without keeping a second implementation.
__path__ = _canonical_api.__path__
create_app = _canonical_api.create_app

__all__ = ["create_app"]
