import os
import json
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from state import IncidentState
from tools import send_slack_message, create_jira_ticket, route_to_channel

_project_root = Path(__file__).parent.parent
env_path = _project_root / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=str(env_path))
else:
    parent_env = _project_root.parent / ".env"
    if parent_env.exists():
        load_dotenv(dotenv_path=str(parent_env))

_llm_cache = {}
_llm_cache_key = None

def _get_llm(json_mode=False):
    global _llm_cache_key
    current_api_key = os.getenv("OPENROUTER_API_KEY", "")
    if current_api_key != _llm_cache_key:
        _llm_cache.clear()
        _llm_cache_key = current_api_key
    key = "json" if json_mode else "default"
    if key not in _llm_cache:
        kwargs = dict(
            model="openai/gpt-4o",
            openai_api_key=current_api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0,
        )
        if json_mode:
            kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}
        _llm_cache[key] = ChatOpenAI(**kwargs)
    return _llm_cache[key]


class _LazyLLM:
    def __init__(self, json_mode=False):
        self._json_mode = json_mode
    def invoke(self, *args, **kwargs):
        return _get_llm(self._json_mode).invoke(*args, **kwargs)


LLM = _LazyLLM(json_mode=False)
LLM_JSON = _LazyLLM(json_mode=True)

SCHEMA_SAMPLE_LINES = 15
LOG_CHUNK_SIZE = 100


def _safe_json_parse(text: str) -> dict | list:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
    return json.loads(text)


# ---------------------------------------------------------------------------
# Phase 2: Log Reader / Classifier Agent
# ---------------------------------------------------------------------------

def log_reader_node(state: IncidentState) -> dict:
    """AI-driven log parser: infers schema, parses events, classifies severity."""
    inferred_schemas = {}
    all_parsed = []
    all_classified = []
    errors = list(state.get("errors", []))

    for filename, content in state["raw_logs"].items():
        lines = content.strip().splitlines()
        if not lines:
            continue

        sample = "\n".join(lines[:SCHEMA_SAMPLE_LINES])

        # Step 1: Schema inference
        schema_resp = LLM_JSON.invoke([
            SystemMessage(content=(
                "You are a network/infrastructure log format analyst. "
                "Given sample log lines, identify the log format type and every field. "
                "Return JSON: {\"format_name\": \"...\", \"description\": \"...\", "
                "\"fields\": [{\"position\": 0, \"name\": \"...\", \"type\": \"...\", "
                "\"description\": \"...\", \"example\": \"...\"}]}"
            )),
            HumanMessage(content=f"Filename: {filename}\n\nSample lines:\n{sample}"),
        ])

        try:
            schema = _safe_json_parse(schema_resp.content)
        except json.JSONDecodeError:
            errors.append(f"Schema inference failed for {filename}")
            continue

        inferred_schemas[filename] = schema

        # Step 2: Parse all events in chunks
        file_events = []
        for i in range(0, len(lines), LOG_CHUNK_SIZE):
            chunk = "\n".join(lines[i:i + LOG_CHUNK_SIZE])
            parse_resp = LLM_JSON.invoke([
                SystemMessage(content=(
                    "You are a log parser. Using the schema below, parse each log line "
                    "into a structured JSON event. For multi-line entries (stack traces, "
                    "continuation lines), combine them into the parent event's message field. "
                    "Return JSON: {\"events\": [{...}]}\n\n"
                    f"Schema: {json.dumps(schema)}"
                )),
                HumanMessage(content=f"Log lines:\n{chunk}"),
            ])
            try:
                parsed = _safe_json_parse(parse_resp.content)
                events = parsed.get("events", parsed) if isinstance(parsed, dict) else parsed
                for evt in events:
                    evt["source_file"] = filename
                file_events.extend(events)
            except json.JSONDecodeError:
                errors.append(f"Parse failed for chunk {i}-{i+LOG_CHUNK_SIZE} in {filename}")

        all_parsed.extend(file_events)

        # Step 3: Classify events
        classify_resp = LLM_JSON.invoke([
            SystemMessage(content=(
                "You are a DevOps incident classifier. For each event, assign:\n"
                "- severity: critical, warning, or info\n"
                "- category: one of [interface, auth, resource, policy, routing, "
                "security, hardware, application, database, network]\n"
                "- summary: one-line human description of what happened\n"
                "Return JSON: {\"classified\": [{original event fields + severity, "
                "category, summary}]}"
            )),
            HumanMessage(content=f"Events to classify:\n{json.dumps(file_events)}"),
        ])
        try:
            classified = _safe_json_parse(classify_resp.content)
            items = classified.get("classified", classified) if isinstance(classified, dict) else classified
            all_classified.extend(items)
        except json.JSONDecodeError:
            errors.append(f"Classification failed for {filename}")
            for evt in file_events:
                evt.update({"severity": "info", "category": "unknown", "summary": "Classification failed"})
                all_classified.append(evt)

    return {
        "inferred_schemas": inferred_schemas,
        "parsed_events": all_parsed,
        "classified_events": all_classified,
        "status": "classified",
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Phase 3: Remediation Agent
# ---------------------------------------------------------------------------

def remediation_node(state: IncidentState) -> dict:
    """Map classified issues to recommended fixes with rationale and commands."""
    events = state.get("classified_events", [])
    actionable = [e for e in events if e.get("severity") in ("critical", "warning")]

    if not actionable:
        return {"remediations": [], "status": "remediated"}

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
            "Return JSON: {\"remediations\": [...]}"
        )),
        HumanMessage(content=f"Actionable events:\n{json.dumps(actionable)}"),
    ])

    try:
        result = _safe_json_parse(resp.content)
        remediations = result.get("remediations", [])
    except json.JSONDecodeError:
        remediations = [{"issue_id": "parse-error", "title": "Remediation parse failed",
                         "severity": "warning", "root_cause": "LLM output was not valid JSON"}]

    return {"remediations": remediations, "status": "remediated"}


