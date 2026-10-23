from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field

from aegisops.integrations.prometheus import (
    QUERIES,
    MetricSample,
    PrometheusError,
    query_prometheus_range,
)


class MetricSummary(BaseModel):
    metric_name: str
    query: str
    count: int
    min: float | None = None
    max: float | None = None
    avg: float | None = None
    first: float | None = None
    last: float | None = None
    samples: list[MetricSample] = Field(default_factory=list)


class HistoricalEvidenceData(BaseModel):
    window_start: datetime
    window_end: datetime
    step: str = "15s"
    metrics: dict[str, MetricSummary]
    errors: dict[str, str] = Field(default_factory=dict)


def collect_historical_metric_window(
    alert_started_at: datetime,
    window_before_minutes: int = 5,
    window_after_minutes: int = 5,
    step: str = "15s",
) -> HistoricalEvidenceData:
    if alert_started_at.utcoffset() is None:
        raise ValueError("Alert occurrence timestamp must be timezone-aware")

    start = alert_started_at - timedelta(minutes=window_before_minutes)
    end = alert_started_at + timedelta(minutes=window_after_minutes)

    now = datetime.now(UTC)
    end = min(end, now)

    if start >= end:
        start = end - timedelta(minutes=1)

    metrics: dict[str, MetricSummary] = {}
    errors: dict[str, str] = {}

    for name, expr in QUERIES.items():
        try:
            samples = query_prometheus_range(
                expression=expr,
                start=start,
                end=end,
                step=step,
            )

            if samples:
                values = [s.value for s in samples]
                metrics[name] = MetricSummary(
                    metric_name=name,
                    query=expr,
                    count=len(values),
                    min=min(values),
                    max=max(values),
                    avg=round(sum(values) / len(values), 4),
                    first=values[0],
                    last=values[-1],
                    samples=samples,
                )
            else:
                metrics[name] = MetricSummary(
                    metric_name=name,
                    query=expr,
                    count=0,
                    min=None,
                    max=None,
                    avg=None,
                    first=None,
                    last=None,
                    samples=[],
                )

        except PrometheusError as exc:
            errors[name] = str(exc)
            metrics[name] = MetricSummary(
                metric_name=name,
                query=expr,
                count=0,
                min=None,
                max=None,
                avg=None,
                first=None,
                last=None,
                samples=[],
            )

    return HistoricalEvidenceData(
        window_start=start,
        window_end=end,
        step=step,
        metrics=metrics,
        errors=errors,
    )
