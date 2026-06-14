"""LangGraph agent node functions for the incident analysis pipeline.

Each public function in this module is a LangGraph node that receives
an ``IncidentState`` dict and returns a partial-state update dict.
LLM calls are lazily initialised via ``_LazyLLM`` so the API key can
be changed at runtime (e.g. by the Streamlit UI) without restarting
the process.

Pipeline stages:
    1. ``log_reader_node`` — infer schema → parse events → classify
    2. ``remediation_node`` — generate fix recommendations
    3. ``cookbook_node`` — synthesise a markdown runbook
    4. ``notification_node`` — route alerts to Slack channels
    5. ``jira_node`` — create JIRA tickets for critical issues
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from state import IncidentState
from tools import create_jira_ticket, route_to_channel, send_slack_message

logger: logging.Logger = logging.getLogger(__name__)

_project_root: Path = Path(__file__).parent.parent
env_path: Path = _project_root / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=str(env_path))
else:
    parent_env: Path = _project_root.parent / ".env"
    if parent_env.exists():
        load_dotenv(dotenv_path=str(parent_env))

_llm_cache: dict[str, ChatOpenAI] = {}
_llm_cache_key: str | None = None

SCHEMA_SAMPLE_LINES: int = 15
LOG_CHUNK_SIZE: int = 100


def _get_llm(json_mode: bool = False) -> ChatOpenAI:
    """Return a cached ``ChatOpenAI`` instance, creating one if needed.

    The cache is invalidated whenever the ``OPENROUTER_API_KEY``
    environment variable changes, allowing users to paste a new key
    mid-session without restarting.

    Args:
        json_mode: When ``True``, the LLM is configured with
            ``response_format={"type": "json_object"}`` for reliable
            structured output.

    Returns:
        A ``ChatOpenAI`` instance configured for OpenRouter.
    """
    global _llm_cache_key
    current_api_key: str = os.getenv("OPENROUTER_API_KEY", "")

    if current_api_key != _llm_cache_key:
        _llm_cache.clear()
        _llm_cache_key = current_api_key

    key: str = "json" if json_mode else "default"
    if key not in _llm_cache:
        kwargs: dict[str, Any] = {
            "model": "openai/gpt-4o",
            "openai_api_key": current_api_key,
            "openai_api_base": "https://openrouter.ai/api/v1",
            "temperature": 0,
        }
        if json_mode:
            kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}
        _llm_cache[key] = ChatOpenAI(**kwargs)
        logger.info("Created %s-mode LLM instance", key)

    return _llm_cache[key]


class _LazyLLM:
    """Proxy that defers ``ChatOpenAI`` construction until first call.

    This avoids creating an LLM at import time (which would fail if
    no API key is set yet) and automatically picks up key changes.

    Args:
        json_mode: Forwarded to ``_get_llm`` on each invocation.
    """

    def __init__(self, json_mode: bool = False) -> None:
        self._json_mode: bool = json_mode

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to the underlying ``ChatOpenAI.invoke``.

        Args:
            *args: Positional arguments forwarded to ``ChatOpenAI.invoke``.
            **kwargs: Keyword arguments forwarded to ``ChatOpenAI.invoke``.

        Returns:
            The LLM response object.
        """
        return _get_llm(self._json_mode).invoke(*args, **kwargs)


LLM: _LazyLLM = _LazyLLM(json_mode=False)
LLM_JSON: _LazyLLM = _LazyLLM(json_mode=True)


def _safe_json_parse(text: str) -> dict[str, Any] | list[Any]:
    """Parse a JSON string, stripping markdown code fences if present.

    LLMs sometimes wrap JSON output in triple-backtick code blocks.
    This helper removes those fences before parsing.

    Args:
        text: Raw string that may contain a JSON object or array,
            optionally wrapped in markdown code fences.

    Returns:
        The parsed Python dict or list.

    Raises:
        json.JSONDecodeError: If the content is not valid JSON after
            fence removal.
    """
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
    return json.loads(text)


