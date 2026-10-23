from datetime import UTC, datetime, timedelta
from typing import Literal

from aegisops.domain.execution import RemediationExecution
from aegisops.execution.diagnostics import DIAGNOSTIC_METRICS
from aegisops.integrations.prometheus import (
    MetricSample,
    PrometheusError,
    query_prometheus_range,
)
from aegisops.verification.schemas import (
    MetricObservation,
    VerificationCriteria,
)

SIMULATOR_SCENARIO_LIMITATION = (
    "The simulator changes scenarios automatically. Observed telemetry differences "
    "between baseline and follow-up intervals may be caused by background simulator scenario "
    "transitions rather than the read-only diagnostic operation."
)


def parse_step_seconds(step: str) -> float:
    """Parses Prometheus step string (e.g. '15s', '1m', '1h') to seconds."""
    clean = step.strip().lower()
    if clean.endswith("s"):
        return float(clean[:-1])
    elif clean.endswith("m"):
        return float(clean[:-1]) * 60.0
    elif clean.endswith("h"):
        return float(clean[:-1]) * 3600.0
    try:
        return float(clean)
    except ValueError:
        return 15.0


def assess_telemetry_coverage(
    samples: list[MetricSample],
    interval_start: datetime,
    interval_end: datetime,
    step: str,
    criteria: VerificationCriteria,
    is_service_up: bool = False,
) -> tuple[
    float,
    float | None,
    datetime | None,
    datetime | None,
    Literal[
        "available", "no_data", "insufficient_samples", "insufficient_coverage", "error"
    ],
    list[str],
]:
    """Deterministically evaluates observation window coverage, temporal gaps, and sample ordering.

    Returns:
        (coverage_pct, max_gap_seconds, first_sample_time, last_sample_time, availability, notes)
    """
    notes: list[str] = []
    if not samples:
        return (
            0.0,
            None,
            None,
            None,
            "no_data",
            ["No telemetry observations returned for requested interval."],
        )

    # Validate and normalize timestamp ordering
    ordered_samples = list(samples)
    if any(
        ordered_samples[i].timestamp < ordered_samples[i - 1].timestamp
        for i in range(1, len(ordered_samples))
    ):
        notes.append(
            "Out-of-order telemetry sample timestamps detected; sorted chronologically for coverage evaluation."
        )
        ordered_samples.sort(key=lambda s: s.timestamp)

    first_ts = ordered_samples[0].timestamp
    last_ts = ordered_samples[-1].timestamp
    requested_duration = max(1.0, (interval_end - interval_start).total_seconds())
    step_sec = max(1.0, parse_step_seconds(step))

    # Calculate temporal gaps
    max_gap: float | None = None
    if len(ordered_samples) > 1:
        gaps = [
            (
                ordered_samples[i].timestamp - ordered_samples[i - 1].timestamp
            ).total_seconds()
            for i in range(1, len(ordered_samples))
        ]
        max_gap = round(max(gaps), 2)
    else:
        max_gap = 0.0

    # Calculate estimated temporal coverage
    if len(ordered_samples) == 1:
        observed_span = min(step_sec, requested_duration)
    else:
        observed_span = max(0.0, (last_ts - first_ts).total_seconds())

    coverage_pct = round(min(100.0, (observed_span / requested_duration) * 100.0), 2)

    # 1. Sample count check
    effective_min_samples = 1 if is_service_up else criteria.min_samples_required
    if len(ordered_samples) < effective_min_samples:
        notes.append(
            f"Observed sample count ({len(ordered_samples)}) does not satisfy minimum required samples ({effective_min_samples})."
        )
        return (
            coverage_pct,
            max_gap,
            first_ts,
            last_ts,
            "insufficient_samples",
            notes,
        )

    # 2. Window coverage check
    if coverage_pct < criteria.min_coverage_pct:
        notes.append(
            f"Estimated observation window coverage ({coverage_pct}%) is below required threshold ({criteria.min_coverage_pct}%). "
            "Telemetry data is too sparse or interval is truncated."
        )
        return (
            coverage_pct,
            max_gap,
            first_ts,
            last_ts,
            "insufficient_coverage",
            notes,
        )

    # 3. Maximum gap check
    if max_gap is not None and max_gap > criteria.max_allowed_gap_seconds:
        notes.append(
            f"Maximum observed gap between samples ({max_gap}s) exceeds allowable limit ({criteria.max_allowed_gap_seconds}s). "
            "Data continuity is compromised."
        )
        return (
            coverage_pct,
            max_gap,
            first_ts,
            last_ts,
            "insufficient_coverage",
            notes,
        )

    notes.append(
        f"Temporal coverage verified: {coverage_pct}% over {requested_duration:.0f}s requested duration "
        f"(samples: {len(ordered_samples)}, max gap: {max_gap}s)."
    )
    return (
        coverage_pct,
        max_gap,
        first_ts,
        last_ts,
        "available",
        notes,
    )


