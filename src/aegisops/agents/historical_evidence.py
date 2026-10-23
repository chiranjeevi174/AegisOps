from datetime import datetime

from aegisops.integrations.prometheus import PrometheusError
from aegisops.services.historical_evidence import collect_historical_metric_window
from aegisops.workflows.state import IncidentState


def collect_historical_evidence_node(state: IncidentState) -> dict:
    started_at_str = state.get("alert_started_at")
    if not started_at_str:
        return {
            "historical_evidence": None,
            "historical_evidence_error": "Alert occurrence timestamp is not configured",
            "historical_window": None,
            "rca": None,
            "rca_error": "Historical correlation skipped: missing alert timestamp",
        }

    try:
        started_at = datetime.fromisoformat(started_at_str)
        if started_at.utcoffset() is None:
            raise ValueError(
                "Alert occurrence timestamp must include timezone information"
            )

        data = collect_historical_metric_window(alert_started_at=started_at)

        has_any_samples = any(summary.count > 0 for summary in data.metrics.values())

        window_dict = {
            "start": data.window_start.isoformat(),
            "end": data.window_end.isoformat(),
            "step": data.step,
        }

        if not has_any_samples:
            return {
                "historical_evidence": None,
                "historical_evidence_error": "No historical metrics available in the requested window",
                "historical_window": window_dict,
                "rca": None,
                "rca_error": "Historical correlation skipped: no monitoring samples available",
            }

        return {
            "historical_evidence": data.model_dump(mode="json"),
            "historical_evidence_error": None,
            "historical_window": window_dict,
        }

    except (PrometheusError, ValueError, KeyError, TypeError) as exc:
        return {
            "historical_evidence": None,
            "historical_evidence_error": str(exc),
            "historical_window": None,
            "rca": None,
            "rca_error": f"Historical evidence collection failed: {exc}",
        }
