"""Tests for state.py — IncidentState TypedDict schema validation."""

from __future__ import annotations

from typing import Any

from state import IncidentState


class TestIncidentState:
    """Verify IncidentState TypedDict instantiation and field access."""

    def test_empty_state_has_correct_defaults(self) -> None:
        """An empty state should be instantiable with all required keys."""
        # Arrange / Act
        state: IncidentState = {
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

        # Assert
        assert state["status"] == "starting"
        assert isinstance(state["raw_logs"], dict)
        assert isinstance(state["errors"], list)

    def test_populated_state_preserves_data(self) -> None:
        """A fully populated state should round-trip all field values."""
        # Arrange / Act
        state: IncidentState = {
            "raw_logs": {"router.log": "line1\nline2"},
            "inferred_schemas": {"router.log": [{"field": "ts"}]},
            "parsed_events": [{"ts": "2026-01-01", "msg": "up"}],
            "classified_events": [{"severity": "critical", "category": "interface"}],
            "remediations": [{"title": "Fix link", "severity": "critical"}],
            "cookbook": "# Runbook",
            "notifications_sent": [{"channel": "#ops"}],
            "jira_tickets": [{"key": "OPS-1"}],
            "status": "complete",
            "errors": ["something failed"],
        }

        # Assert
        assert len(state["parsed_events"]) == 1
        assert state["cookbook"].startswith("#")