def log_reader_node(state: IncidentState) -> dict[str, Any]:
    """AI-driven log parser: infer schema, parse events, classify severity.

    For each file in ``state["raw_logs"]``:
        1. Send the first ``SCHEMA_SAMPLE_LINES`` lines to the LLM to
           infer the log format and field definitions.
        2. Parse all lines into structured events using the inferred
           schema, chunking into batches of ``LOG_CHUNK_SIZE``.
        3. Classify each event with severity, category, and summary.

    Args:
        state: Current pipeline state containing ``raw_logs`` and
            ``errors``.

    Returns:
        Partial state update with ``inferred_schemas``,
        ``parsed_events``, ``classified_events``, ``status``, and
        ``errors``.
    """
    inferred_schemas: dict[str, Any] = {}
    all_parsed: list[dict[str, Any]] = []
    all_classified: list[dict[str, Any]] = []
    errors: list[str] = list(state.get("errors", []))

    for filename, content in state["raw_logs"].items():
        lines: list[str] = content.strip().splitlines()
        if not lines:
            continue

        sample: str = "\n".join(lines[:SCHEMA_SAMPLE_LINES])
        logger.info("Inferring schema for %s (%d lines)", filename, len(lines))

        schema_resp = LLM_JSON.invoke([
            SystemMessage(content=(
                "You are a network/infrastructure log format analyst. "
                "Given sample log lines, identify the log format type and every field. "
                'Return JSON: {"format_name": "...", "description": "...", '
                '"fields": [{"position": 0, "name": "...", "type": "...", '
                '"description": "...", "example": "..."}]}'
            )),
            HumanMessage(content=f"Filename: {filename}\n\nSample lines:\n{sample}"),
        ])

        try:
            schema: dict[str, Any] | list[Any] = _safe_json_parse(schema_resp.content)
        except json.JSONDecodeError:
            logger.warning("Schema inference failed for %s", filename)
            errors.append(f"Schema inference failed for {filename}")
            continue

        inferred_schemas[filename] = schema

        file_events: list[dict[str, Any]] = []
        for i in range(0, len(lines), LOG_CHUNK_SIZE):
            chunk: str = "\n".join(lines[i : i + LOG_CHUNK_SIZE])
            parse_resp = LLM_JSON.invoke([
                SystemMessage(content=(
                    "You are a log parser. Using the schema below, parse each log line "
                    "into a structured JSON event. For multi-line entries (stack traces, "
                    "continuation lines), combine them into the parent event's message field. "
                    'Return JSON: {"events": [{...}]}\n\n'
                    f"Schema: {json.dumps(schema)}"
                )),
                HumanMessage(content=f"Log lines:\n{chunk}"),
            ])
            try:
                parsed: dict[str, Any] | list[Any] = _safe_json_parse(parse_resp.content)
                events: list[dict[str, Any]] = (
                    parsed.get("events", parsed)
                    if isinstance(parsed, dict)
                    else parsed
                )
                for evt in events:
                    evt["source_file"] = filename
                file_events.extend(events)
            except json.JSONDecodeError:
                logger.warning("Parse failed for chunk %d-%d in %s", i, i + LOG_CHUNK_SIZE, filename)
                errors.append(f"Parse failed for chunk {i}-{i + LOG_CHUNK_SIZE} in {filename}")

        all_parsed.extend(file_events)

        classify_resp = LLM_JSON.invoke([
            SystemMessage(content=(
                "You are a DevOps incident classifier. For each event, assign:\n"
                "- severity: critical, warning, or info\n"
                "- category: one of [interface, auth, resource, policy, routing, "
                "security, hardware, application, database, network]\n"
                "- summary: one-line human description of what happened\n"
                'Return JSON: {"classified": [{original event fields + severity, '
                "category, summary}]}"
            )),
            HumanMessage(content=f"Events to classify:\n{json.dumps(file_events)}"),
        ])
        try:
            classified: dict[str, Any] | list[Any] = _safe_json_parse(classify_resp.content)
            items: list[dict[str, Any]] = (
                classified.get("classified", classified)
                if isinstance(classified, dict)
                else classified
            )
            all_classified.extend(items)
        except json.JSONDecodeError:
            logger.warning("Classification failed for %s", filename)
            errors.append(f"Classification failed for {filename}")
            for evt in file_events:
                evt.update({
                    "severity": "info",
                    "category": "unknown",
                    "summary": "Classification failed",
                })
                all_classified.append(evt)

    logger.info(
        "Log reader complete: %d schemas, %d events, %d classified",
        len(inferred_schemas),
        len(all_parsed),
        len(all_classified),
    )
    return {
        "inferred_schemas": inferred_schemas,
        "parsed_events": all_parsed,
        "classified_events": all_classified,
        "status": "classified",
        "errors": errors,
    }


