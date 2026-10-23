import uuid
from datetime import UTC, datetime

from sqlalchemy import func, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from aegisops.api.webhook_schemas import AlertmanagerPayload
from aegisops.domain.incident import Incident


async def process_alerts(
    session: AsyncSession,
    payload: AlertmanagerPayload,
) -> dict[str, int]:
    created_or_updated = 0
    resolved = 0
    now = datetime.now(UTC)

    for alert in payload.alerts:
        starts_at = alert.startsAt
        if starts_at is not None:
            starts_at = (
                starts_at.replace(tzinfo=UTC)
                if starts_at.tzinfo is None
                else starts_at.astimezone(UTC)
            )

        if alert.status == "resolved":
            result = await session.execute(
                update(Incident)
                .where(
                    Incident.alert_fingerprint == alert.fingerprint,
                    Incident.source == "alertmanager",
                )
                .values(
                    alert_state="resolved",
                    alert_updated_at=now,
                    alert_started_at=func.coalesce(
                        Incident.alert_started_at,
                        starts_at,
                    ),
                )
            )
            resolved += int(getattr(result, "rowcount", 0))
            continue

        severity = alert.labels.get("severity", "medium")

        if severity not in {"critical", "high", "medium", "low"}:
            severity = "medium"

        statement = insert(Incident).values(
            id=uuid.uuid4(),
            title=alert.annotations.get(
                "summary",
                alert.labels.get("alertname", "Monitoring alert"),
            )[:200],
            description=alert.annotations.get(
                "description",
                "Alert received from Alertmanager.",
            ),
            severity=severity,
            status="open",
            source="alertmanager",
            alert_fingerprint=alert.fingerprint,
            alert_state="firing",
            alert_started_at=starts_at,
            alert_updated_at=now,
            created_at=now,
        )

        statement = statement.on_conflict_do_update(
            constraint="uq_incidents_alert_fingerprint",
            set_={
                "alert_state": "firing",
                "alert_updated_at": now,
                "alert_started_at": func.coalesce(
                    Incident.alert_started_at,
                    statement.excluded.alert_started_at,
                ),
            },
        )

        await session.execute(statement)
        created_or_updated += 1

    await session.commit()

    return {
        "processed": created_or_updated,
        "resolved": resolved,
    }
