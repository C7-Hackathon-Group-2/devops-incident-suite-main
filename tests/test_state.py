"""Tests for state.py — IncidentState TypedDict."""

from state import IncidentState


def test_incident_state_can_be_instantiated():
    s: IncidentState = {
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
    assert s["status"] == "starting"
    assert isinstance(s["raw_logs"], dict)
    assert isinstance(s["errors"], list)


def test_incident_state_accepts_populated_data():
    s: IncidentState = {
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
    assert len(s["parsed_events"]) == 1
    assert s["cookbook"].startswith("#")
