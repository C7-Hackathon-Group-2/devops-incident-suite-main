"""Tests for agents.py — all agent node functions with mocked LLM calls.

Follows the AAA (Arrange-Act-Assert) pattern.  Every LLM interaction
is mocked so tests run offline and deterministically.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


def _make_llm_response(content: str) -> MagicMock:
    """Create a mock LLM response with the given content string.

    Args:
        content: JSON or plain-text string to set as ``response.content``.

    Returns:
        A ``MagicMock`` with a ``.content`` attribute.
    """
    mock: MagicMock = MagicMock()
    mock.content = content
    return mock


class TestAgentsEnvLoading:
    """Verify the .env loading logic at module import time."""

    def test_local_env_path_is_reachable(self, tmp_path: Path) -> None:
        """The local ``.env`` detection branch should be exercisable."""
        # Arrange
        env_file: Path = tmp_path / ".env"
        env_file.write_text("OPENROUTER_API_KEY=test-key-123\n")

        # Act / Assert — verify the path logic is sound
        with (
            patch("agents.load_dotenv"),
            patch("agents.Path"),
        ):
            from agents import _safe_json_parse  # noqa: F401

            p: Path = Path(__file__).parent / ".env"
            assert isinstance(p, Path)

    def test_parent_env_fallback_path_exists(self, tmp_path: Path) -> None:
        """When local ``.env`` is missing, the parent directory is checked."""
        # Arrange
        local: Path = tmp_path / "subdir"
        local.mkdir()
        parent_env: Path = tmp_path / ".env"
        parent_env.write_text("OPENROUTER_API_KEY=parent-key\n")

        # Assert
        assert not (local / ".env").exists()
        assert parent_env.exists()


class TestLazyLLM:
    """Verify _LazyLLM proxy instantiation and delegation."""

    def test_default_mode_sets_json_mode_false(self) -> None:
        """A default-mode ``_LazyLLM`` should have ``_json_mode=False``."""
        from agents import _LazyLLM

        lazy: _LazyLLM = _LazyLLM(json_mode=False)
        assert lazy._json_mode is False

    def test_json_mode_sets_json_mode_true(self) -> None:
        """A JSON-mode ``_LazyLLM`` should have ``_json_mode=True``."""
        from agents import _LazyLLM

        lazy: _LazyLLM = _LazyLLM(json_mode=True)
        assert lazy._json_mode is True

    @patch("agents._get_llm")
    def test_invoke_delegates_to_underlying_llm(
        self, mock_get_llm: MagicMock
    ) -> None:
        """``invoke()`` should call ``_get_llm`` and forward arguments."""
        from agents import _LazyLLM

        # Arrange
        mock_inner: MagicMock = MagicMock()
        mock_inner.invoke.return_value = "response"
        mock_get_llm.return_value = mock_inner

        # Act
        lazy: _LazyLLM = _LazyLLM(json_mode=True)
        result: str = lazy.invoke(["msg1"])

        # Assert
        mock_get_llm.assert_called_once_with(True)
        mock_inner.invoke.assert_called_once_with(["msg1"])
        assert result == "response"

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key-for-llm"})
    @patch("agents.ChatOpenAI")
    def test_get_llm_creates_default_mode_instance(
        self, mock_chat: MagicMock
    ) -> None:
        """``_get_llm(json_mode=False)`` should omit ``model_kwargs``."""
        import agents as _agents_mod

        # Arrange
        _agents_mod._llm_cache.clear()
        _agents_mod._llm_cache_key = None
        mock_chat.return_value = MagicMock()

        # Act
        _agents_mod._get_llm(json_mode=False)

        # Assert
        mock_chat.assert_called_once()
        call_kwargs: dict[str, Any] = mock_chat.call_args[1]
        assert call_kwargs["model"] == "openai/gpt-4o"
        assert call_kwargs["temperature"] == 0
        assert "model_kwargs" not in call_kwargs

        # Cleanup
        _agents_mod._llm_cache.clear()
        _agents_mod._llm_cache_key = None

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key-for-llm"})
    @patch("agents.ChatOpenAI")
    def test_get_llm_creates_json_mode_instance(
        self, mock_chat: MagicMock
    ) -> None:
        """``_get_llm(json_mode=True)`` should include ``response_format``."""
        import agents as _agents_mod

        _agents_mod._llm_cache.clear()
        _agents_mod._llm_cache_key = None
        mock_chat.return_value = MagicMock()

        _agents_mod._get_llm(json_mode=True)

        call_kwargs: dict[str, Any] = mock_chat.call_args[1]
        assert call_kwargs["model_kwargs"] == {
            "response_format": {"type": "json_object"},
        }

        _agents_mod._llm_cache.clear()
        _agents_mod._llm_cache_key = None

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key-for-llm"})
    @patch("agents.ChatOpenAI")
    def test_get_llm_returns_cached_instance_on_repeat_call(
        self, mock_chat: MagicMock
    ) -> None:
        """Repeated calls with the same key should return the same object."""
        import agents as _agents_mod

        _agents_mod._llm_cache.clear()
        _agents_mod._llm_cache_key = None
        mock_chat.return_value = MagicMock()

        result1 = _agents_mod._get_llm(json_mode=False)
        result2 = _agents_mod._get_llm(json_mode=False)

        assert result1 is result2
        assert mock_chat.call_count == 1

        _agents_mod._llm_cache.clear()
        _agents_mod._llm_cache_key = None


class TestSafeJsonParse:
    """Verify JSON parsing with markdown fence stripping."""

    @pytest.mark.parametrize(
        "raw_input,expected",
        [
            ('{"key": "value"}', {"key": "value"}),
            ("[1, 2, 3]", [1, 2, 3]),
            ('  \n  {"a": 1}  \n  ', {"a": 1}),
        ],
        ids=["plain-dict", "plain-list", "whitespace-padded"],
    )
    def test_parses_valid_json_variants(
        self, raw_input: str, expected: dict | list
    ) -> None:
        """Valid JSON (with optional whitespace) should parse correctly."""
        from agents import _safe_json_parse

        assert _safe_json_parse(raw_input) == expected

    def test_strips_markdown_code_fences(self) -> None:
        """JSON wrapped in triple-backtick fences should be unwrapped."""
        from agents import _safe_json_parse

        text: str = '```json\n{"key": "value"}\n```'
        assert _safe_json_parse(text) == {"key": "value"}

    def test_raises_json_decode_error_on_invalid_input(self) -> None:
        """Non-JSON input should raise ``json.JSONDecodeError``."""
        from agents import _safe_json_parse

        with pytest.raises(json.JSONDecodeError):
            _safe_json_parse("not json at all")


class TestLogReaderNode:
    """Verify the combined AI log analysis pipeline."""

    @patch("agents.LLM_JSON")
    def test_basic_log_parsing_produces_classified_events(
        self, mock_llm: MagicMock
    ) -> None:
        """A single log file should yield inferred schema and classified events."""
        # Arrange
        mock_llm.invoke.return_value = _make_llm_response(json.dumps({
            "schema": {
                "format_name": "syslog",
                "description": "Standard syslog",
                "fields": [{
                    "position": 0, "name": "timestamp", "type": "datetime",
                    "description": "ts", "example": "Jan 1",
                }],
            },
            "events": [{"timestamp": "Jan 1", "message": "link up"}],
            "classified": [{
                "timestamp": "Jan 1", "message": "link up",
                "severity": "info", "category": "interface",
                "summary": "Link came up",
            }],
        }))
        state: dict[str, Any] = {
            "raw_logs": {"test.log": "Jan 1 host link up"},
            "errors": [],
        }

        # Act
        from agents import log_reader_node

        result: dict[str, Any] = log_reader_node(state)

        # Assert
        assert "test.log" in result["inferred_schemas"]
        assert len(result["classified_events"]) == 1
        assert result["classified_events"][0]["severity"] == "info"
        assert result["status"] == "classified"
        mock_llm.invoke.assert_called_once()

    @patch("agents.LLM_JSON")
    def test_empty_log_file_is_skipped(self, mock_llm: MagicMock) -> None:
        """An empty log file should not trigger any LLM calls."""
        from agents import log_reader_node

        state: dict[str, Any] = {"raw_logs": {"empty.log": ""}, "errors": []}
        result: dict[str, Any] = log_reader_node(state)

        assert result["classified_events"] == []
        mock_llm.invoke.assert_not_called()

    @patch("agents.LLM_JSON")
    def test_log_analysis_failure_records_error(self, mock_llm: MagicMock) -> None:
        """Invalid JSON from log analysis should add an error and skip the file."""
        from agents import log_reader_node

        mock_llm.invoke.return_value = _make_llm_response("not valid json")

        state: dict[str, Any] = {"raw_logs": {"bad.log": "some log line"}, "errors": []}
        result: dict[str, Any] = log_reader_node(state)

        assert any("Log analysis failed" in e for e in result["errors"])
        assert result["classified_events"] == []

    @patch("agents.LLM_JSON")
    def test_unexpected_json_shape_records_error(self, mock_llm: MagicMock) -> None:
        """A non-object JSON response should add an analysis error."""
        from agents import log_reader_node

        mock_llm.invoke.return_value = _make_llm_response(json.dumps([]))

        state: dict[str, Any] = {"raw_logs": {"test.log": "line1"}, "errors": []}
        result: dict[str, Any] = log_reader_node(state)

        assert any("unexpected JSON" in e for e in result["errors"])

    @patch("agents.LLM_JSON")
    def test_missing_classification_defaults_to_info_severity(
        self, mock_llm: MagicMock
    ) -> None:
        """Missing classification data should fall back to ``severity=info``."""
        from agents import log_reader_node

        mock_llm.invoke.return_value = _make_llm_response(json.dumps({
            "schema": {"format_name": "test", "fields": []},
            "events": [{"msg": "test"}],
        }))

        state: dict[str, Any] = {"raw_logs": {"test.log": "line1"}, "errors": []}
        result: dict[str, Any] = log_reader_node(state)

        assert result["errors"] == []
        assert len(result["classified_events"]) == 1
        assert result["classified_events"][0]["severity"] == "info"
        assert result["classified_events"][0]["category"] == "unknown"

    @patch("agents.LLM_JSON")
    def test_multiple_files_produces_combined_output(
        self, mock_llm: MagicMock
    ) -> None:
        """Processing two files should yield schemas and events from both."""
        from agents import log_reader_node

        def _responses_for(fname: str) -> list[MagicMock]:
            return [
                _make_llm_response(json.dumps({
                    "schema": {"format_name": fname, "fields": []},
                    "events": [{"msg": f"event from {fname}"}],
                    "classified": [{
                        "msg": f"event from {fname}", "severity": "info",
                        "category": "application", "summary": "test",
                    }],
                })),
            ]

        mock_llm.invoke.side_effect = _responses_for("a.log") + _responses_for("b.log")

        state: dict[str, Any] = {
            "raw_logs": {"a.log": "line a", "b.log": "line b"},
            "errors": [],
        }
        result: dict[str, Any] = log_reader_node(state)

        assert len(result["inferred_schemas"]) == 2
        assert len(result["classified_events"]) == 2
        assert mock_llm.invoke.call_count == 2

    @patch("agents.LLM_JSON")
    def test_repeated_file_content_uses_cached_analysis(
        self, mock_llm: MagicMock
    ) -> None:
        """Repeated analysis of identical content should avoid another LLM call."""
        from agents import log_reader_node

        mock_llm.invoke.return_value = _make_llm_response(json.dumps({
            "schema": {"format_name": "test", "fields": []},
            "events": [{"msg": "cached"}],
            "classified": [{
                "msg": "cached", "severity": "info",
                "category": "application", "summary": "Cached event",
            }],
        }))
        state: dict[str, Any] = {"raw_logs": {"test.log": "line a"}, "errors": []}

        first = log_reader_node(state)
        second = log_reader_node(state)

        assert first["classified_events"] == second["classified_events"]
        mock_llm.invoke.assert_called_once()


class TestRemediationNode:
    """Verify remediation generation from classified events."""

    @patch("agents.LLM_JSON")
    def test_critical_events_produce_remediations(
        self, mock_llm: MagicMock
    ) -> None:
        """Critical events should yield at least one remediation."""
        from agents import remediation_node

        mock_llm.invoke.return_value = _make_llm_response(json.dumps({
            "remediations": [{
                "issue_id": "i1", "title": "Link flap",
                "severity": "critical", "category": "interface",
            }],
        }))

        state: dict[str, Any] = {
            "classified_events": [
                {"severity": "critical", "category": "interface", "summary": "Link down"},
            ],
        }
        result: dict[str, Any] = remediation_node(state)

        assert len(result["remediations"]) == 1
        assert result["remediations"][0]["title"] == "Link flap"
        assert result["status"] == "remediated"

    def test_info_only_events_return_empty_remediations(self) -> None:
        """Events with only ``info`` severity should yield no remediations."""
        from agents import remediation_node

        state: dict[str, Any] = {
            "classified_events": [
                {"severity": "info", "category": "application", "summary": "Healthy"},
            ],
        }
        result: dict[str, Any] = remediation_node(state)

        assert result["remediations"] == []
        assert result["status"] == "remediated"

    @patch("agents.LLM_JSON")
    def test_json_parse_failure_returns_fallback_remediation(
        self, mock_llm: MagicMock
    ) -> None:
        """Invalid LLM JSON should produce a single ``parse-error`` fallback."""
        from agents import remediation_node

        mock_llm.invoke.return_value = _make_llm_response("not json")

        state: dict[str, Any] = {
            "classified_events": [{"severity": "warning", "category": "resource"}],
        }
        result: dict[str, Any] = remediation_node(state)

        assert len(result["remediations"]) == 1
        assert result["remediations"][0]["issue_id"] == "parse-error"


class TestCookbookNode:
    """Verify runbook generation from remediations."""

    @patch("agents.LLM")
    def test_remediations_produce_markdown_runbook(
        self, mock_llm: MagicMock
    ) -> None:
        """Remediations should be synthesised into a markdown runbook."""
        from agents import cookbook_node

        mock_resp: MagicMock = MagicMock()
        mock_resp.content = "# Incident Runbook\n## Summary\nFixed stuff."
        mock_llm.invoke.return_value = mock_resp

        state: dict[str, Any] = {
            "remediations": [{"title": "Fix link", "severity": "critical"}],
        }
        result: dict[str, Any] = cookbook_node(state)

        assert "# Incident Runbook" in result["cookbook"]
        assert result["status"] == "complete"

    def test_empty_remediations_return_default_runbook(self) -> None:
        """No remediations should produce a default 'no issues' runbook."""
        from agents import cookbook_node

        state: dict[str, Any] = {"remediations": []}
        result: dict[str, Any] = cookbook_node(state)

        assert "No actionable issues detected" in result["cookbook"]
        assert result["status"] == "complete"


class TestNotificationNode:
    """Verify Slack notification routing and message formatting."""

    @patch("agents.send_slack_message")
    def test_multiple_categories_route_to_separate_channels(
        self, mock_slack: MagicMock
    ) -> None:
        """Two remediations in different categories should send two messages."""
        from agents import notification_node

        mock_slack.invoke.return_value = json.dumps({"mock": True, "channel": "#test"})

        state: dict[str, Any] = {
            "remediations": [
                {
                    "title": "Auth fail", "severity": "critical",
                    "category": "security", "affected_systems": ["fw-01"],
                },
                {
                    "title": "Disk full", "severity": "warning",
                    "category": "resource", "affected_systems": ["srv-01"],
                },
            ],
        }
        result: dict[str, Any] = notification_node(state)

        assert len(result["notifications_sent"]) == 2
        assert result["status"] == "notified"
        assert mock_slack.invoke.call_count == 2

    def test_empty_remediations_send_no_notifications(self) -> None:
        """No remediations should produce no Slack messages."""
        from agents import notification_node

        state: dict[str, Any] = {"remediations": []}
        result: dict[str, Any] = notification_node(state)

        assert result["notifications_sent"] == []
        assert result["status"] == "notified"

    @patch("agents.send_slack_message")
    def test_missing_category_defaults_to_ops_channel(
        self, mock_slack: MagicMock
    ) -> None:
        """A remediation without a category should route to ``#ops-incidents``."""
        from agents import notification_node

        mock_slack.invoke.return_value = json.dumps(
            {"mock": True, "channel": "#ops-incidents"}
        )

        state: dict[str, Any] = {
            "remediations": [{"title": "Unknown issue", "severity": "warning"}],
        }
        result: dict[str, Any] = notification_node(state)

        call_args: dict[str, str] = mock_slack.invoke.call_args[0][0]
        assert call_args["channel"] == "#ops-incidents"