def retrieve_baseline_evidence(
    execution: RemediationExecution,
    criteria: VerificationCriteria,
) -> tuple[MetricObservation | None, list[str]]:
    """Retrieves baseline monitoring evidence preceding execution start time.

    Labels retrospectively queried evidence explicitly.
    """
    limitations: list[str] = []
    operation_id = execution.operation_id

    metric_info = DIAGNOSTIC_METRICS.get(operation_id)
    if not metric_info:
        limitations.append(
            f"Operation '{operation_id}' does not target a known Prometheus metric."
        )
        return None, limitations

    expression = metric_info["expression"]
    unit = metric_info["unit"]
    metric_label = metric_info["label"]

    end_time = execution.started_at
    start_time = end_time - timedelta(minutes=criteria.baseline_window_minutes)

    try:
        samples = query_prometheus_range(
            expression=expression,
            start=start_time,
            end=end_time,
            step=criteria.step,
        )

        if not samples:
            return (
                MetricObservation(
                    metric_name=metric_label,
                    expression=expression,
                    unit=unit,
                    sample_count=0,
                    min_value=None,
                    max_value=None,
                    mean_value=None,
                    latest_value=None,
                    is_retrospective=True,
                    interval_start=start_time,
                    interval_end=end_time,
                    data_availability="no_data",
                    label="retrospectively_retrieved_baseline",
                    coverage_pct=0.0,
                    coverage_assessment="No samples returned by Prometheus for baseline window",
                ),
                limitations,
            )

        vals = [s.value for s in samples]
        mean_val = round(sum(vals) / len(vals), 4)
        min_val = round(min(vals), 4)
        max_val = round(max(vals), 4)
        latest_val = round(vals[-1], 4)

        (
            coverage_pct,
            max_gap,
            first_ts,
            last_ts,
            availability,
            coverage_notes,
        ) = assess_telemetry_coverage(
            samples=samples,
            interval_start=start_time,
            interval_end=end_time,
            step=criteria.step,
            criteria=criteria,
            is_service_up="service_up" in expression,
        )
        if availability != "available":
            limitations.extend(coverage_notes)

        return (
            MetricObservation(
                metric_name=metric_label,
                expression=expression,
                unit=unit,
                sample_count=len(vals),
                min_value=min_val,
                max_value=max_val,
                mean_value=mean_val,
                latest_value=latest_val,
                is_retrospective=True,
                interval_start=start_time,
                interval_end=end_time,
                data_availability=availability,
                label="retrospectively_retrieved_baseline",
                coverage_pct=coverage_pct,
                first_sample_time=first_ts,
                last_sample_time=last_ts,
                max_gap_seconds=max_gap,
                coverage_assessment="; ".join(coverage_notes),
            ),
            limitations,
        )

    except PrometheusError as exc:
        limitations.append(f"Failed to retrieve Prometheus baseline telemetry: {exc}")
        return (
            MetricObservation(
                metric_name=metric_label,
                expression=expression,
                unit=unit,
                sample_count=0,
                min_value=None,
                max_value=None,
                mean_value=None,
                latest_value=None,
                is_retrospective=True,
                interval_start=start_time,
                interval_end=end_time,
                data_availability="error",
                label="retrospectively_retrieved_baseline",
                coverage_pct=0.0,
                coverage_assessment=f"Prometheus error: {exc}",
            ),
            limitations,
        )


