"""Generate project report PDF for the DevOps Incident Analysis Suite."""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    HRFlowable, KeepTogether, Image, Preformatted,
)
from pathlib import Path

OUTPUT = "DevOps_Incident_Suite_Project_Report.pdf"

styles = getSampleStyleSheet()

styles.add(ParagraphStyle(
    "CoverTitle", parent=styles["Title"], fontSize=28, leading=34,
    spaceAfter=6, textColor=HexColor("#1a1a2e"),
))
styles.add(ParagraphStyle(
    "CoverSub", parent=styles["Normal"], fontSize=14, leading=18,
    textColor=HexColor("#555555"), alignment=TA_CENTER, spaceAfter=4,
))
styles.add(ParagraphStyle(
    "SectionHead", parent=styles["Heading1"], fontSize=18, leading=22,
    spaceBefore=20, spaceAfter=10, textColor=HexColor("#1a1a2e"),
))
styles.add(ParagraphStyle(
    "SubHead", parent=styles["Heading2"], fontSize=14, leading=17,
    spaceBefore=14, spaceAfter=6, textColor=HexColor("#2d3436"),
))
styles.add(ParagraphStyle(
    "Body", parent=styles["Normal"], fontSize=10.5, leading=15,
    spaceAfter=8,
))
styles.add(ParagraphStyle(
    "BulletCustom", parent=styles["Normal"], fontSize=10.5, leading=15,
    leftIndent=20, bulletIndent=10, spaceAfter=4,
))
styles.add(ParagraphStyle(
    "PreCode", parent=styles["Code"], fontSize=8.5, leading=11,
    leftIndent=20, backColor=HexColor("#f5f5f5"), spaceAfter=8,
    borderWidth=0.5, borderColor=HexColor("#dddddd"), borderPadding=8,
    fontName="Courier",
))
styles.add(ParagraphStyle(
    "Caption", parent=styles["Normal"], fontSize=9, leading=12,
    textColor=HexColor("#888888"), alignment=TA_CENTER, spaceAfter=12,
))


def hr():
    return HRFlowable(width="100%", thickness=0.5, color=HexColor("#cccccc"),
                      spaceBefore=6, spaceAfter=12)


def bullet(text):
    return Paragraph(f"•  {text}", styles["BulletCustom"])


def code_block(text):
    return Preformatted(text, styles["PreCode"])


