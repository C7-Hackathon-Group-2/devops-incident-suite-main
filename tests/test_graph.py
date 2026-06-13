"""Tests for graph.py — LangGraph orchestrator wiring and routing.

Includes unit tests for the ``route_by_severity`` function and
integration-level tests that run the compiled graph end-to-end with
mocked LLM, Slack, and JIRA backends.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from graph import build_incident_graph, route_by_severity


class TestRouteBySeverity:
    """Verify the conditional-edge routing function."""

    @pytest.mark.parametrize(
        "remediations,expected",
        [
            ([{"severity": "warning"}, {"severity": "critical"}], "critical"),
            ([{"severity": "warning"}, {"severity": "info"}], "normal"),
            ([], "normal"),
        ],
        ids=["has-critical", "no-critical", "empty-list"],
    )
    def test_returns_correct_route(
        self, remediations: list[dict[str, str]], expected: str
    ) -> None:
        """The route should be ``critical`` iff any remediation is critical."""
        state: dict[str, Any] = {"remediations": remediations}
        assert route_by_severity(state) == expected

    def test_returns_normal_when_remediations_key_missing(self) -> None:
        """A state dict without ``remediations`` should default to ``normal``."""
        assert route_by_severity({}) == "normal"


class TestBuildIncidentGraph:
    """Verify graph compilation and end-to-end pipeline execution."""

    def test_graph_compiles_without_error(self) -> None:
        """``build_incident_graph()`` should return a non-None compiled graph."""
        graph = build_incident_graph()
        assert graph is not None

    def test_graph_contains_all_expected_nodes(self) -> None:
        """The compiled graph should contain all five agent nodes."""
        graph = build_incident_graph()
        node_names: set[str] = set(graph.nodes.keys())
        expected: set[str] = {"log_reader", "remediation", "notification", "jira", "cookbook"}
        assert expected.issubset(node_names)

    @patch("agents.LLM_JSON")
    @patch("agents.LLM")
    @patch("agents.send_slack_message")
    @patch("agents.create_jira_ticket")
    def test_critical_path_traverses_all_five_nodes(
        self,
        mock_jira: MagicMock,
        mock_slack: MagicMock,
        mock_llm: MagicMock,
        mock_llm_json: MagicMock,
        empty_state: dict[str, Any],
    ) -> None:
        """Critical events should flow through all five nodes end-to-end."""
        # Arrange — LLM responses for log_reader (3) + remediation (1)
        schema_resp: MagicMock = MagicMock()
        schema_resp.content = json.dumps({"format_name": "test", "fields": []})

        events_resp: MagicMock = MagicMock()
        events_resp.content = json.dumps({"events": [{"msg": "link down"}]})

        classify_resp: MagicMock = MagicMock()
        classify_resp.content = json.dumps({
            "classified": [{
                "msg": "link down", "severity": "critical",
                "category": "interface", "summary": "Link failure",
            }],
        })

        remed_resp: MagicMock = MagicMock()
        remed_resp.content = json.dumps({
            "remediations": [{
                "issue_id": "i1", "title": "Link down", "severity": "critical",
                "category": "interface", "affected_systems": ["rtr-01"],
                "root_cause": "Cable fault", "remediation_steps": ["Replace cable"],
                "cli_commands": ["show interface"], "verification": "ping",
                "risk_level": "low",
            }],
        })

        mock_llm_json.invoke.side_effect = [
            schema_resp, events_resp, classify_resp, remed_resp,
        ]

        cookbook_resp: MagicMock = MagicMock()
        cookbook_resp.content = "# Runbook\n## Summary\nLink fixed."
        mock_llm.invoke.return_value = cookbook_resp

        mock_slack.invoke.return_value = json.dumps(
            {"mock": True, "channel": "#network-incidents"}
        )
        mock_jira.invoke.return_value = json.dumps({"mock": True, "key": "OPS-001"})

        empty_state["raw_logs"] = {"test.log": "link down"}

        # Act
        graph = build_incident_graph()
        result: dict[str, Any] = graph.invoke(empty_state)

        # Assert
        assert result["status"] == "complete"
        assert len(result["classified_events"]) == 1
        assert len(result["remediations"]) == 1
        assert len(result["notifications_sent"]) == 1
        assert len(result["jira_tickets"]) == 1
        assert "# Runbook" in result["cookbook"]

    @patch("agents.LLM_JSON")
    @patch("agents.LLM")
    def test_normal_path_skips_slack_and_jira(
        self,
        mock_llm: MagicMock,
        mock_llm_json: MagicMock,
        empty_state: dict[str, Any],
    ) -> None:
        """Non-critical events should skip the notification and JIRA nodes."""
        # Arrange
        schema_resp: MagicMock = MagicMock()
        schema_resp.content = json.dumps({"format_name": "test", "fields": []})

        events_resp: MagicMock = MagicMock()
        events_resp.content = json.dumps({"events": [{"msg": "all good"}]})

        classify_resp: MagicMock = MagicMock()
        classify_resp.content = json.dumps({
            "classified": [{
                "msg": "all good", "severity": "info",
                "category": "application", "summary": "Healthy",
            }],
        })

        mock_llm_json.invoke.side_effect = [schema_resp, events_resp, classify_resp]

        cookbook_resp: MagicMock = MagicMock()
        cookbook_resp.content = "# Runbook\nNo issues."
        mock_llm.invoke.return_value = cookbook_resp

        empty_state["raw_logs"] = {"test.log": "all good"}

        # Act
        graph = build_incident_graph()
        result: dict[str, Any] = graph.invoke(empty_state)

        # Assert
        assert result["status"] == "complete"
        assert result["notifications_sent"] == []
        assert result["jira_tickets"] == []
        assert "No actionable issues" in result["cookbook"]
