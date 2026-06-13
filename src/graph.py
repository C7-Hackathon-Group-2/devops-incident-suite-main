"""LangGraph state-graph wiring for the incident analysis pipeline.

Defines the directed acyclic graph of agent nodes with a conditional
edge that routes critical incidents through Slack and JIRA before
reaching the runbook generator.

Graph topology::

    START → log_reader → remediation → route_by_severity
        critical → notification → jira → cookbook → END
        normal   → cookbook → END
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents import (
    cookbook_node,
    jira_node,
    log_reader_node,
    notification_node,
    remediation_node,
)
from state import IncidentState


def route_by_severity(state: IncidentState) -> str:
    """Determine whether the pipeline should follow the critical path.

    Inspects ``state["remediations"]`` for any entry with
    ``severity == "critical"``.

    Args:
        state: Current pipeline state containing ``remediations``.

    Returns:
        ``"critical"`` if at least one remediation is critical,
        otherwise ``"normal"``.
    """
    remediations: list[dict] = state.get("remediations", [])
    has_critical: bool = any(r.get("severity") == "critical" for r in remediations)
    return "critical" if has_critical else "normal"


def build_incident_graph() -> CompiledStateGraph:
    """Construct and compile the incident analysis state graph.

    Wires the five agent nodes together with a conditional edge on
    ``route_by_severity`` so that Slack notifications and JIRA ticket
    creation only run when critical-severity issues are found.

    Returns:
        A compiled LangGraph ready for ``graph.invoke(initial_state)``.
    """
    graph: StateGraph = StateGraph(IncidentState)

    graph.add_node("log_reader", log_reader_node)
    graph.add_node("remediation", remediation_node)
    graph.add_node("notification", notification_node)
    graph.add_node("jira", jira_node)
    graph.add_node("cookbook", cookbook_node)

    graph.set_entry_point("log_reader")
    graph.add_edge("log_reader", "remediation")
    graph.add_conditional_edges(
        "remediation",
        route_by_severity,
        {"critical": "notification", "normal": "cookbook"},
    )
    graph.add_edge("notification", "jira")
    graph.add_edge("jira", "cookbook")
    graph.add_edge("cookbook", END)

    return graph.compile()
