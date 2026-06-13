"""Shared state schema for the incident analysis pipeline.

Defines the ``IncidentState`` TypedDict that flows through every
LangGraph node, carrying raw logs, inferred schemas, parsed events,
classified events, remediations, runbook text, notification results,
JIRA tickets, pipeline status, and accumulated errors.
"""

from __future__ import annotations

from typing import Any, TypedDict


class IncidentState(TypedDict):
    """Shared state passed between all LangGraph agent nodes.

    Attributes:
        raw_logs: Mapping of filename to full log-file text content.
        inferred_schemas: Mapping of filename to AI-inferred field schemas.
        parsed_events: Flat list of structured events extracted from all logs.
        classified_events: Events enriched with severity, category, and summary.
        remediations: Recommended fixes grouped by distinct issue.
        cookbook: Markdown runbook synthesized from remediations.
        notifications_sent: Slack notification results (mock or live).
        jira_tickets: JIRA ticket creation results (mock or live).
        status: Current pipeline stage identifier.
        errors: Accumulated error messages from all pipeline stages.
    """

    raw_logs: dict[str, str]
    inferred_schemas: dict[str, list[Any]]
    parsed_events: list[dict[str, Any]]
    classified_events: list[dict[str, Any]]
    remediations: list[dict[str, Any]]
    cookbook: str
    notifications_sent: list[dict[str, Any]]
    jira_tickets: list[dict[str, Any]]
    status: str
    errors: list[str]
