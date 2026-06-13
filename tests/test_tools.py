"""Tests for tools.py — channel routing, Slack, and JIRA tools."""

import json
import os
from unittest.mock import patch, MagicMock

import pytest

import tools
from tools import route_to_channel, send_slack_message, create_jira_ticket, CHANNEL_ROUTING, DEFAULT_CHANNEL


# ---------------------------------------------------------------------------
# route_to_channel
# ---------------------------------------------------------------------------

class TestRouteToChannel:
    def test_security_routes_to_secops(self):
        assert route_to_channel("security") == "#secops-incidents"

    def test_auth_routes_to_secops(self):
        assert route_to_channel("auth") == "#secops-incidents"

    def test_policy_routes_to_secops(self):
        assert route_to_channel("policy") == "#secops-incidents"

    def test_interface_routes_to_network(self):
        assert route_to_channel("interface") == "#network-incidents"

    def test_routing_routes_to_network(self):
        assert route_to_channel("routing") == "#network-incidents"

    def test_network_routes_to_network(self):
        assert route_to_channel("network") == "#network-incidents"

    def test_hardware_routes_to_network(self):
        assert route_to_channel("hardware") == "#network-incidents"

    def test_resource_routes_to_ops(self):
        assert route_to_channel("resource") == "#ops-incidents"

    def test_application_routes_to_ops(self):
        assert route_to_channel("application") == "#ops-incidents"

    def test_database_routes_to_ops(self):
        assert route_to_channel("database") == "#ops-incidents"

    def test_unknown_category_defaults_to_ops(self):
        assert route_to_channel("unknown_thing") == DEFAULT_CHANNEL

    def test_case_insensitive(self):
        assert route_to_channel("SECURITY") == "#secops-incidents"
        assert route_to_channel("Interface") == "#network-incidents"

    def test_all_routing_keys_covered(self):
        for key, channel in CHANNEL_ROUTING.items():
            assert route_to_channel(key) == channel


# ---------------------------------------------------------------------------
# send_slack_message — mock mode
# ---------------------------------------------------------------------------

class TestSendSlackMock:
    @patch.object(tools, "SLACK_MOCK", True)
    def test_mock_returns_json_with_mock_flag(self):
        result = send_slack_message.invoke({"channel": "#test", "text": "hello"})
        data = json.loads(result)
        assert data["mock"] is True
        assert data["channel"] == "#test"
        assert data["text"] == "hello"
        assert data["status"] == "would_send"
        assert "timestamp" in data

    @patch.object(tools, "SLACK_MOCK", True)
    def test_mock_preserves_channel_name(self):
        result = send_slack_message.invoke({"channel": "#secops-incidents", "text": "alert"})
        data = json.loads(result)
        assert data["channel"] == "#secops-incidents"


# ---------------------------------------------------------------------------
# send_slack_message — live mode
# ---------------------------------------------------------------------------

class TestSendSlackLive:
    @patch.object(tools, "SLACK_MOCK", False)
    @patch.dict(os.environ, {"SLACK_WEBHOOK_URL": ""}, clear=False)
    def test_live_no_webhook_returns_error(self):
        result = send_slack_message.invoke({"channel": "#test", "text": "hello"})
        data = json.loads(result)
        assert "error" in data

    @patch.object(tools, "SLACK_MOCK", False)
    @patch.dict(os.environ, {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=False)
    @patch("tools.requests.post")
    def test_live_posts_to_webhook(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "ok"
        mock_post.return_value = mock_resp

        result = send_slack_message.invoke({"channel": "#ops", "text": "incident"})
        data = json.loads(result)

        assert data["mock"] is False
        assert data["channel"] == "#ops"
        assert data["status_code"] == 200
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs[1]["json"]["channel"] == "#ops"


# ---------------------------------------------------------------------------
# create_jira_ticket — mock mode
# ---------------------------------------------------------------------------

class TestCreateJiraMock:
    @patch.object(tools, "JIRA_MOCK", True)
    def test_mock_returns_json_with_ticket_key(self):
        result = create_jira_ticket.invoke({
            "summary": "Test issue",
            "description": "Description",
            "priority": "critical",
        })
        data = json.loads(result)
        assert data["mock"] is True
        assert data["key"].startswith("OPS-")
        assert data["summary"] == "Test issue"
        assert data["priority"] == "critical"
        assert data["status"] == "would_create"

    @patch.object(tools, "JIRA_MOCK", True)
    def test_mock_ticket_key_format(self):
        result = create_jira_ticket.invoke({
            "summary": "s", "description": "d", "priority": "warning",
        })
        data = json.loads(result)
        assert len(data["key"]) == 10  # OPS-HHMMSS


# ---------------------------------------------------------------------------
# create_jira_ticket — live mode
# ---------------------------------------------------------------------------

class TestCreateJiraLive:
    @patch.object(tools, "JIRA_MOCK", False)
    @patch.dict(os.environ, {"JIRA_URL": "", "JIRA_API_TOKEN": "", "JIRA_EMAIL": ""}, clear=False)
    def test_live_no_creds_returns_error(self):
        result = create_jira_ticket.invoke({
            "summary": "s", "description": "d", "priority": "critical",
        })
        data = json.loads(result)
        assert "error" in data

    @patch.object(tools, "JIRA_MOCK", False)
    @patch.dict(os.environ, {
        "JIRA_URL": "https://test.atlassian.net",
        "JIRA_API_TOKEN": "tok",
        "JIRA_EMAIL": "a@b.com",
        "JIRA_PROJECT_KEY": "MYPROJ",
    }, clear=False)
    @patch("tools.requests.post")
    def test_live_posts_to_jira_api(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"key": "MYPROJ-42"}
        mock_post.return_value = mock_resp

        result = create_jira_ticket.invoke({
            "summary": "Critical failure",
            "description": "Router down",
            "priority": "critical",
        })
        data = json.loads(result)

        assert data["mock"] is False
        assert data["key"] == "MYPROJ-42"
        assert data["status_code"] == 201
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "rest/api/2/issue" in call_args[0][0]
        payload = call_args[1]["json"]
        assert payload["fields"]["project"]["key"] == "MYPROJ"
        assert payload["fields"]["priority"]["name"] == "Highest"
