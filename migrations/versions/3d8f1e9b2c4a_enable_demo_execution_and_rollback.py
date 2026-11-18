"""enable demo execution and rollback capabilities

Revision ID: 3d8f1e9b2c4a
Revises: 2b6feb4eb4be
Create Date: 2026-11-18 10:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "3d8f1e9b2c4a"
down_revision: str | Sequence[str] | None = "2b6feb4eb4be"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Update check constraints on remediation_executions
    op.drop_constraint("valid_execution_mode", "remediation_executions", type_="check")
    op.create_check_constraint(
        "valid_execution_mode",
        "remediation_executions",
        "mode IN ('simulation', 'live_diagnostic', 'demo_execution')",
    )

    op.drop_constraint(
        "valid_execution_status", "remediation_executions", type_="check"
    )
    op.create_check_constraint(
        "valid_execution_status",
        "remediation_executions",
        "status IN ('pending', 'running', 'simulated', 'diagnosed', 'executed', 'failed', 'rejected', 'timed_out')",
    )

    # 2. Add execution_result column to remediation_executions
    op.add_column(
        "remediation_executions",
        sa.Column(
            "execution_result",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=True,
        ),
    )

    # 3. Drop overly restrictive static constraints on rollback_assessments
    op.drop_constraint(
        "ck_rollback_execution_disabled", "rollback_assessments", type_="check"
    )
    op.drop_constraint(
        "ck_rollback_system_changes_disabled", "rollback_assessments", type_="check"
    )

    # 4. Create rollback_executions table
    op.create_table(
        "rollback_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("execution_id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("approval_id", sa.Uuid(), nullable=False),
        sa.Column("operation_id", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("requested_by", sa.String(length=100), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("restored_scenario", sa.String(length=50), nullable=False),
        sa.Column(
            "restored_state",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'executed', 'failed')",
            name="valid_rollback_execution_status",
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"], ["rollback_assessments.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["execution_id"], ["remediation_executions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["approval_id"], ["remediation_approvals.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "execution_id", "idempotency_key", name="uq_rollback_exec_idempotency_key"
        ),
    )
    op.create_index(
        "ix_rollback_executions_assessment_id",
        "rollback_executions",
        ["assessment_id"],
        unique=False,
    )
    op.create_index(
        "ix_rollback_executions_execution_id",
        "rollback_executions",
        ["execution_id"],
        unique=False,
    )
    op.create_index(
        "ix_rollback_executions_incident_id",
        "rollback_executions",
        ["incident_id"],
        unique=False,
    )
    op.create_index(
        "ix_rollback_executions_status",
        "rollback_executions",
        ["status"],
        unique=False,
    )

    # 5. Create rollback_execution_events table
    op.create_table(
        "rollback_execution_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rollback_execution_id", sa.Uuid(), nullable=False),
        sa.Column("execution_id", sa.Uuid(), nullable=False),
        sa.Column("actor", sa.String(length=100), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("previous_status", sa.String(length=30), nullable=True),
        sa.Column("new_status", sa.String(length=30), nullable=False),
        sa.Column(
            "details",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["rollback_execution_id"],
            ["rollback_executions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_rollback_execution_events_rb_exec_id",
        "rollback_execution_events",
        ["rollback_execution_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("rollback_execution_events")
    op.drop_table("rollback_executions")

    op.create_check_constraint(
        "ck_rollback_system_changes_disabled",
        "rollback_assessments",
        "system_changes_performed = FALSE",
    )
    op.create_check_constraint(
        "ck_rollback_execution_disabled",
        "rollback_assessments",
        "rollback_execution_enabled = FALSE",
    )

    op.drop_column("remediation_executions", "execution_result")

    op.drop_constraint(
        "valid_execution_status", "remediation_executions", type_="check"
    )
    op.create_check_constraint(
        "valid_execution_status",
        "remediation_executions",
        "status IN ('pending', 'running', 'simulated', 'diagnosed', 'failed', 'rejected', 'timed_out')",
    )

    op.drop_constraint("valid_execution_mode", "remediation_executions", type_="check")
    op.create_check_constraint(
        "valid_execution_mode",
        "remediation_executions",
        "mode IN ('simulation', 'live_diagnostic')",
    )
