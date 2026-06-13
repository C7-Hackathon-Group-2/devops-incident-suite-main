import os
import json
from datetime import datetime

import requests
from langchain_core.tools import tool


SLACK_MOCK = os.getenv("SLACK_MOCK", "true").lower() == "true"
JIRA_MOCK = os.getenv("JIRA_MOCK", "true").lower() == "true"

CHANNEL_ROUTING = {
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

DEFAULT_CHANNEL = "#ops-incidents"


def route_to_channel(category: str) -> str:
    """Map an incident category to the appropriate Slack channel."""
    return CHANNEL_ROUTING.get(category.lower(), DEFAULT_CHANNEL)


@tool
def send_slack_message(channel: str, text: str) -> str:
    """Send a message to a Slack channel via webhook."""
    if SLACK_MOCK:
        return json.dumps({
            "mock": True,
            "channel": channel,
            "text": text,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "would_send",
        })

    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return json.dumps({"error": "SLACK_WEBHOOK_URL not configured"})

    resp = requests.post(
        webhook_url,
        json={"channel": channel, "text": text},
        timeout=10,
    )
    return json.dumps({
        "mock": False,
        "channel": channel,
        "status_code": resp.status_code,
        "response": resp.text,
        "timestamp": datetime.utcnow().isoformat(),
    })


@tool
def create_jira_ticket(summary: str, description: str, priority: str) -> str:
    """Create a JIRA ticket for a critical incident."""
    if JIRA_MOCK:
        ticket_key = f"OPS-{datetime.utcnow().strftime('%H%M%S')}"
        return json.dumps({
            "mock": True,
            "key": ticket_key,
            "summary": summary,
            "priority": priority,
            "status": "would_create",
            "timestamp": datetime.utcnow().isoformat(),
        })

    jira_url = os.getenv("JIRA_URL", "").rstrip("/")
    jira_token = os.getenv("JIRA_API_TOKEN")
    jira_email = os.getenv("JIRA_EMAIL")
    jira_project = os.getenv("JIRA_PROJECT_KEY", "OPS")

    if not all([jira_url, jira_token, jira_email]):
        return json.dumps({"error": "JIRA credentials not configured"})

    priority_map = {"critical": "Highest", "high": "High", "warning": "Medium", "info": "Low"}

    payload = {
        "fields": {
            "project": {"key": jira_project},
            "summary": summary,
            "description": description,
            "issuetype": {"name": "Bug"},
            "priority": {"name": priority_map.get(priority, "Medium")},
        }
    }

    resp = requests.post(
        f"{jira_url}/rest/api/2/issue",
        json=payload,
        auth=(jira_email, jira_token),
        headers={"Content-Type": "application/json"},
        timeout=15,
    )
    result = resp.json()
    return json.dumps({
        "mock": False,
        "key": result.get("key", "UNKNOWN"),
        "status_code": resp.status_code,
        "timestamp": datetime.utcnow().isoformat(),
    })
