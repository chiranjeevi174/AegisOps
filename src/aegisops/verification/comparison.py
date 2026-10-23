from typing import Literal

from aegisops.verification.schemas import (
    MetricComparisonResult,
    MetricObservation,
    VerificationCriteria,
)

METRIC_EPSILON: dict[str, float] = {
    "aegisops_sim_cpu_usage_percent": 0.5,
    "aegisops_sim_latency_seconds": 0.005,
    "aegisops_sim_error_rate": 0.0001,
    "aegisops_sim_service_up": 0.01,
}


def compare_metric_observations(
    baseline: MetricObservation | None,
    followup: MetricObservation | None,
    criteria: VerificationCriteria,
) -> MetricComparisonResult:
    """Deterministically compares baseline and follow-up monitoring observations.

    Enforces strict mathematical validity, distinguishes zero from missing data,
    and adheres to metric-specific interpretations.
    """
    notes: list[str] = []

    if baseline is None or followup is None:
        notes.append(
            "Incomplete observation: baseline or follow-up evidence is missing."
        )
        metric_name = (
            baseline.metric_name
            if baseline
            else (followup.metric_name if followup else "unknown")
        )
        unit = baseline.unit if baseline else (followup.unit if followup else "unknown")
        return MetricComparisonResult(
            metric_name=metric_name,
            unit=unit,
            baseline_mean=baseline.mean_value if baseline else None,
            followup_mean=followup.mean_value if followup else None,
            absolute_change=None,
            relative_change_pct=None,
            direction="insufficient_evidence",
            sample_sufficiency=False,
            evaluation_notes=notes,
        )

    metric_name = baseline.metric_name
    unit = baseline.unit

    # Check sample counts
    # For service_up, 1 sample can suffice for instant checks; otherwise respect criteria.min_samples_required
    effective_min_samples = (
        1 if "service_up" in baseline.expression else criteria.min_samples_required
    )
    sufficient = (
        baseline.sample_count >= effective_min_samples
        and followup.sample_count >= effective_min_samples
        and baseline.mean_value is not None
        and followup.mean_value is not None
    )

    if not sufficient:
        notes.append(
            f"Insufficient samples for statistical verification (baseline samples: {baseline.sample_count}, "
            f"follow-up samples: {followup.sample_count}, required: {effective_min_samples})."
        )
        return MetricComparisonResult(
            metric_name=metric_name,
            unit=unit,
            baseline_mean=baseline.mean_value,
            followup_mean=followup.mean_value,
            absolute_change=None,
            relative_change_pct=None,
            direction="insufficient_evidence",
            sample_sufficiency=False,
            evaluation_notes=notes,
        )

    # We have sufficient valid numeric data
    base_mean = baseline.mean_value
    post_mean = followup.mean_value
    assert base_mean is not None and post_mean is not None

    abs_change = round(post_mean - base_mean, 4)

    # Relative change calculation
    rel_change_pct: float | None = None
    if abs(base_mean) < 1e-9:
        rel_change_pct = None
        notes.append(
            "Relative percentage change is mathematically undefined (baseline mean is zero)."
        )
    else:
        rel_change_pct = round(((post_mean - base_mean) / abs(base_mean)) * 100.0, 2)

    # Direction determination
    direction: Literal[
        "improved", "degraded", "unchanged", "insufficient_evidence", "undetermined"
    ]
    epsilon = METRIC_EPSILON.get(baseline.expression, 0.001)

    if "service_up" in baseline.expression:
        # Service availability ratio: higher values represent better availability.
        # Epsilon is the availability ratio stability tolerance (0.01 = 1.0% uptime change).
        if abs_change < -epsilon:
            direction = "degraded"
            notes.append(
                f"Service availability ratio decreased from {base_mean:.4f} to {post_mean:.4f} "
                f"({abs_change:+.4f}"
                + (f", {rel_change_pct:+.2f}%" if rel_change_pct is not None else "")
                + f"), exceeding stability tolerance ({epsilon}), indicating availability degradation."
            )
        elif abs_change > epsilon:
            direction = "improved"
            notes.append(
                f"Service availability ratio increased from {base_mean:.4f} to {post_mean:.4f} "
                f"({abs_change:+.4f}"
                + (f", {rel_change_pct:+.2f}%" if rel_change_pct is not None else "")
                + f"), exceeding stability tolerance ({epsilon}), indicating availability improvement."
            )
        else:
            direction = "unchanged"
            if base_mean >= 1.0 and post_mean >= 1.0:
                notes.append("Service availability remained continuously UP (1.0).")
            elif base_mean <= 0.0 and post_mean <= 0.0:
                notes.append("Service availability remained continuously DOWN (0.0).")
            else:
                notes.append(
                    f"Service availability ratio remained stable within tolerance "
                    f"(baseline: {base_mean:.4f}, follow-up: {post_mean:.4f}, tolerance: {epsilon})."
                )
    else:
        # cpu_percent, latency_seconds, error_rate: lower values are better
        if abs_change < -epsilon:
            direction = "improved"
            notes.append(
                f"Observed telemetry decrease: {abs_change} {unit}"
                + (f" ({rel_change_pct}%)" if rel_change_pct is not None else "")
                + "."
            )
        elif abs_change > epsilon:
            direction = "degraded"
            notes.append(
                f"Observed telemetry increase: +{abs_change} {unit}"
                + (f" (+{rel_change_pct}%)" if rel_change_pct is not None else "")
                + "."
            )
        else:
            direction = "unchanged"
            notes.append(
                f"Observed telemetry remained stable within epsilon ({epsilon} {unit})."
            )

    if direction == "improved":
        notes.append(
            "Advisory: Observed metric improvement cannot be attributed to the read-only diagnostic operation. "
            "Causality cannot be inferred without active, controlled remediation."
        )

    return MetricComparisonResult(
        metric_name=metric_name,
        unit=unit,
        baseline_mean=base_mean,
        followup_mean=post_mean,
        absolute_change=abs_change,
        relative_change_pct=rel_change_pct,
        direction=direction,
        sample_sufficiency=True,
        evaluation_notes=notes,
    )
