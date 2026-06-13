from langgraph.graph import StateGraph, END
from state import IncidentState
from agents import (
    log_reader_node,
    remediation_node,
    cookbook_node,
    notification_node,
    jira_node,
)


def route_by_severity(state: IncidentState) -> str:
    remediations = state.get("remediations", [])
    has_critical = any(r.get("severity") == "critical" for r in remediations)
    return "critical" if has_critical else "normal"


def build_incident_graph():
    graph = StateGraph(IncidentState)

    graph.add_node("log_reader", log_reader_node)
    graph.add_node("remediation", remediation_node)
    graph.add_node("notification", notification_node)
    graph.add_node("jira", jira_node)
    graph.add_node("cookbook", cookbook_node)

    graph.set_entry_point("log_reader")
    graph.add_edge("log_reader", "remediation")
    graph.add_conditional_edges("remediation", route_by_severity, {
        "critical": "notification",
        "normal": "cookbook",
    })
    graph.add_edge("notification", "jira")
    graph.add_edge("jira", "cookbook")
    graph.add_edge("cookbook", END)

    return graph.compile()
