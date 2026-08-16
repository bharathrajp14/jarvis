"""BR JARVIS API Package."""
from __future__ import annotations

import sys
_mod = sys.modules.get(__name__)
if _mod:
    sys.modules["api"] = _mod
    sys.modules["brjarvis.apps.web.api"] = _mod
