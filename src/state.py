from typing import TypedDict


class IncidentState(TypedDict):
    raw_logs: dict[str, str]
    inferred_schemas: dict[str, list]
    parsed_events: list[dict]
    classified_events: list[dict]
    remediations: list[dict]
    cookbook: str
    notifications_sent: list[dict]
    jira_tickets: list[dict]
    status: str
    errors: list[str]
