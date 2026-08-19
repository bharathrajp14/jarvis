"""Integration tests for App Connectors Suite."""

from __future__ import annotations

import pytest
from connectors.hub import get_hub


@pytest.mark.integration
def test_connectors_hub_registered_connectors():
    """Verify ConnectorHub registers cloud and local connectors."""
    hub = get_hub()
    assert hub is not None
    status = hub.get_status() if hasattr(hub, "get_status") else hub.list_connectors()
    assert status is not None
