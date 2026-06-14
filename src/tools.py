"""Integration tools for Slack and JIRA with mock/live mode switching.

Provides ``@tool``-decorated functions consumed by LangChain agents,
plus a channel-routing helper that maps incident categories to the
appropriate Slack channel.  Each tool checks its ``*_MOCK`` flag at
call time so the same code path works for both demo and production use.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

import requests
from langchain_core.tools import tool

logger: logging.Logger = logging.getLogger(__name__)

SLACK_MOCK: bool = os.getenv("SLACK_MOCK", "true").lower() == "true"
JIRA_MOCK: bool = os.getenv("JIRA_MOCK", "true").lower() == "true"

CHANNEL_ROUTING: dict[str, str] = {
    "security": "#secops-incidents",
    "auth": "#secops-incidents",
    "policy": "#secops-incidents",
    "interface": "#network-incidents",
    "routing": "#network-incidents",
    "network": "#network-incidents",
    "hardware": "#network-incidents",
    "resource": "#ops-incidents",
    "application": "#ops-incidents",
    "database": "#ops-incidents",
}

DEFAULT_CHANNEL: str = "#ops-incidents"


def route_to_channel(category: str) -> str:
    """Map an incident category to the appropriate Slack channel.

    Args:
        category: Incident category string (case-insensitive), e.g.
            ``"security"``, ``"interface"``, ``"resource"``.

    Returns:
        The Slack channel name for the given category, or
        ``DEFAULT_CHANNEL`` if the category is unrecognised.
    """
    return CHANNEL_ROUTING.get(category.lower(), DEFAULT_CHANNEL)


@tool
def send_slack_message(channel: str, text: str) -> str:
    """Send a message to a Slack channel via webhook.

    In mock mode the message is not actually sent; instead a JSON
    payload is returned describing what *would* be sent.

    Args:
        channel: Target Slack channel, e.g. ``"#ops-incidents"``.
        text: Markdown-formatted message body.

    Returns:
        JSON string containing the delivery result with keys ``mock``,
        ``channel``, ``timestamp``, and either ``text``/``status``
        (mock) or ``status_code``/``response`` (live).
    """
    if SLACK_MOCK:
        logger.info("Mock Slack message to %s (%d chars)", channel, len(text))
        return json.dumps({
            "mock": True,
            "channel": channel,
            "text": text,
            "timestamp": datetime.now(UTC).isoformat(),
            "status": "would_send",
        })

    webhook_url: str | None = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        logger.error("SLACK_WEBHOOK_URL not configured")
        return json.dumps({"error": "SLACK_WEBHOOK_URL not configured"})

    resp: requests.Response = requests.post(
        webhook_url,
        json={"channel": channel, "text": text},
        timeout=10,
    )
    logger.info("Slack POST to %s returned %d", channel, resp.status_code)
    return json.dumps({
        "mock": False,
        "channel": channel,
        "status_code": resp.status_code,
        "response": resp.text,
        "timestamp": datetime.now(UTC).isoformat(),
    })


@tool
def create_jira_ticket(summary: str, description: str, priority: str) -> str:
    """Create a JIRA ticket for a critical incident.

    In mock mode the ticket is not actually created; instead a JSON
    payload is returned describing what *would* be created, including a
    deterministic ticket key derived from the current UTC time.

    Args:
        summary: One-line ticket summary prefixed with ``[INCIDENT]``.
        description: Multi-line ticket body with root cause, steps,
            and CLI commands formatted in JIRA markup.
        priority: Severity string mapped to JIRA priority —
            ``"critical"`` → Highest, ``"high"`` → High,
            ``"warning"`` → Medium, ``"info"`` → Low.

    Returns:
        JSON string containing the creation result with keys ``mock``,
        ``key``, ``timestamp``, and ``status_code`` (live only).
    """
    if JIRA_MOCK:
        ticket_key: str = f"OPS-{datetime.now(UTC).strftime('%H%M%S')}"
        logger.info("Mock JIRA ticket %s: %s", ticket_key, summary)
        return json.dumps({
            "mock": True,
            "key": ticket_key,
            "summary": summary,
            "priority": priority,
            "status": "would_create",
            "timestamp": datetime.now(UTC).isoformat(),
        })

    jira_url: str = os.getenv("JIRA_URL", "").rstrip("/")
    jira_token: str | None = os.getenv("JIRA_API_TOKEN")
    jira_email: str | None = os.getenv("JIRA_EMAIL")
    jira_project: str = os.getenv("JIRA_PROJECT_KEY", "OPS")

    print(f"jira_url: {jira_url}")
    print(f"JIRA_API_TOKEN: {jira_token}")
    print(f"jira_email: {jira_email}")
    print(f"jira_project: {jira_project}")

    if not all([jira_url, jira_token, jira_email]):
        logger.error("JIRA credentials not configured")
        return json.dumps({"error": "JIRA credentials not configured"})

    priority_map: dict[str, str] = {
        "critical": "Highest",
        "high": "High",
        "warning": "Medium",
        "info": "Low",
    }

    payload: dict[str, Any] = {
        "fields": {
            "project": {"key": jira_project},
            "summary": summary,
            "description": description,
            "issuetype": {"name": "Incident"},
            "priority": {"name": priority_map.get(priority, "Medium")},
        },
    }

    resp: requests.Response = requests.post(
        f"{jira_url}/rest/api/2/issue",
        json=payload,
        auth=(jira_email, jira_token),
        headers={"Content-Type": "application/json"},
        timeout=15,
    )
    result: dict[str, Any] = resp.json()
    logger.info("JIRA POST returned %d — key=%s", resp.status_code, result.get("key"))
    return json.dumps({
        "mock": False,
        "key": result.get("key", "UNKNOWN"),
        "status_code": resp.status_code,
        "timestamp": datetime.now(UTC).isoformat(),
    })
