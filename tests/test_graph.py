"""Tests for graph.py — LangGraph orchestrator wiring and routing."""

import json
from unittest.mock import patch, MagicMock

import pytest

from graph import route_by_severity, build_incident_graph


# ---------------------------------------------------------------------------
# route_by_severity
# ---------------------------------------------------------------------------

class TestRouteBySeverity:
    def test_returns_critical_when_critical_present(self):
        state = {"remediations": [
            {"severity": "warning"},
            {"severity": "critical"},
        ]}
        assert route_by_severity(state) == "critical"

    def test_returns_normal_when_no_critical(self):
        state = {"remediations": [
            {"severity": "warning"},
            {"severity": "info"},
        ]}
        assert route_by_severity(state) == "normal"

    def test_returns_normal_when_empty(self):
        state = {"remediations": []}
        assert route_by_severity(state) == "normal"

    def test_returns_normal_when_missing(self):
        state = {}
        assert route_by_severity(state) == "normal"


# ---------------------------------------------------------------------------
# build_incident_graph
# ---------------------------------------------------------------------------

class TestBuildIncidentGraph:
    def test_graph_compiles(self):
        graph = build_incident_graph()
        assert graph is not None

    def test_graph_has_expected_nodes(self):
        graph = build_incident_graph()
        node_names = set(graph.nodes.keys())
        expected = {"log_reader", "remediation", "notification", "jira", "cookbook"}
        assert expected.issubset(node_names)

    @patch("agents.LLM_JSON")
    @patch("agents.LLM")
    @patch("agents.send_slack_message")
    @patch("agents.create_jira_ticket")
    def test_full_pipeline_critical_path(self, mock_jira, mock_slack, mock_llm, mock_llm_json):
        """Test the full pipeline with critical events — goes through all 5 nodes."""
        # log_reader responses (schema, events, classify)
        schema_resp = MagicMock()
        schema_resp.content = json.dumps({"format_name": "test", "fields": []})

        events_resp = MagicMock()
        events_resp.content = json.dumps({"events": [{"msg": "link down"}]})

        classify_resp = MagicMock()
        classify_resp.content = json.dumps({"classified": [
            {"msg": "link down", "severity": "critical", "category": "interface", "summary": "Link failure"}
        ]})

        # remediation response
        remed_resp = MagicMock()
        remed_resp.content = json.dumps({"remediations": [
            {"issue_id": "i1", "title": "Link down", "severity": "critical",
             "category": "interface", "affected_systems": ["rtr-01"],
             "root_cause": "Cable fault", "remediation_steps": ["Replace cable"],
             "cli_commands": ["show interface"], "verification": "ping", "risk_level": "low"}
        ]})

        mock_llm_json.invoke.side_effect = [schema_resp, events_resp, classify_resp, remed_resp]

        # cookbook response
        cookbook_resp = MagicMock()
        cookbook_resp.content = "# Runbook\n## Summary\nLink fixed."
        mock_llm.invoke.return_value = cookbook_resp

        # slack + jira mocks
        mock_slack.invoke.return_value = json.dumps({"mock": True, "channel": "#network-incidents"})
        mock_jira.invoke.return_value = json.dumps({"mock": True, "key": "OPS-001"})

        graph = build_incident_graph()
        result = graph.invoke({
            "raw_logs": {"test.log": "link down"},
            "inferred_schemas": {},
            "parsed_events": [],
            "classified_events": [],
            "remediations": [],
            "cookbook": "",
            "notifications_sent": [],
            "jira_tickets": [],
            "status": "starting",
            "errors": [],
        })

        assert result["status"] == "complete"
        assert len(result["classified_events"]) == 1
        assert len(result["remediations"]) == 1
        assert len(result["notifications_sent"]) == 1
        assert len(result["jira_tickets"]) == 1
        assert "# Runbook" in result["cookbook"]

    @patch("agents.LLM_JSON")
    @patch("agents.LLM")
    def test_pipeline_normal_path_skips_slack_jira(self, mock_llm, mock_llm_json):
        """Test that non-critical events skip notification and JIRA nodes."""
        schema_resp = MagicMock()
        schema_resp.content = json.dumps({"format_name": "test", "fields": []})

        events_resp = MagicMock()
        events_resp.content = json.dumps({"events": [{"msg": "all good"}]})

        classify_resp = MagicMock()
        classify_resp.content = json.dumps({"classified": [
            {"msg": "all good", "severity": "info", "category": "application", "summary": "Healthy"}
        ]})

        mock_llm_json.invoke.side_effect = [schema_resp, events_resp, classify_resp]

        cookbook_resp = MagicMock()
        cookbook_resp.content = "# Runbook\nNo issues."
        mock_llm.invoke.return_value = cookbook_resp

        graph = build_incident_graph()
        result = graph.invoke({
            "raw_logs": {"test.log": "all good"},
            "inferred_schemas": {},
            "parsed_events": [],
            "classified_events": [],
            "remediations": [],
            "cookbook": "",
            "notifications_sent": [],
            "jira_tickets": [],
            "status": "starting",
            "errors": [],
        })

        assert result["status"] == "complete"
        assert result["notifications_sent"] == []
        assert result["jira_tickets"] == []
        assert "No actionable issues" in result["cookbook"]
