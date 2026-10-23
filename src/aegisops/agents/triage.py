from aegisops.workflows.state import IncidentState

PRIORITY_MAP = {
    "critical": "P1",
    "high": "P2",
    "medium": "P3",
    "low": "P4",
}


def triage_incident(state: IncidentState) -> dict:
    severity = str(state.get("severity", "medium") or "medium").lower()
    priority = PRIORITY_MAP.get(severity, "P3")

    return {
        "priority": priority,
        "requires_escalation": severity in {"critical", "high"},
    }
