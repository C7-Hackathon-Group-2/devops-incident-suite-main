"""Shared pytest configuration and fixtures.

Adds the ``src/`` directory to ``sys.path`` so that test modules can
import application code directly (e.g. ``from state import IncidentState``).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture()
def empty_state() -> dict[str, Any]:
    """Provide a minimal empty ``IncidentState`` dict for pipeline tests.

    Returns:
        A dictionary matching the ``IncidentState`` schema with all
        fields set to their empty/default values.
    """
    return {
        "raw_logs": {},
        "inferred_schemas": {},
        "parsed_events": [],
        "classified_events": [],
        "remediations": [],
        "cookbook": "",
        "notifications_sent": [],
        "jira_tickets": [],
        "status": "starting",
        "errors": [],
    }
