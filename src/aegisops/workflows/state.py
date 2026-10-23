from typing import Literal, NotRequired, TypedDict
from uuid import UUID

Severity = Literal["critical", "high", "medium", "low"]
Priority = Literal["P1", "P2", "P3", "P4"]

MetricEvidence = dict[str, float | None]


class IncidentState(TypedDict):
    incident_id: UUID
    title: str
    severity: Severity
    status: str

    alert_name: NotRequired[str]
    priority: NotRequired[Priority]
    requires_escalation: NotRequired[bool]
    evidence: NotRequired[MetricEvidence]
    monitoring_error: NotRequired[str | None]
    investigation: NotRequired[dict | None]
    investigation_error: NotRequired[str | None]
    evidence_collected_at: NotRequired[str | None]
    alert_started_at: NotRequired[str | None]
    evidence_type: NotRequired[str]
    historical_evidence: NotRequired[dict | None]
    historical_evidence_error: NotRequired[str | None]
    historical_window: NotRequired[dict[str, str] | None]
    rca: NotRequired[dict | None]
    rca_error: NotRequired[str | None]
    remediation_plan: NotRequired[dict | None]
    remediation_error: NotRequired[str | None]
