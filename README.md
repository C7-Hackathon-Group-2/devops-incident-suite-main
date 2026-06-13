# Multi-Agent DevOps Incident Analysis Suite

AI-driven multi-agent application for DevOps and SRE teams. Upload infrastructure log files (routers, switches, firewalls, servers) and a pipeline of LangGraph-orchestrated agents automatically analyzes logs, classifies incidents, recommends remediations, generates runbooks, and pushes notifications to Slack and JIRA.

**AI Engineering Accelerator — Cohort 7**

## Key Features

- **AI-driven log parsing** — no hardcoded regex or format parsers; the LLM infers field meanings from log samples
- **5-agent pipeline** — parse → classify → remediate → notify → runbook
- **Multi-channel Slack routing** — incidents route to `#ops-incidents`, `#secops-incidents`, or `#network-incidents` by category
- **JIRA ticket creation** — automatic tickets for critical-severity issues
- **Markdown runbook generation** — actionable checklists with CLI commands and verification steps
- **Directory watcher** — automatic log ingestion via watchdog
- **Mock/live integration toggles** — safe demoing without live credentials

## Architecture

```
START → Log Reader/Classifier → Remediation → route_by_severity
  has_critical → Slack Notifier → JIRA Agent → Cookbook → END
  no_critical  → Cookbook → END
```

The core pipeline (`state.py`, `agents.py`, `graph.py`, `tools.py`) has zero Streamlit dependencies, enabling a future Flask/FastAPI frontend swap with no agent changes.

## Project Structure

```
devops-incident-suite/
├── src/                    # Application source code
│   ├── __init__.py
│   ├── app.py              # Streamlit UI entry point
│   ├── state.py            # IncidentState TypedDict (shared state)
│   ├── agents.py           # 5 agent node functions + lazy LLM
│   ├── graph.py            # LangGraph StateGraph wiring
│   ├── tools.py            # @tool wrappers (Slack, JIRA) + channel routing
│   ├── watcher.py          # Directory watcher (watchdog)
│   └── log_samples/        # Synthetic test logs
│       ├── routers.log     # Cisco IOS syslog format
│       ├── switches.log    # Structured tabular format
│       ├── security.log    # CEF (Common Event Format)
│       └── servers.log     # RFC5424 syslog format
├── tests/                  # Unit tests (pytest)
│   ├── __init__.py
│   ├── conftest.py         # pytest path configuration
│   ├── test_state.py       # State schema tests
│   ├── test_tools.py       # Channel routing, Slack, JIRA tests
│   ├── test_watcher.py     # Directory watcher tests
│   ├── test_agents.py      # Agent node + LLM mock tests
│   └── test_graph.py       # Graph compilation + pipeline tests
├── generate_report.py      # PDF report generator (reportlab)
├── generate_slides.py      # Slide deck generator (python-pptx)
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
└── .streamlit/
    └── config.toml         # Streamlit theme configuration
```

## Setup

### Prerequisites

- Python 3.11+
- An [OpenRouter](https://openrouter.ai/) API key (uses GPT-4o)

### Installation

```bash
git clone https://github.com/wjohnston99/devops-incident-suite.git
cd devops-incident-suite
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root (optional — keys can also be entered in the UI):

```
OPENROUTER_API_KEY=your_openrouter_key_here
```

For live Slack/JIRA integrations (optional):

```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your@email.com
JIRA_API_TOKEN=your_jira_token
JIRA_PROJECT_KEY=OPS
```

## Usage

### Run the App

```bash
streamlit run src/app.py
```

1. Enter your OpenRouter API key in the sidebar
2. Upload log files or click **Load Samples** to use the included synthetic logs
3. Click **Analyze Incidents**
4. View results across 6 tabs: Events, Remediations, Runbook, Slack, JIRA, Inferred Schemas

### Verify Imports

```bash
PYTHONPATH=src python -c "from state import IncidentState; print('state OK')"
PYTHONPATH=src python -c "from graph import build_incident_graph; g = build_incident_graph(); print('graph OK')"
```

## Testing

### Run All Tests

```bash
python -m pytest tests/ -v --tb=short
```

### Run Tests with Code Coverage

```bash
python -m pytest tests/ -v --tb=short \
  --cov=state --cov=tools --cov=watcher --cov=agents --cov=graph \
  --cov-report=term-missing
```

### Generate HTML Coverage Report

```bash
python -m pytest tests/ \
  --cov=state --cov=tools --cov=watcher --cov=agents --cov=graph \
  --cov-report=html
open htmlcov/index.html
```

### Current Coverage

| Module | Stmts | Miss | Cover | Missing |
|---|---|---|---|---|
| state.py | 12 | 0 | 100% | — |
| tools.py | 36 | 0 | 100% | — |
| watcher.py | 64 | 0 | 100% | — |
| graph.py | 21 | 0 | 100% | — |
| agents.py | 143 | 2 | 99% | 13, 17 |
| **TOTAL** | **276** | **2** | **99%** | |

The 2 uncovered lines are import-time `.env` path checks (`load_dotenv` calls) that execute during module import before test functions run.

### Test Suite Breakdown

| Module | Tests | Coverage |
|---|---|---|
| test_state.py | 2 | TypedDict instantiation |
| test_tools.py | 23 | Channel routing, Slack mock/live, JIRA mock/live |
| test_watcher.py | 10 | File filtering, debounce, directory scan, error handling |
| test_agents.py | 25 | Lazy LLM, all 5 agent nodes, JSON parse edge cases |
| test_graph.py | 8 | Severity routing, graph compilation, full pipeline paths |

## Slack Channel Routing

| Channel | Categories |
|---|---|
| `#ops-incidents` | resource, application, database |
| `#secops-incidents` | security, auth, policy |
| `#network-incidents` | interface, routing, network, hardware |

## Technology Stack

| Component | Technology |
|---|---|
| LLM | OpenAI GPT-4o via OpenRouter |
| Orchestration | LangGraph StateGraph |
| Agent Framework | LangChain Core |
| UI | Streamlit |
| Notifications | Slack Webhook API |
| Ticketing | JIRA REST API |
| File Watcher | watchdog |

## Deployment

Deployed on [Streamlit Cloud](https://share.streamlit.io):

1. Sign in to share.streamlit.io with GitHub
2. Click **New app** → select `devops-incident-suite` repo
3. Branch: `main` | Main file: `src/app.py`
4. No secrets required (users enter their own API keys)
5. Click **Deploy**

## License

This project was built as part of the AI Engineering Accelerator (Cohort 7).