def retrieve_followup_evidence(
    execution: RemediationExecution,
    criteria: VerificationCriteria,
) -> tuple[MetricObservation | None, list[str]]:
    """Retrieves post-execution monitoring evidence following completion time."""
    limitations: list[str] = []
    operation_id = execution.operation_id

    metric_info = DIAGNOSTIC_METRICS.get(operation_id)
    if not metric_info:
        limitations.append(
            f"Operation '{operation_id}' does not target a known Prometheus metric."
        )
        return None, limitations

    expression = metric_info["expression"]
    unit = metric_info["unit"]
    metric_label = metric_info["label"]

    start_time = execution.completed_at
    target_end_time = start_time + timedelta(minutes=criteria.followup_window_minutes)
    now = datetime.now(UTC)

    # Bound by current timestamp
    end_time = min(target_end_time, now)

    # Check elapsed duration against requested window
    elapsed_duration = (end_time - start_time).total_seconds()
    requested_duration = max(1.0, (target_end_time - start_time).total_seconds())
    elapsed_pct = round((elapsed_duration / requested_duration) * 100.0, 2)

    # Check whether sufficient observation time has elapsed
    if elapsed_duration < 5:
        limitations.append(
            "Insufficient post-execution observation time elapsed since completion. "
            "Follow-up window has not yielded required observations. Retry verification after the observation window."
        )
        return (
            MetricObservation(
                metric_name=metric_label,
                expression=expression,
                unit=unit,
                sample_count=0,
                min_value=None,
                max_value=None,
                mean_value=None,
                latest_value=None,
                is_retrospective=False,
                interval_start=start_time,
                interval_end=target_end_time,
                data_availability="insufficient_samples",
                label="followup_monitoring_observation",
                coverage_pct=elapsed_pct,
                coverage_assessment=f"Incomplete follow-up window: {elapsed_pct}% elapsed",
            ),
            limitations,
        )

    if elapsed_pct < criteria.min_coverage_pct:
        limitations.append(
            f"Insufficient observation window coverage: follow-up window has not fully elapsed "
            f"({elapsed_pct}% elapsed of {criteria.followup_window_minutes}m). "
            f"Minimum required coverage is {criteria.min_coverage_pct}%. Retry verification after the observation window."
        )
        return (
            MetricObservation(
                metric_name=metric_label,
                expression=expression,
                unit=unit,
                sample_count=0,
                min_value=None,
                max_value=None,
                mean_value=None,
                latest_value=None,
                is_retrospective=False,
                interval_start=start_time,
                interval_end=target_end_time,
                data_availability="insufficient_coverage",
                label="followup_monitoring_observation",
                coverage_pct=elapsed_pct,
                coverage_assessment=f"Incomplete follow-up window: {elapsed_pct}% elapsed (threshold: {criteria.min_coverage_pct}%)",
            ),
            limitations,
        )

    try:
        samples = query_prometheus_range(
            expression=expression,
            start=start_time,
            end=end_time,
            step=criteria.step,
        )

        if not samples:
            return (
                MetricObservation(
                    metric_name=metric_label,
                    expression=expression,
                    unit=unit,
                    sample_count=0,
                    min_value=None,
                    max_value=None,
                    mean_value=None,
                    latest_value=None,
                    is_retrospective=False,
                    interval_start=start_time,
                    interval_end=end_time,
                    data_availability="no_data",
                    label="followup_monitoring_observation",
                    coverage_pct=0.0,
                    coverage_assessment="No samples returned by Prometheus for follow-up window",
                ),
                limitations,
            )

        vals = [s.value for s in samples]
        mean_val = round(sum(vals) / len(vals), 4)
        min_val = round(min(vals), 4)
        max_val = round(max(vals), 4)
        latest_val = round(vals[-1], 4)

        (
            coverage_pct,
            max_gap,
            first_ts,
            last_ts,
            availability,
            coverage_notes,
        ) = assess_telemetry_coverage(
            samples=samples,
            interval_start=start_time,
            interval_end=target_end_time,
            step=criteria.step,
            criteria=criteria,
            is_service_up="service_up" in expression,
        )
        if availability != "available":
            limitations.extend(coverage_notes)

        return (
            MetricObservation(
                metric_name=metric_label,
                expression=expression,
                unit=unit,
                sample_count=len(vals),
                min_value=min_val,
                max_value=max_val,
                mean_value=mean_val,
                latest_value=latest_val,
                is_retrospective=False,
                interval_start=start_time,
                interval_end=end_time,
                data_availability=availability,
                label="followup_monitoring_observation",
                coverage_pct=coverage_pct,
                first_sample_time=first_ts,
                last_sample_time=last_ts,
                max_gap_seconds=max_gap,
                coverage_assessment="; ".join(coverage_notes),
            ),
            limitations,
        )

    except PrometheusError as exc:
        limitations.append(f"Failed to retrieve Prometheus follow-up telemetry: {exc}")
        return (
            MetricObservation(
                metric_name=metric_label,
                expression=expression,
                unit=unit,
                sample_count=0,
                min_value=None,
                max_value=None,
                mean_value=None,
                latest_value=None,
                is_retrospective=False,
                interval_start=start_time,
                interval_end=end_time,
                data_availability="error",
                label="followup_monitoring_observation",
                coverage_pct=0.0,
                coverage_assessment=f"Prometheus error: {exc}",
            ),
            limitations,
        )
