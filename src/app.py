from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from dotenv import load_dotenv

_project_root = Path(__file__).parent.parent
env_path = _project_root / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=str(env_path))
else:
    parent_env = _project_root.parent / ".env"
    if parent_env.exists():
        load_dotenv(dotenv_path=str(parent_env))


def _get_secret(key: str) -> str:
    """Read a secret from st.secrets or env — for API use only, never pre-fill UI."""
    try:
        return st.secrets.get(key, os.getenv(key, ""))
    except Exception:
        return os.getenv(key, "")


st.set_page_config(
    page_title="DevOps Incident Analyzer", page_icon="🔍", layout="wide"
)

DEFAULTS: dict = {
    "analysis_result": None,
    "running": False,
    "watcher_active": False,
    "watched_files": {},
    "raw_logs": {},
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

with st.sidebar:
    st.title("⚙️ Configuration")

    openrouter_key = st.text_input(
        "OpenRouter API Key",
        value="",
        type="password",
        placeholder="Paste your OpenRouter API key",
        help="Required. Your key is used only for this session and never stored.",
    )
    if openrouter_key:
        os.environ["OPENROUTER_API_KEY"] = openrouter_key
    elif not os.getenv("OPENROUTER_API_KEY"):
        st.warning("⚠️ Enter your API key to run analysis")

    st.markdown("---")
    st.markdown("### 📂 Directory Watcher")

    default_watch = str(_project_root / "watched_logs")
    watch_dir = st.text_input("Watch directory", value=default_watch)

    col_w1, col_w2 = st.columns(2)
    with col_w1:
        if st.button("📡 Scan Directory", use_container_width=True):
            from watcher import DirectoryWatcher

            watcher = DirectoryWatcher(watch_dir, callback=lambda p, e: None)
            found = watcher.scan_existing()
            if found:
                st.session_state.watched_files = found
                st.success(f"Found {len(found)} file(s)")
            else:
                st.warning("No .log/.txt files found")
    with col_w2:
        if st.button("🗂️ Create Dir", use_container_width=True):
            Path(watch_dir).mkdir(parents=True, exist_ok=True)
            st.success("Directory created")

    st.markdown("---")
    st.markdown("### 🔗 Integrations")

    slack_mock = st.toggle("Slack Mock Mode", value=True)
    os.environ["SLACK_MOCK"] = str(slack_mock).lower()

    jira_mock = st.toggle("JIRA Mock Mode", value=True)
    os.environ["JIRA_MOCK"] = str(jira_mock).lower()

    if slack_mock:
        st.info("🧪 Slack: Mock — messages simulated")
    else:
        st.success("🟢 Slack: Live")

    if jira_mock:
        st.info("🧪 JIRA: Mock — tickets simulated")
    else:
        st.success("🟢 JIRA: Live")

    st.markdown("---")
    st.markdown("### 📢 Slack Channel Routing")
    st.caption("Incidents auto-route by category:")
    st.markdown(
        """
    - `#ops-incidents` — resource, application, database
    - `#secops-incidents` — security, auth, policy
    - `#network-incidents` — interface, routing, hardware
    """
    )

    slack_webhook = st.text_input(
        "Slack Webhook URL",
        value="",
        type="password",
        disabled=slack_mock,
        placeholder="https://hooks.slack.com/services/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",
    )
    if slack_webhook:
        os.environ["SLACK_WEBHOOK_URL"] = slack_webhook

    st.markdown("---")
    st.markdown("### 🎫 JIRA")
    jira_url = st.text_input(
        "JIRA URL",
        value="",
        disabled=jira_mock,
        placeholder="https://yourcompany.atlassian.net",
    )
    if jira_url:
        os.environ["JIRA_URL"] = jira_url

    jira_email = st.text_input(
        "JIRA Email", value="", disabled=jira_mock, placeholder="you@company.com"
    )
    if jira_email:
        os.environ["JIRA_EMAIL"] = jira_email

    jira_token = st.text_input(
        "JIRA API Token",
        value="",
        type="password",
        disabled=jira_mock,
        placeholder="Paste JIRA API token",
    )
    if jira_token:
        os.environ["JIRA_API_TOKEN"] = jira_token

    jira_project = st.text_input("JIRA Project Key", value="OPS", disabled=jira_mock)
    if jira_project:
        os.environ["JIRA_PROJECT_KEY"] = jira_project


st.title("🔍 DevOps Incident Analysis Suite")
st.markdown(
    "Upload infrastructure logs or watch a directory for AI-driven "
    "incident analysis, remediation, and notification."
)

col1, col2, col3 = st.columns([3, 1, 1])

with col1:
    uploaded_files = st.file_uploader(
        "Upload log files",
        type=["log", "txt"],
        accept_multiple_files=True,
        help="Supports any log format — AI will infer field meanings automatically.",
    )

with col2:
    st.markdown("#### Samples")
    use_samples = st.button("📂 Load Samples", use_container_width=True)

with col3:
    st.markdown("#### Watched")
    use_watched = st.button(
        "📡 Use Watched",
        use_container_width=True,
        disabled=not st.session_state.watched_files,
    )

if use_samples:
    sample_dir = Path(__file__).parent / "log_samples"
    loaded = {}
    for f in sample_dir.glob("*.log"):
        loaded[f.name] = f.read_text()
    st.session_state.raw_logs = loaded

if use_watched and st.session_state.watched_files:
    st.session_state.raw_logs = dict(st.session_state.watched_files)

if uploaded_files:
    loaded = {}
    for f in uploaded_files:
        loaded[f.name] = f.read().decode("utf-8", errors="replace")
    st.session_state.raw_logs = loaded

raw_logs = st.session_state.raw_logs

if raw_logs:
    st.success(f"**{len(raw_logs)} log file(s) loaded:** {', '.join(raw_logs.keys())}")

    with st.expander("Preview log content", expanded=False):
        for name, content in raw_logs.items():
            st.markdown(f"**{name}** ({len(content.splitlines())} lines)")
            st.code(
                content[:2000] + ("..." if len(content) > 2000 else ""),
                language="text",
            )

has_api_key = bool(os.getenv("OPENROUTER_API_KEY"))
if raw_logs and not has_api_key:
    st.warning("Enter your OpenRouter API key in the sidebar to run analysis.")

if raw_logs and has_api_key and st.button(
    "🚀 Analyze Incidents", type="primary", use_container_width=True
):
    from graph import build_incident_graph

    initial_state = {
        "raw_logs": raw_logs,
        "inferred_schemas": {},
        "parsed_events": [],
        "classified_events": [],
        "remediations": [],
        "cookbook": "",
        "notifications_sent": [],
        "jira_tickets": [],
        "status": "starting",
        "errors": [],
    }

    with st.status("Analyzing incidents...", expanded=True) as status:
        try:
            st.write("🔎 Building analysis pipeline...")
            graph = build_incident_graph()

            st.write("📋 Running log reader / classifier agent...")
            st.write("⚡ AI is inferring log formats and classifying events...")

            result = graph.invoke(initial_state)
            st.session_state.analysis_result = result

            n_events = len(result.get("classified_events", []))
            n_issues = len(result.get("remediations", []))
            n_notifications = len(result.get("notifications_sent", []))
            n_tickets = len(result.get("jira_tickets", []))
            status.update(
                label=(
                    f"Complete — {n_events} events, {n_issues} issues, "
                    f"{n_notifications} notifications, {n_tickets} tickets"
                ),
                state="complete",
            )
        except Exception as exc:
            status.update(label=f"Error: {exc}", state="error")
            st.error(f"Analysis failed: {type(exc).__name__}: {exc}")
            import traceback

            st.code(traceback.format_exc(), language="text")

    if st.session_state.analysis_result:
        st.rerun()

result = st.session_state.analysis_result

if result:
    st.markdown("---")

    events = result.get("classified_events", [])
    remediations = result.get("remediations", [])
    critical_count = sum(1 for e in events if e.get("severity") == "critical")
    warning_count = sum(1 for e in events if e.get("severity") == "warning")
    info_count = sum(1 for e in events if e.get("severity") == "info")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Events", len(events))
    m2.metric("Critical", critical_count)
    m3.metric("Warnings", warning_count)
    m4.metric("Info", info_count)
    m5.metric("Issues Found", len(remediations))

    tab_events, tab_remed, tab_runbook, tab_slack, tab_jira, tab_schemas = st.tabs([
        "📊 Classified Events",
        "🔧 Remediations",
        "📖 Runbook",
        "💬 Slack Notifications",
        "🎫 JIRA Tickets",
        "🔍 Inferred Schemas",
    ])

    with tab_events:
        if events:
            import pandas as pd

            df = pd.json_normalize(events)
            display_cols = [
                c
                for c in ["severity", "category", "summary", "source_file"]
                if c in df.columns
            ]
            if display_cols:

                def color_severity(val):
                    colors = {
                        "critical": "background-color: #fee2e2",
                        "warning": "background-color: #fef3c7",
                        "info": "background-color: #dbeafe",
                    }
                    return colors.get(val, "")

                styled = df[display_cols].style.map(
                    color_severity,
                    subset=["severity"] if "severity" in display_cols else [],
                )
                st.dataframe(styled, use_container_width=True, height=400)
            else:
                st.dataframe(df, use_container_width=True, height=400)
        else:
            st.info("No events parsed.")

    with tab_remed:
        if remediations:
            for r in remediations:
                sev = r.get("severity", "unknown")
                cat = r.get("category", "unknown")
                from tools import route_to_channel

                channel = route_to_channel(cat)
                icon = "🔴" if sev == "critical" else "🟡"
                with st.expander(
                    f"{icon} {r.get('title', 'Issue')}  |  {channel}",
                    expanded=(sev == "critical"),
                ):
                    col_a, col_b, col_c = st.columns(3)
                    col_a.markdown(f"**Severity:** {sev.upper()}")
                    col_b.markdown(f"**Category:** {cat}")
                    col_c.markdown(f"**Slack Channel:** `{channel}`")

                    systems = r.get("affected_systems", [])
                    if systems:
                        st.markdown(f"**Affected Systems:** {', '.join(systems)}")
                    st.markdown(f"**Root Cause:** {r.get('root_cause', 'Unknown')}")

                    steps = r.get("remediation_steps", [])
                    if steps:
                        st.markdown("**Remediation Steps:**")
                        if isinstance(steps, list):
                            for i, step in enumerate(steps, 1):
                                st.markdown(f"{i}. {step}")
                        else:
                            st.markdown(steps)

                    commands = r.get("cli_commands", [])
                    if commands:
                        st.markdown("**CLI Commands:**")
                        cmd_text = (
                            "\n".join(commands)
                            if isinstance(commands, list)
                            else str(commands)
                        )
                        st.code(cmd_text, language="bash")

                    st.markdown(f"**Verification:** {r.get('verification', 'N/A')}")
                    st.markdown(f"**Risk Level:** {r.get('risk_level', 'N/A')}")
        else:
            st.success("No actionable issues found — all events are informational.")

    with tab_runbook:
        cookbook = result.get("cookbook", "")
        if cookbook:
            st.markdown(cookbook)
            st.download_button(
                "📥 Download Runbook",
                data=cookbook,
                file_name="incident_runbook.md",
                mime="text/markdown",
            )
        else:
            st.info("No runbook generated.")

    with tab_slack:
        notifications = result.get("notifications_sent", [])
        if notifications:
            for n in notifications:
                channel = n.get("channel", "unknown")
                is_mock = n.get("mock", True)
                mode_badge = "🧪 MOCK" if is_mock else "✅ SENT"
                st.markdown(f"### {channel}  `{mode_badge}`")
                if "text" in n:
                    st.text(n["text"])
                st.json(n)
                st.markdown("---")
        else:
            st.info("No Slack notifications sent.")

    with tab_jira:
        tickets = result.get("jira_tickets", [])
        if tickets:
            for t in tickets:
                is_mock = t.get("mock", True)
                key = t.get("key", "UNKNOWN")
                mode_badge = "🧪 MOCK" if is_mock else "✅ CREATED"
                st.markdown(f"### {key}  `{mode_badge}`")
                st.json(t)
        else:
            st.info("No JIRA tickets (no critical-severity issues detected).")

    with tab_schemas:
        schemas = result.get("inferred_schemas", {})
        if schemas:
            for filename, schema in schemas.items():
                with st.expander(f"📄 {filename}", expanded=True):
                    fmt = schema.get("format_name", "Unknown")
                    desc = schema.get("description", "")
                    st.markdown(f"**Format:** {fmt}")
                    if desc:
                        st.markdown(f"**Description:** {desc}")
                    fields = schema.get("fields", [])
                    if fields:
                        st.markdown("**Fields:**")
                        import pandas as pd

                        st.dataframe(pd.DataFrame(fields), use_container_width=True)
        else:
            st.info("No schemas inferred.")

    errors = result.get("errors", [])
    if errors:
        with st.expander("⚠️ Errors encountered during analysis", expanded=False):
            for err in errors:
                st.error(err)

    st.markdown("---")
    st.download_button(
        "📥 Download Full Analysis (JSON)",
        data=json.dumps(result, indent=2, default=str),
        file_name="incident_analysis.json",
        mime="application/json",
    )
