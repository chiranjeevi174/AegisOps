from datetime import UTC, datetime

from aegisops.integrations.prometheus import PrometheusError, collect_metrics
from aegisops.workflows.state import IncidentState


def collect_incident_evidence(state: IncidentState) -> dict:
    if not state.get("alert_name"):
        return {
            "evidence": {},
            "evidence_type": "unavailable",
            "evidence_collected_at": None,
            "monitoring_error": None,
        }

    try:
        started_at = state.get("alert_started_at")
        timestamp = datetime.fromisoformat(started_at) if started_at else None

        if timestamp is not None and timestamp.utcoffset() is None:
            raise ValueError("Alert timestamp must include a timezone")

        metrics = collect_metrics(at=timestamp)
        evidence_type = "historical" if timestamp else "live_snapshot"

        if timestamp is not None and all(value is None for value in metrics.values()):
            live_metrics = collect_metrics(at=None)
            if any(value is not None for value in live_metrics.values()):
                metrics = live_metrics
                evidence_type = "live_snapshot"

        return {
            "evidence": metrics,
            "evidence_type": evidence_type,
            "evidence_collected_at": datetime.now(UTC).isoformat(),
            "monitoring_error": None,
        }

    except (PrometheusError, ValueError) as exc:
        return {
            "evidence": {},
            "evidence_type": "unavailable",
            "evidence_collected_at": None,
            "monitoring_error": str(exc),
        }