def remediation_node(state: IncidentState) -> dict[str, Any]:
    """Generate remediation recommendations for actionable incidents.

    Filters classified events to those with severity ``"critical"`` or
    ``"warning"``, then asks the LLM to group related events and
    produce fix recommendations with root-cause analysis, CLI
    commands, and verification steps.

    Args:
        state: Current pipeline state containing ``classified_events``.

    Returns:
        Partial state update with ``remediations`` and ``status``.
    """
    events: list[dict[str, Any]] = state.get("classified_events", [])
    actionable: list[dict[str, Any]] = [
        e for e in events if e.get("severity") in ("critical", "warning")
    ]

    if not actionable:
        logger.info("No actionable events — skipping remediation")
        return {"remediations": [], "status": "remediated"}

    logger.info("Generating remediations for %d actionable events", len(actionable))
    resp = LLM_JSON.invoke([
        SystemMessage(content=(
            "You are a senior DevOps/SRE engineer. Given classified incident events, "
            "produce remediation recommendations. Group related events into distinct issues. "
            "For each issue provide:\n"
            "- issue_id: short identifier\n"
            "- title: brief issue title\n"
            "- severity: critical or warning\n"
            "- affected_systems: list of hostnames/services\n"
            "- root_cause: likely root cause analysis\n"
            "- remediation_steps: numbered list of fix steps\n"
            "- cli_commands: exact vendor-specific CLI commands to execute\n"
            "- verification: how to verify the fix worked\n"
            "- risk_level: low/medium/high risk of the remediation itself\n"
            "- category: one of [security, auth, policy, interface, routing, network, "
            "hardware, resource, application, database] — the primary category of this issue\n"
            'Return JSON: {"remediations": [...]}'
        )),
        HumanMessage(content=f"Actionable events:\n{json.dumps(actionable)}"),
    ])

    try:
        result: dict[str, Any] = _safe_json_parse(resp.content)
        remediations: list[dict[str, Any]] = result.get("remediations", [])
    except json.JSONDecodeError:
        logger.error("Remediation JSON parse failed — returning fallback")
        remediations = [{
            "issue_id": "parse-error",
            "title": "Remediation parse failed",
            "severity": "warning",
            "root_cause": "LLM output was not valid JSON",
        }]

    return {"remediations": remediations, "status": "remediated"}


def cookbook_node(state: IncidentState) -> dict[str, Any]:
    """Synthesise remediations into an actionable markdown runbook.

    Produces a structured document with an executive summary, priority
    matrix, numbered checklists with CLI commands, escalation criteria,
    and post-incident review items.

    Args:
        state: Current pipeline state containing ``remediations``.

    Returns:
        Partial state update with ``cookbook`` (markdown string) and
        ``status``.
    """
    remediations: list[dict[str, Any]] = state.get("remediations", [])

    if not remediations:
        logger.info("No remediations — returning default runbook")
        return {
            "cookbook": "# Incident Runbook\n\nNo actionable issues detected.",
            "status": "complete",
        }

    logger.info("Generating runbook from %d remediations", len(remediations))
    resp = LLM.invoke([
        SystemMessage(content=(
            "You are a technical writer for DevOps teams. Given remediation data, "
            "create a single, comprehensive incident runbook in Markdown format.\n\n"
            "Structure:\n"
            "# Incident Runbook\n"
            "## Executive Summary (2-3 sentences)\n"
            "## Priority Matrix (table: issue, severity, affected systems)\n"
            "## Remediation Checklists (one numbered section per issue with:\n"
            "   - [ ] checkbox steps\n"
            "   - ```code blocks``` for CLI commands\n"
            "   - Verification steps after each fix)\n"
            "## Escalation Criteria\n"
            "## Post-Incident Review Items\n\n"
            "Be specific, actionable, and concise."
        )),
        HumanMessage(content=f"Remediation data:\n{json.dumps(remediations)}"),
    ])

    return {"cookbook": resp.content, "status": "complete"}


