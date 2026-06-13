"""Tests for tools.py — channel routing, Slack, and JIRA tools.

Follows the AAA (Arrange-Act-Assert) pattern throughout.  Channel
routing is exhaustively tested with ``@pytest.mark.parametrize`` to
cover every category in a single concise test.
"""

from __future__ import annotations

import json
import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import tools
from tools import (
    CHANNEL_ROUTING,
    DEFAULT_CHANNEL,
    create_jira_ticket,
    route_to_channel,
    send_slack_message,
)


class TestRouteToChannel:
    """Verify that every incident category maps to the correct Slack channel."""

    @pytest.mark.parametrize(
        "category,expected_channel",
        [
            ("security", "#secops-incidents"),
            ("auth", "#secops-incidents"),
            ("policy", "#secops-incidents"),
            ("interface", "#network-incidents"),
            ("routing", "#network-incidents"),
            ("network", "#network-incidents"),
            ("hardware", "#network-incidents"),
            ("resource", "#ops-incidents"),
            ("application", "#ops-incidents"),
            ("database", "#ops-incidents"),
        ],
    )
    def test_known_category_routes_correctly(
        self, category: str, expected_channel: str
    ) -> None:
        """Each known category should map to its designated channel."""
        assert route_to_channel(category) == expected_channel

    def test_unknown_category_falls_back_to_default(self) -> None:
        """An unrecognised category should return ``DEFAULT_CHANNEL``."""
        assert route_to_channel("unknown_thing") == DEFAULT_CHANNEL

    @pytest.mark.parametrize(
        "category,expected_channel",
        [
            ("SECURITY", "#secops-incidents"),
            ("Interface", "#network-incidents"),
        ],
    )
    def test_routing_is_case_insensitive(
        self, category: str, expected_channel: str
    ) -> None:
        """Category matching should be case-insensitive."""
        assert route_to_channel(category) == expected_channel

    def test_all_routing_keys_are_exercised(self) -> None:
        """Every key in ``CHANNEL_ROUTING`` should resolve correctly."""
        for key, channel in CHANNEL_ROUTING.items():
            assert route_to_channel(key) == channel


class TestSendSlackMock:
    """Verify Slack message delivery in mock mode."""

    @patch.object(tools, "SLACK_MOCK", True)
    def test_mock_returns_would_send_payload(self) -> None:
        """Mock mode should return a JSON envelope with ``mock: true``."""
        # Act
        result: str = send_slack_message.invoke({"channel": "#test", "text": "hello"})
        data: dict[str, Any] = json.loads(result)

        # Assert
        assert data["mock"] is True
        assert data["channel"] == "#test"
        assert data["text"] == "hello"
        assert data["status"] == "would_send"
        assert "timestamp" in data

    @patch.object(tools, "SLACK_MOCK", True)
    def test_mock_preserves_target_channel(self) -> None:
        """The returned payload should echo the requested channel."""
        result: str = send_slack_message.invoke(
            {"channel": "#secops-incidents", "text": "alert"}
        )
        data: dict[str, Any] = json.loads(result)
        assert data["channel"] == "#secops-incidents"


class TestSendSlackLive:
    """Verify Slack message delivery in live mode."""

    @patch.object(tools, "SLACK_MOCK", False)
    @patch.dict(os.environ, {"SLACK_WEBHOOK_URL": ""}, clear=False)
    def test_missing_webhook_returns_error(self) -> None:
        """Live mode without a webhook URL should return an error payload."""
        result: str = send_slack_message.invoke({"channel": "#test", "text": "hello"})
        data: dict[str, Any] = json.loads(result)
        assert "error" in data

    @patch.object(tools, "SLACK_MOCK", False)
    @patch.dict(
        os.environ,
        {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"},
        clear=False,
    )
    @patch("tools.requests.post")
    def test_live_posts_to_webhook_url(self, mock_post: MagicMock) -> None:
        """Live mode should POST to the configured webhook and return status."""
        # Arrange
        mock_resp: MagicMock = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "ok"
        mock_post.return_value = mock_resp

        # Act
        result: str = send_slack_message.invoke({"channel": "#ops", "text": "incident"})
        data: dict[str, Any] = json.loads(result)

        # Assert
        assert data["mock"] is False
        assert data["channel"] == "#ops"
        assert data["status_code"] == 200
        mock_post.assert_called_once()
        assert mock_post.call_args[1]["json"]["channel"] == "#ops"


class TestCreateJiraMock:
    """Verify JIRA ticket creation in mock mode."""

    @patch.object(tools, "JIRA_MOCK", True)
    def test_mock_returns_ticket_with_ops_prefix(self) -> None:
        """Mock mode should return a ticket key starting with ``OPS-``."""
        # Act
        result: str = create_jira_ticket.invoke({
            "summary": "Test issue",
            "description": "Description",
            "priority": "critical",
        })
        data: dict[str, Any] = json.loads(result)

        # Assert
        assert data["mock"] is True
        assert data["key"].startswith("OPS-")
        assert data["summary"] == "Test issue"
        assert data["priority"] == "critical"
        assert data["status"] == "would_create"

    @patch.object(tools, "JIRA_MOCK", True)
    def test_mock_ticket_key_has_expected_length(self) -> None:
        """The mock ticket key should be ``OPS-HHMMSS`` (10 chars)."""
        result: str = create_jira_ticket.invoke({
            "summary": "s",
            "description": "d",
            "priority": "warning",
        })
        data: dict[str, Any] = json.loads(result)
        assert len(data["key"]) == 10


class TestCreateJiraLive:
    """Verify JIRA ticket creation in live mode."""

    @patch.object(tools, "JIRA_MOCK", False)
    @patch.dict(
        os.environ,
        {"JIRA_URL": "", "JIRA_API_TOKEN": "", "JIRA_EMAIL": ""},
        clear=False,
    )
    def test_missing_credentials_returns_error(self) -> None:
        """Live mode without credentials should return an error payload."""
        result: str = create_jira_ticket.invoke({
            "summary": "s",
            "description": "d",
            "priority": "critical",
        })
        data: dict[str, Any] = json.loads(result)
        assert "error" in data

    @patch.object(tools, "JIRA_MOCK", False)
    @patch.dict(
        os.environ,
        {
            "JIRA_URL": "https://test.atlassian.net",
            "JIRA_API_TOKEN": "tok",
            "JIRA_EMAIL": "a@b.com",
            "JIRA_PROJECT_KEY": "MYPROJ",
        },
        clear=False,
    )
    @patch("tools.requests.post")
    def test_live_posts_to_jira_rest_api(self, mock_post: MagicMock) -> None:
        """Live mode should POST to the JIRA REST API with correct payload."""
        # Arrange
        mock_resp: MagicMock = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"key": "MYPROJ-42"}
        mock_post.return_value = mock_resp

        # Act
        result: str = create_jira_ticket.invoke({
            "summary": "Critical failure",
            "description": "Router down",
            "priority": "critical",
        })
        data: dict[str, Any] = json.loads(result)

        # Assert
        assert data["mock"] is False
        assert data["key"] == "MYPROJ-42"
        assert data["status_code"] == 201
        mock_post.assert_called_once()
        assert "rest/api/2/issue" in mock_post.call_args[0][0]
        payload: dict[str, Any] = mock_post.call_args[1]["json"]
        assert payload["fields"]["project"]["key"] == "MYPROJ"
        assert payload["fields"]["priority"]["name"] == "Highest"