def make_table(headers, rows, col_widths=None):
    data = [headers] + rows
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, -1), 9.5),
        ("BACKGROUND", (0, 1), (-1, -1), HexColor("#fafafa")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#ffffff"), HexColor("#f0f0f5")]),
        ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def build():
    doc = SimpleDocTemplate(
        OUTPUT, pagesize=letter,
        topMargin=0.75*inch, bottomMargin=0.75*inch,
        leftMargin=0.9*inch, rightMargin=0.9*inch,
        title="DevOps Incident Analysis Suite - Project Report",
        author="Wayne Johnston & Claude Opus 4.6",
    )
    story = []

    # -- Cover --
    story.append(Spacer(1, 2*inch))
    story.append(Paragraph("Multi-Agent DevOps<br/>Incident Analysis Suite", styles["CoverTitle"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Design, Build &amp; Deployment Report", styles["CoverSub"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("AI Engineering Accelerator - Cohort 7", styles["CoverSub"]))
    story.append(Spacer(1, 24))
    story.append(hr())
    story.append(Paragraph("Wayne Johnston", styles["CoverSub"]))
    story.append(Paragraph("June 13, 2026", styles["CoverSub"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Built with Claude Opus 4.6  |  LangGraph  |  LangChain  |  Streamlit", styles["CoverSub"]))
    story.append(PageBreak())

    # -- Table of Contents --
    story.append(Paragraph("Table of Contents", styles["SectionHead"]))
    story.append(hr())
    toc_items = [
        "1. Executive Summary",
        "2. Design &amp; Architecture",
        "3. Technology Stack",
        "4. Agent Design",
        "5. LangGraph Orchestration",
        "6. Slack Channel Routing",
        "7. Project Structure &amp; Implementation",
        "8. Shared State Schema",
        "9. Synthetic Log Samples",
        "10. Streamlit UI",
        "11. Security Considerations",
        "12. Deployment",
        "13. Verification &amp; Testing",
        "14. Risks &amp; Mitigations",
        "15. Future Enhancements",
    ]
    for item in toc_items:
        story.append(Paragraph(item, styles["Body"]))
    story.append(PageBreak())

    # -- 1. Executive Summary --
    story.append(Paragraph("1. Executive Summary", styles["SectionHead"]))
    story.append(hr())
    story.append(Paragraph(
        "The Multi-Agent DevOps Incident Analysis Suite is an AI-driven application "
        "designed for DevOps, SRE, and incident management teams. Users upload infrastructure "
        "log files (routers, switches, firewalls, servers) and a pipeline of LangGraph-orchestrated "
        "agents automatically analyzes the logs, classifies incidents, recommends remediations, "
        "generates actionable runbooks, and pushes notifications to Slack and JIRA.",
        styles["Body"],
    ))
    story.append(Paragraph(
        "The key differentiator is that the log parser is entirely AI-driven: no hardcoded regex "
        "or format-specific parsers. The LLM infers field meanings from log samples, supporting "
        "any log format including Cisco IOS syslog, CEF, RFC5424, and structured tabular formats.",
        styles["Body"],
    ))
    story.append(Paragraph("Key Capabilities:", styles["SubHead"]))
    for cap in [
        "AI-driven log format inference - no hardcoded parsers",
        "Multi-agent pipeline with 5 specialized agents orchestrated by LangGraph",
        "Automatic severity classification (critical / warning / info)",
        "Vendor-aware remediation with specific CLI commands",
        "Multi-channel Slack routing: #ops-incidents, #secops-incidents, #network-incidents",
        "JIRA ticket creation for critical-severity issues",
        "Markdown runbook generation with checklists and verification steps",
        "Directory watcher for automatic log ingestion",
        "Mock/live integration toggles for safe demo and production use",
    ]:
        story.append(bullet(cap))
    story.append(PageBreak())

    # -- 2. Design & Architecture --
    story.append(Paragraph("2. Design &amp; Architecture", styles["SectionHead"]))
    story.append(hr())
    story.append(Paragraph(
        "The system follows a pipeline architecture where six agents collaborate in sequence "
        "with conditional branching. The Orchestrator Agent, implemented as a LangGraph StateGraph, "
        "manages the flow between agents based on the severity of detected incidents.",
        styles["Body"],
    ))
    story.append(Paragraph("Architecture Flow:", styles["SubHead"]))
    story.append(code_block(
        "START --> Log Reader/Classifier --> Remediation --> route_by_severity\n"
        "  has_critical --> Slack Notifier --> JIRA Ticket Agent --> Cookbook --> END\n"
        "  no_critical  --> Cookbook --> END"
    ))

    diagram_path = Path(__file__).parent / "architecture_diagram.png"
    if diagram_path.exists():
        img_width = 6.0 * inch
        img_height = img_width * (520.0 / 700.0)
        story.append(Spacer(1, 8))
        story.append(Image(str(diagram_path), width=img_width, height=img_height))
        story.append(Paragraph("Figure 1: Multi-Agent Architecture Diagram", styles["Caption"]))

    story.append(Paragraph(
        "Each agent is implemented as a node function that reads from and writes to a shared "
        "TypedDict state (IncidentState). This allows agents to collaborate without direct coupling. "
        "The LangGraph StateGraph provides explicit control flow, conditional edges, and state "
        "management - an evolution from the simple agent patterns used in earlier cohort projects.",
        styles["Body"],
    ))
    story.append(Paragraph("Design Decisions:", styles["SubHead"]))
    for d in [
        "<b>AI-driven parsing over regex</b>: The LLM infers field meanings from log samples, "
        "making the system format-agnostic. No new code is needed to support new log types.",
        "<b>Mock-first integrations</b>: Slack and JIRA start in mock mode, showing what would "
        "be sent without requiring live credentials. A sidebar toggle switches to live mode.",
        "<b>Multi-channel Slack routing</b>: Incidents auto-route to the appropriate channel "
        "based on category, reducing alert noise for each team.",
        "<b>Framework-agnostic core</b>: The agent pipeline (agents.py, graph.py, tools.py, "
        "state.py) has zero Streamlit dependencies. Only app.py imports Streamlit, enabling "
        "a future Flask or FastAPI frontend swap with no core changes.",
        "<b>Directory watcher</b>: In addition to manual upload, the app can monitor a "
        "directory for new .log files using watchdog, enabling automated ingestion.",
    ]:
        story.append(bullet(d))
    story.append(PageBreak())

    # -- 3. Technology Stack --
    story.append(Paragraph("3. Technology Stack", styles["SectionHead"]))
    story.append(hr())
    story.append(make_table(
        ["Component", "Technology", "Purpose"],
        [
            ["LLM", "OpenAI GPT-4o via OpenRouter", "Log parsing, classification, remediation"],
            ["Orchestration", "LangGraph StateGraph", "Agent pipeline flow control"],
            ["Agent Framework", "LangChain Core", "Tool definitions, prompt templates"],
            ["UI", "Streamlit", "File upload, dashboard, results display"],
            ["Notifications", "Slack Webhook API", "Multi-channel incident alerts"],
            ["Ticketing", "JIRA REST API", "Critical issue ticket creation"],
            ["File Watcher", "watchdog", "Directory monitoring for auto-ingestion"],
            ["Environment", "python-dotenv", "API key management"],
            ["HTTP", "requests", "Slack/JIRA API calls"],
        ],
        col_widths=[1.6*inch, 2.2*inch, 2.8*inch],
    ))
    story.append(Spacer(1, 12))
    story.append(Paragraph("LLM Configuration:", styles["SubHead"]))
    story.append(code_block(
        'ChatOpenAI(\n'
        '    model="openai/gpt-4o",\n'
        '    openai_api_key=os.getenv("OPENROUTER_API_KEY"),\n'
        '    openai_api_base="https://openrouter.ai/api/v1",\n'
        '    temperature=0,\n'
        ')'
    ))
    story.append(PageBreak())

    # -- 4. Agent Design --
    story.append(Paragraph("4. Agent Design", styles["SectionHead"]))
    story.append(hr())

    story.append(Paragraph("4.1 Log Reader / Classifier Agent", styles["SubHead"]))
    story.append(Paragraph(
        "The core differentiator of the system. Uses a two-stage LLM approach with no "
        "hardcoded parsers:",
        styles["Body"],
    ))
    story.append(bullet(
        "<b>Stage 1 - Schema Inference</b>: Sends the first 15 lines of each log file to the LLM "
        "with the prompt: 'Analyze these log lines. Identify every field and its meaning.' "
        "Returns JSON with field positions, names, data types, and examples."
    ))
    story.append(bullet(
        "<b>Stage 2 - Full Parse</b>: Sends the complete log text plus inferred schema to the LLM "
        "to parse every line into structured JSON events. Multi-line entries are combined."
    ))
    story.append(bullet(
        "<b>Stage 3 - Classification</b>: Each event is classified by severity (critical/warning/info) "
        "and category (interface, auth, resource, policy, routing, security, etc.)."
    ))
    story.append(Paragraph(
        "For large files, logs are chunked into 100-line batches. The inferred schema is cached "
        "per file to avoid redundant LLM calls. All LLM responses use "
        "response_format={\"type\": \"json_object\"} for reliable parsing.",
        styles["Body"],
    ))

    story.append(Paragraph("4.2 Remediation Agent", styles["SubHead"]))
    story.append(Paragraph(
        "Filters events to warning and critical severity, groups by issue type, and produces "
        "vendor-aware remediation recommendations:",
        styles["Body"],
    ))
    for f in [
        "Root cause hypothesis",
        "Step-by-step remediation instructions",
        "Exact CLI commands (vendor-specific, e.g. Cisco IOS)",
        "Verification steps to confirm the fix",
        "Risk assessment of the remediation itself",
        "Category tag for Slack channel routing",
    ]:
        story.append(bullet(f))

    story.append(Paragraph("4.3 Cookbook Synthesizer Agent", styles["SubHead"]))
    story.append(Paragraph(
        "Takes all remediations and synthesizes a single, comprehensive Markdown runbook with: "
        "executive summary, priority matrix table, numbered remediation checklists with checkbox "
        "steps and code blocks for CLI commands, escalation criteria, and post-incident review items.",
        styles["Body"],
    ))

    story.append(Paragraph("4.4 Slack Notification Agent", styles["SubHead"]))
    story.append(Paragraph(
        "Groups remediations by category and routes each group to the appropriate Slack channel. "
        "Formats rich Slack messages with severity badges, affected systems, and issue summaries.",
        styles["Body"],
    ))

    story.append(Paragraph("4.5 JIRA Ticket Agent", styles["SubHead"]))
    story.append(Paragraph(
        "Creates JIRA tickets for each critical-severity issue. Ticket descriptions include "
        "root cause analysis, numbered remediation steps, and CLI commands in JIRA's {noformat} "
        "blocks. Priority is mapped from incident severity to JIRA priority levels.",
        styles["Body"],
    ))
    story.append(PageBreak())

    # -- 5. LangGraph Orchestration --
    story.append(Paragraph("5. LangGraph Orchestration", styles["SectionHead"]))
    story.append(hr())
    story.append(Paragraph(
        "The orchestrator is implemented as a LangGraph StateGraph in graph.py. Each agent "
        "is registered as a node, and edges define the execution flow. A conditional edge "
        "after the Remediation node checks if any critical-severity issues were found:",
        styles["Body"],
    ))
    story.append(code_block(
        'graph = StateGraph(IncidentState)\n'
        'graph.add_node("log_reader", log_reader_node)\n'
        'graph.add_node("remediation", remediation_node)\n'
        'graph.add_node("notification", notification_node)\n'
        'graph.add_node("jira", jira_node)\n'
        'graph.add_node("cookbook", cookbook_node)\n'
        'graph.set_entry_point("log_reader")\n'
        'graph.add_edge("log_reader", "remediation")\n'
        'graph.add_conditional_edges("remediation", route_by_severity, {\n'
        '    "critical": "notification",\n'
        '    "normal": "cookbook"\n'
        '})\n'
        'graph.add_edge("notification", "jira")\n'
        'graph.add_edge("jira", "cookbook")\n'
        'graph.add_edge("cookbook", END)'
    ))
    story.append(Paragraph(
        "The route_by_severity function checks if any remediation has severity == 'critical'. "
        "If so, the pipeline routes through the Slack and JIRA agents before generating the "
        "cookbook. Otherwise, it skips directly to cookbook generation.",
        styles["Body"],
    ))
    story.append(PageBreak())

    # -- 6. Slack Channel Routing --
    story.append(Paragraph("6. Slack Channel Routing", styles["SectionHead"]))
    story.append(hr())
    story.append(Paragraph(
        "Incidents are automatically routed to the appropriate Slack channel based on their "
        "category. This reduces alert noise by ensuring each team sees only relevant incidents:",
        styles["Body"],
    ))
    story.append(make_table(
        ["Slack Channel", "Categories Routed"],
        [
            ["#ops-incidents", "resource, application, database"],
            ["#secops-incidents", "security, auth, policy"],
            ["#network-incidents", "interface, routing, network, hardware"],
        ],
        col_widths=[2.5*inch, 4*inch],
    ))
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "The routing logic is defined in tools.py via a CHANNEL_ROUTING dictionary. The "
        "notification_node groups remediations by target channel and sends one formatted "
        "message per channel, each containing only the issues relevant to that team.",
        styles["Body"],
    ))

    # -- 7. Project Structure --
    story.append(Paragraph("7. Project Structure &amp; Implementation", styles["SectionHead"]))
    story.append(hr())
    story.append(code_block(
        "devops-incident-suite-main/\n"
        "|-- src/                    # Application source code\n"
        "|   |-- __init__.py\n"
        "|   |-- app.py              # Streamlit UI entry point\n"
        "|   |-- state.py            # IncidentState TypedDict (shared state)\n"
        "|   |-- agents.py           # 5 agent node functions + lazy LLM\n"
        "|   |-- graph.py            # LangGraph StateGraph wiring\n"
        "|   |-- tools.py            # @tool wrappers (Slack, JIRA) + channel routing\n"
        "|   |-- watcher.py          # Directory watcher (watchdog)\n"
        "|   +-- log_samples/        # Synthetic test logs\n"
        "|       |-- routers.log     # Cisco IOS syslog format\n"
        "|       |-- switches.log    # Structured tabular format\n"
        "|       |-- security.log    # CEF (Common Event Format)\n"
        "|       +-- servers.log     # RFC5424 syslog format\n"
        "|-- tests/                  # Unit tests (pytest)\n"
        "|   |-- __init__.py\n"
        "|   |-- conftest.py         # pytest path + shared fixtures\n"
        "|   |-- test_state.py       # State schema tests\n"
        "|   |-- test_tools.py       # Channel routing, Slack, JIRA tests\n"
        "|   |-- test_watcher.py     # Directory watcher tests\n"
        "|   |-- test_agents.py      # Agent node + LLM mock tests\n"
        "|   +-- test_graph.py       # Graph compilation + pipeline tests\n"
        "|-- docs/                   # Documentation & generated reports\n"
        "|   |-- generate_report.py  # PDF report generator (reportlab)\n"
        "|   |-- generate_slides.py  # Slide deck generator (python-pptx)\n"
        "|   |-- architecture_diagram.png\n"
        "|   |-- DevOps_Incident_Suite_Project_Report.pdf\n"
        "|   +-- DevOps_Incident_Suite_Presentation.pptx\n"
        "|-- requirements.txt        # Python dependencies\n"
        "|-- pyproject.toml          # pytest/coverage configuration\n"
        "|-- .env.example            # Environment variable template\n"
        "+-- .streamlit/\n"
        "    +-- config.toml         # Streamlit theme configuration"
    ))
    story.append(Paragraph(
        "The project uses a src/tests layout. The core pipeline "
        "(state.py, agents.py, graph.py, tools.py) has zero UI dependencies, enabling "
        "a future swap from Streamlit to Flask or FastAPI without changing the agent logic.",
        styles["Body"],
    ))
    story.append(PageBreak())

    # -- 8. Shared State Schema --
    story.append(Paragraph("8. Shared State Schema", styles["SectionHead"]))
    story.append(hr())
    story.append(Paragraph(
        "All agents communicate through a shared IncidentState TypedDict. Each node "
        "returns a partial dict that is merged into the running state by LangGraph:",
        styles["Body"],
    ))
    story.append(make_table(
        ["Field", "Type", "Description"],
        [
            ["raw_logs", "dict[str, str]", "Filename to full log text"],
            ["inferred_schemas", "dict[str, list]", "Filename to field definitions"],
            ["parsed_events", "list[dict]", "Unified parsed events"],
            ["classified_events", "list[dict]", "Events with severity + category"],
            ["remediations", "list[dict]", "Issue to fix mappings"],
            ["cookbook", "str", "Markdown runbook content"],
            ["notifications_sent", "list[dict]", "Slack message results"],
            ["jira_tickets", "list[dict]", "JIRA ticket references"],
            ["status", "str", "Current pipeline stage"],
            ["errors", "list[str]", "Accumulated error messages"],
        ],
        col_widths=[1.6*inch, 1.5*inch, 3.4*inch],
    ))

    # -- 9. Synthetic Log Samples --
    story.append(Spacer(1, 16))
    story.append(Paragraph("9. Synthetic Log Samples", styles["SectionHead"]))
    story.append(hr())
    story.append(Paragraph(
        "Four synthetic log files are included for development and demo purposes. Each uses "
        "a distinct format and embeds 3-4 incidents at varying severity levels. Some incidents "
        "correlate across files (e.g., a switch port flap causing a router OSPF adjacency loss).",
        styles["Body"],
    ))
    story.append(make_table(
        ["File", "Format", "Embedded Incidents"],
        [
            ["routers.log", "Cisco IOS syslog", "Link flaps, OSPF neighbor changes, high CPU"],
            ["switches.log", "Structured tabular", "Port errors, STP topology changes, MAC flaps"],
            ["security.log", "CEF (Common Event Format)", "ACL denies, auth failures, IDS alerts"],
            ["servers.log", "RFC5424 syslog", "Disk full, OOM kills, service crashes"],
        ],
        col_widths=[1.4*inch, 2*inch, 3.2*inch],
    ))
    story.append(PageBreak())

    # -- 10. Streamlit UI --
    story.append(Paragraph("10. Streamlit UI", styles["SectionHead"]))
    story.append(hr())
    story.append(Paragraph("Sidebar Configuration:", styles["SubHead"]))
    for item in [
        "OpenRouter API key input (never pre-filled, user must enter each session)",
        "Directory watcher path and scan controls",
        "Slack Mock/Live toggle with channel routing reference",
        "JIRA Mock/Live toggle with URL, email, token, and project key inputs",
        "All credential fields start empty with placeholder text",
    ]:
        story.append(bullet(item))

    story.append(Paragraph("Main Area:", styles["SubHead"]))
    for item in [
        "Multi-file upload accepting .log and .txt files",
        "'Load Samples' button to use synthetic logs",
        "'Use Watched' button to ingest from watched directory",
        "Log content preview with expandable sections",
        "'Analyze Incidents' button (blocked until API key is provided)",
        "Live progress status during analysis",
    ]:
        story.append(bullet(item))

    story.append(Paragraph("Results Tabs:", styles["SubHead"]))
    for item in [
        "<b>Classified Events</b>: Dataframe with severity color coding (red/yellow/blue)",
        "<b>Remediations</b>: Expandable cards per issue with CLI commands and channel routing",
        "<b>Runbook</b>: Rendered Markdown with download button",
        "<b>Slack Notifications</b>: Mock/real output grouped by channel",
        "<b>JIRA Tickets</b>: Ticket summaries with mock/created badges",
        "<b>Inferred Schemas</b>: AI-detected field definitions per log file",
    ]:
        story.append(bullet(item))

    # -- 11. Security --
    story.append(Paragraph("11. Security Considerations", styles["SectionHead"]))
    story.append(hr())
    for item in [
        "<b>No pre-filled credentials</b>: All API key and token fields start empty. "
        "Users must enter their own keys per session. Keys are never stored or persisted.",
        "<b>Secrets separation</b>: Server-side secrets (from .env or st.secrets) are reserved "
        "for API endpoint use only and are never exposed in the UI.",
        "<b>Analysis gating</b>: The Analyze button is disabled with a warning message until "
        "a valid API key is provided.",
        "<b>Mock-first integrations</b>: Slack and JIRA default to mock mode, preventing "
        "accidental production notifications during development and demos.",
        "<b>No sensitive data in git</b>: .gitignore excludes .env files, __pycache__, "
        "and IDE artifacts.",
    ]:
        story.append(bullet(item))
    story.append(PageBreak())

    # -- 12. Deployment --
    story.append(Paragraph("12. Deployment", styles["SectionHead"]))
    story.append(hr())
    story.append(Paragraph("GitHub Repository:", styles["SubHead"]))
    story.append(Paragraph(
        "The project is hosted at github.com/wjohnston99/devops-incident-suite on the main branch.",
        styles["Body"],
    ))
    story.append(Paragraph("Streamlit Cloud Deployment:", styles["SubHead"]))
    for i, step in enumerate([
        "Sign in to share.streamlit.io with GitHub account",
        "Click 'New app' and select the devops-incident-suite repository",
        "Set branch to 'main' and main file to 'src/app.py'",
        "No secrets required in Advanced Settings (users enter their own keys)",
        "Click Deploy - app will be live within 2 minutes",
    ], 1):
        story.append(bullet(f"<b>Step {i}</b>: {step}"))

    story.append(Paragraph("Future Deployment Options:", styles["SubHead"]))
    story.append(Paragraph(
        "The framework-agnostic core enables deployment on Flask, FastAPI, or any Python "
        "web framework. Since agents.py, graph.py, tools.py, and state.py have zero Streamlit "
        "imports, a Flask api.py can import and invoke the same pipeline via HTTP endpoints.",
        styles["Body"],
    ))

    # -- 13. Verification --
    story.append(Paragraph("13. Verification &amp; Testing", styles["SectionHead"]))
    story.append(hr())
    story.append(Paragraph("Verification Steps Performed:", styles["SubHead"]))
    for item in [
        "All Python modules import cleanly with no errors",
        "LangGraph StateGraph compiles and builds without errors",
        "LLM connection verified via OpenRouter (GPT-4o responds correctly)",
        "Full pipeline tested end-to-end: 10 events parsed, 1 remediation generated, "
        "1 Slack notification sent (mock), 1 JIRA ticket created (mock)",
        "Cookbook/runbook generated with proper Markdown formatting",
        "Channel routing verified: security maps to #secops-incidents, interface maps to "
        "#network-incidents, application maps to #ops-incidents",
        "Streamlit UI loads, file upload works, results tabs populate after analysis",
    ]:
        story.append(bullet(item))

    story.append(Paragraph("Test Suite (84 tests, 99% coverage):", styles["SubHead"]))
    story.append(make_table(
        ["Module", "Tests", "Coverage"],
        [
            ["test_state.py", "2", "TypedDict instantiation"],
            ["test_tools.py", "23", "Channel routing, Slack mock/live, JIRA mock/live"],
            ["test_watcher.py", "14", "File filtering, debounce, directory scan, error handling"],
            ["test_agents.py", "32", "Lazy LLM, all 5 agent nodes, JSON parse edge cases"],
            ["test_graph.py", "8", "Severity routing, graph compilation, full pipeline paths"],
        ],
        col_widths=[1.6*inch, 0.8*inch, 4.1*inch],
    ))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Test Commands:", styles["SubHead"]))
    story.append(code_block(
        '# Verify imports\n'
        'PYTHONPATH=src python -c "from state import IncidentState"\n'
        'PYTHONPATH=src python -c "from graph import build_incident_graph; \\\n'
        '    g = build_incident_graph()"\n'
        '\n'
        '# Run all tests\n'
        'python -m pytest tests/ -v --tb=short\n'
        '\n'
        '# Run with coverage\n'
        'python -m pytest tests/ -v --tb=short \\\n'
        '    --cov=state --cov=tools --cov=watcher \\\n'
        '    --cov=agents --cov=graph --cov-report=term-missing\n'
        '\n'
        '# Run the app\n'
        'streamlit run src/app.py'
    ))
    story.append(PageBreak())

    # -- 14. Risks & Mitigations --
    story.append(Paragraph("14. Risks &amp; Mitigations", styles["SectionHead"]))
    story.append(hr())
    story.append(make_table(
        ["Risk", "Mitigation"],
        [
            ["LLM returns malformed JSON",
             "Use response_format={\"type\":\"json_object\"}, retry once on parse failure"],
            ["Large log files exceed token budget",
             "Chunk into 100-line batches, cache inferred schema per file"],
            ["Mock mode forgotten during demo",
             "Sidebar shows prominent MOCK/LIVE badge with color indicators"],
            ["API key exposed in UI",
             "Fields never pre-filled, secrets reserved for API endpoint only"],
            ["Streamlit session state lost",
             "Logs and results stored in st.session_state, survive button reruns"],
        ],
        col_widths=[2.5*inch, 4*inch],
    ))

    # -- 15. Future Enhancements --
    story.append(Spacer(1, 16))
    story.append(Paragraph("15. Future Enhancements", styles["SectionHead"]))
    story.append(hr())
    for item in [
        "<b>Flask API endpoint</b>: Add api.py with POST /api/analyze accepting log files "
        "and returning JSON results. Uses server-side secrets from .env/st.secrets.",
        "<b>RAG-based remediation</b>: Embed historical runbooks in FAISS so the remediation "
        "agent can retrieve past fixes for similar incidents.",
        "<b>Real-time streaming</b>: Stream agent progress to the UI using LangGraph's "
        "streaming interface instead of batch invoke.",
        "<b>Correlation engine</b>: Cross-correlate events across multiple log files to "
        "identify cascading failures (e.g., switch flap causing router OSPF loss).",
        "<b>Persistent storage</b>: SQLite or PostgreSQL for incident history, enabling "
        "trend analysis and recurring issue detection.",
        "<b>PagerDuty integration</b>: Add critical incident escalation to PagerDuty "
        "alongside Slack and JIRA.",
        "<b>Custom log format registry</b>: Allow users to save and share inferred schemas "
        "to speed up future parsing of known log formats.",
    ]:
        story.append(bullet(item))

    story.append(Spacer(1, 36))
    story.append(hr())
    story.append(Paragraph(
        "This report was generated as part of the AI Engineering Accelerator (Cohort 7). "
        "The project demonstrates multi-agent orchestration, AI-driven log analysis, "
        "automated remediation mapping, and cross-tool notification in a scalable workflow.",
        styles["Caption"],
    ))

    doc.build(story)
    print(f"PDF generated: {OUTPUT}")


if __name__ == "__main__":
    build()
