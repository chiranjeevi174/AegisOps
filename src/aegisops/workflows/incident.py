import logging
import time
from typing import Any

from langgraph.graph import END, START, StateGraph

from aegisops.agents.evidence import collect_incident_evidence
from aegisops.agents.historical_evidence import collect_historical_evidence_node
from aegisops.agents.investigation import investigate_incident
from aegisops.agents.rca import analyze_root_cause
from aegisops.agents.remediation import plan_remediation
from aegisops.agents.triage import triage_incident
from aegisops.observability.metrics import WORKFLOW_NODE_DURATION
from aegisops.services.remediation_safety import validate_remediation_safety_node
from aegisops.workflows.state import IncidentState

logger = logging.getLogger(__name__)


def _instrument_node(node_name: str, node_func: Any) -> Any:
    def wrapped(state: Any, *args: Any, **kwargs: Any) -> Any:
        start_time = time.perf_counter()
        logger.info(
            "Workflow node started",
            extra={
                "event": "workflow_node_start",
                "node_name": node_name,
                "incident_id": str(state.get("incident_id"))
                if state.get("incident_id")
                else None,
            },
        )
        try:
            result = node_func(state)
            duration = time.perf_counter() - start_time
            WORKFLOW_NODE_DURATION.labels(node=node_name).observe(duration)
            logger.info(
                "Workflow node completed",
                extra={
                    "event": "workflow_node_complete",
                    "node_name": node_name,
                    "duration_seconds": round(duration, 4),
                    "incident_id": str(state.get("incident_id"))
                    if state.get("incident_id")
                    else None,
                },
            )
            return result
        except Exception as exc:
            duration = time.perf_counter() - start_time
            WORKFLOW_NODE_DURATION.labels(node=node_name).observe(duration)
            logger.exception(
                "Workflow node failed",
                extra={
                    "event": "workflow_node_failed",
                    "node_name": node_name,
                    "duration_seconds": round(duration, 4),
                    "error_category": type(exc).__name__,
                    "incident_id": str(state.get("incident_id"))
                    if state.get("incident_id")
                    else None,
                },
            )
            raise

    return wrapped


def build_incident_workflow():
    workflow = StateGraph(IncidentState)

    workflow.add_node("triage", _instrument_node("triage", triage_incident))
    workflow.add_node(
        "collect_evidence",
        _instrument_node("collect_evidence", collect_incident_evidence),
    )
    workflow.add_node(
        "investigate", _instrument_node("investigate", investigate_incident)
    )
    workflow.add_node(
        "collect_historical_evidence",
        _instrument_node(
            "collect_historical_evidence", collect_historical_evidence_node
        ),
    )
    workflow.add_node(
        "root_cause_analysis",
        _instrument_node("root_cause_analysis", analyze_root_cause),
    )
    workflow.add_node(
        "remediation_planning",
        _instrument_node("remediation_planning", plan_remediation),
    )
    workflow.add_node(
        "safety_validation",
        _instrument_node("safety_validation", validate_remediation_safety_node),
    )

    workflow.add_edge(START, "triage")
    workflow.add_edge("triage", "collect_evidence")

    workflow.add_conditional_edges(
        "collect_evidence",
        lambda state: (
            "investigate"
            if (
                not state.get("monitoring_error")
                and any(
                    value is not None
                    for value in (state.get("evidence") or {}).values()
                )
            )
            else (
                "collect_historical_evidence" if state.get("alert_started_at") else END
            )
        ),
    )

    workflow.add_conditional_edges(
        "investigate",
        lambda state: (
            "collect_historical_evidence" if state.get("alert_started_at") else END
        ),
    )

    workflow.add_conditional_edges(
        "collect_historical_evidence",
        lambda state: (
            "root_cause_analysis"
            if (
                state.get("historical_evidence")
                and not state.get("historical_evidence_error")
            )
            else END
        ),
    )

    workflow.add_conditional_edges(
        "root_cause_analysis",
        lambda state: (
            "remediation_planning"
            if (state.get("rca") and not state.get("rca_error"))
            else END
        ),
    )

    workflow.add_edge("remediation_planning", "safety_validation")
    workflow.add_edge("safety_validation", END)

    return workflow.compile()


incident_workflow = build_incident_workflow()