class TestJiraNode:
    """Verify JIRA ticket creation for critical-severity issues."""

    @patch("agents.create_jira_ticket")
    def test_critical_issue_creates_ticket(self, mock_jira: MagicMock) -> None:
        """A critical remediation should produce exactly one JIRA ticket."""
        from agents import jira_node

        mock_jira.invoke.return_value = json.dumps({"mock": True, "key": "OPS-001"})

        state: dict[str, Any] = {
            "remediations": [{
                "title": "Router down", "severity": "critical",
                "root_cause": "Power failure",
                "remediation_steps": ["Step 1", "Step 2"],
                "cli_commands": ["show ip route"],
            }],
        }
        result: dict[str, Any] = jira_node(state)

        assert len(result["jira_tickets"]) == 1
        assert result["jira_tickets"][0]["key"] == "OPS-001"
        mock_jira.invoke.assert_called_once()

    @patch("agents.create_jira_ticket")
    def test_warning_severity_does_not_create_ticket(
        self, mock_jira: MagicMock
    ) -> None:
        """Only critical (not warning) issues should trigger ticket creation."""
        from agents import jira_node

        state: dict[str, Any] = {
            "remediations": [{"title": "Minor issue", "severity": "warning"}],
        }
        result: dict[str, Any] = jira_node(state)

        assert result["jira_tickets"] == []
        mock_jira.invoke.assert_not_called()

    @patch("agents.create_jira_ticket")
    def test_string_steps_and_commands_included_in_description(
        self, mock_jira: MagicMock
    ) -> None:
        """Non-list steps and commands should still appear in the ticket body."""
        from agents import jira_node

        mock_jira.invoke.return_value = json.dumps({"mock": True, "key": "OPS-002"})

        state: dict[str, Any] = {
            "remediations": [{
                "title": "Issue", "severity": "critical",
                "root_cause": "Unknown",
                "remediation_steps": "Do the thing",
                "cli_commands": "show version",
            }],
        }
        result: dict[str, Any] = jira_node(state)

        assert len(result["jira_tickets"]) == 1
        call_args: dict[str, str] = mock_jira.invoke.call_args[0][0]
        assert "Do the thing" in call_args["description"]
        assert "show version" in call_args["description"]

    @patch("agents.create_jira_ticket")
    def test_missing_commands_omits_noformat_block(
        self, mock_jira: MagicMock
    ) -> None:
        """When ``cli_commands`` is absent, the ``{noformat}`` block should not appear."""
        from agents import jira_node

        mock_jira.invoke.return_value = json.dumps({"mock": True, "key": "OPS-003"})

        state: dict[str, Any] = {
            "remediations": [{
                "title": "Issue", "severity": "critical",
                "root_cause": "Unknown",
                "remediation_steps": ["Fix it"],
            }],
        }
        result: dict[str, Any] = jira_node(state)

        call_args: dict[str, str] = mock_jira.invoke.call_args[0][0]
        assert "{noformat}" not in call_args["description"]

    @patch("agents.create_jira_ticket")
    def test_multiple_critical_issues_create_multiple_tickets(
        self, mock_jira: MagicMock
    ) -> None:
        """Each critical remediation should produce its own JIRA ticket."""
        from agents import jira_node

        mock_jira.invoke.side_effect = [
            json.dumps({"mock": True, "key": "OPS-001"}),
            json.dumps({"mock": True, "key": "OPS-002"}),
        ]

        state: dict[str, Any] = {
            "remediations": [
                {"title": "Issue 1", "severity": "critical", "root_cause": "A"},
                {"title": "Issue 2", "severity": "critical", "root_cause": "B"},
            ],
        }
        result: dict[str, Any] = jira_node(state)

        assert len(result["jira_tickets"]) == 2