def notification_node(state: IncidentState) -> dict[str, Any]:
    """Route incident notifications to the appropriate Slack channels.

    Groups remediations by their target channel (determined by
    ``route_to_channel``), formats a summary message for each channel,
    and invokes ``send_slack_message``.

    Args:
        state: Current pipeline state containing ``remediations``.

    Returns:
        Partial state update with ``notifications_sent`` and ``status``.
    """
    remediations: list[dict[str, Any]] = state.get("remediations", [])
    if not remediations:
        return {"notifications_sent": [], "status": "notified"}

    channel_groups: dict[str, list[dict[str, Any]]] = {}
    for r in remediations:
        category: str = r.get("category", "application")
        channel: str = route_to_channel(category)
        channel_groups.setdefault(channel, []).append(r)

    all_sent: list[dict[str, Any]] = []
    for channel, items in channel_groups.items():
        lines: list[str] = [f"*Incident Analysis Alert — {channel}*\n"]
        for r in items:
            title: str = r.get("title", "Unknown issue")
            sev: str = r.get("severity", "unknown")
            systems: str = ", ".join(r.get("affected_systems", ["unknown"]))
            lines.append(f"* *[{sev.upper()}]* {title} — {systems}")

        lines.append(
            f"\n_{len(items)} issue(s) routed to this channel. "
            "See runbook for full details._"
        )
        message: str = "\n".join(lines)

        result: str | dict[str, Any] = send_slack_message.invoke(
            {"channel": channel, "text": message}
        )
        sent: dict[str, Any] = json.loads(result) if isinstance(result, str) else result
        all_sent.append(sent)

    logger.info("Sent %d Slack notifications", len(all_sent))
    return {"notifications_sent": all_sent, "status": "notified"}


def jira_node(state: IncidentState) -> dict[str, Any]:
    """Create JIRA tickets for critical-severity issues.

    Iterates over remediations with ``severity == "critical"`` and
    creates a JIRA ticket for each, including root cause, remediation
    steps, and CLI commands in the ticket description.

    Args:
        state: Current pipeline state containing ``remediations``.

    Returns:
        Partial state update with ``jira_tickets`` and ``status``.
    """
    remediations: list[dict[str, Any]] = state.get("remediations", [])
    critical: list[dict[str, Any]] = [
        r for r in remediations if r.get("severity") == "critical"
    ]
    tickets: list[dict[str, Any]] = []

    for r in critical:
        title: str = r.get("title", "Critical incident")
        steps: list[str] | str = r.get("remediation_steps", [])
        commands: list[str] | str = r.get("cli_commands", [])

        description: str = f"Root Cause: {r.get('root_cause', 'Unknown')}\n\n"
        description += "Remediation Steps:\n"
        if isinstance(steps, list):
            for i, step in enumerate(steps, 1):
                description += f"{i}. {step}\n"
        else:
            description += f"{steps}\n"

        if commands:
            description += "\nCLI Commands:\n{noformat}\n"
            if isinstance(commands, list):
                description += "\n".join(commands)
            else:
                description += str(commands)
            description += "\n{noformat}"

        result: str | dict[str, Any] = create_jira_ticket.invoke({
            "summary": f"[INCIDENT] {title}",
            "description": description,
            "priority": "critical",
        })

        ticket: dict[str, Any] = json.loads(result) if isinstance(result, str) else result
        tickets.append(ticket)

    logger.info("Created %d JIRA tickets", len(tickets))
    return {"jira_tickets": tickets, "status": "ticketed"}