# ---------------------------------------------------------------------------
# Phase 3: Cookbook Synthesizer Agent
# ---------------------------------------------------------------------------

def cookbook_node(state: IncidentState) -> dict:
    """Synthesize remediations into an actionable markdown runbook."""
    remediations = state.get("remediations", [])

    if not remediations:
        return {"cookbook": "# Incident Runbook\n\nNo actionable issues detected.", "status": "complete"}

    resp = LLM.invoke([
        SystemMessage(content=(
            "You are a technical writer for DevOps teams. Given remediation data, "
            "create a single, comprehensive incident runbook in Markdown format.\n\n"
            "Structure:\n"
            "# Incident Runbook — [Date]\n"
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


# ---------------------------------------------------------------------------
# Phase 4: Notification Agent (Slack)
# ---------------------------------------------------------------------------

def notification_node(state: IncidentState) -> dict:
    """Route incident notifications to the appropriate Slack channels."""
    remediations = state.get("remediations", [])
    if not remediations:
        return {"notifications_sent": [], "status": "notified"}

    # Group remediations by target channel
    channel_groups: dict[str, list] = {}
    for r in remediations:
        category = r.get("category", "application")
        channel = route_to_channel(category)
        channel_groups.setdefault(channel, []).append(r)

    all_sent = []
    for channel, items in channel_groups.items():
        lines = [f"*Incident Analysis Alert — {channel}*\n"]
        for r in items:
            title = r.get("title", "Unknown issue")
            sev = r.get("severity", "unknown")
            systems = ", ".join(r.get("affected_systems", ["unknown"]))
            lines.append(f"• *[{sev.upper()}]* {title} — {systems}")

        lines.append(f"\n_{len(items)} issue(s) routed to this channel. See runbook for full details._")
        message = "\n".join(lines)

        result = send_slack_message.invoke({"channel": channel, "text": message})
        sent = json.loads(result) if isinstance(result, str) else result
        all_sent.append(sent)

    return {"notifications_sent": all_sent, "status": "notified"}


# ---------------------------------------------------------------------------
# Phase 4: JIRA Ticket Agent
# ---------------------------------------------------------------------------

def jira_node(state: IncidentState) -> dict:
    """Create JIRA tickets for critical-severity issues."""
    remediations = state.get("remediations", [])
    critical = [r for r in remediations if r.get("severity") == "critical"]
    tickets = []

    for r in critical:
        title = r.get("title", "Critical incident")
        steps = r.get("remediation_steps", [])
        commands = r.get("cli_commands", [])

        description = f"Root Cause: {r.get('root_cause', 'Unknown')}\n\n"
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

        result = create_jira_ticket.invoke({
            "summary": f"[INCIDENT] {title}",
            "description": description,
            "priority": "critical",
        })

        ticket = json.loads(result) if isinstance(result, str) else result
        tickets.append(ticket)

    return {"jira_tickets": tickets, "status": "ticketed"}
