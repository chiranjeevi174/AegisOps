"""security hardening and live diagnostics

Revision ID: e3f198b1a20c
Revises: d2eeb145916a
Create Date: 2026-10-16 19:55:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e3f198b1a20c"
down_revision: str | Sequence[str] | None = "d2eeb145916a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Update check constraints for mode and status
    op.drop_constraint("valid_execution_mode", "remediation_executions", type_="check")
    op.create_check_constraint(
        "valid_execution_mode",
        "remediation_executions",
        "mode IN ('simulation', 'live_diagnostic')",
    )

    op.drop_constraint(
        "valid_execution_status", "remediation_executions", type_="check"
    )
    op.create_check_constraint(
        "valid_execution_status",
        "remediation_executions",
        "status IN ('pending', 'running', 'simulated', 'diagnosed', 'failed', 'rejected', 'timed_out')",
    )

    # 2. Make simulation_result nullable and add diagnostic_result column
    op.alter_column(
        "remediation_executions",
        "simulation_result",
        existing_type=sa.JSON().with_variant(
            postgresql.JSONB(astext_type=sa.Text()), "postgresql"
        ),
        nullable=True,
    )
    op.add_column(
        "remediation_executions",
        sa.Column(
            "diagnostic_result",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=True,
        ),
    )

    # 3. Foreign key audit retention: Replace CASCADE with RESTRICT
    op.drop_constraint(
        "approval_events_approval_id_fkey", "approval_events", type_="foreignkey"
    )
    op.create_foreign_key(
        "approval_events_approval_id_fkey",
        "approval_events",
        "remediation_approvals",
        ["approval_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint(
        "execution_events_execution_id_fkey", "execution_events", type_="foreignkey"
    )
    op.create_foreign_key(
        "execution_events_execution_id_fkey",
        "execution_events",
        "remediation_executions",
        ["execution_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    # 1. Revert foreign keys to CASCADE
    op.drop_constraint(
        "execution_events_execution_id_fkey", "execution_events", type_="foreignkey"
    )
    op.create_foreign_key(
        "execution_events_execution_id_fkey",
        "execution_events",
        "remediation_executions",
        ["execution_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint(
        "approval_events_approval_id_fkey", "approval_events", type_="foreignkey"
    )
    op.create_foreign_key(
        "approval_events_approval_id_fkey",
        "approval_events",
        "remediation_approvals",
        ["approval_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 2. Drop diagnostic_result and restore simulation_result nullable=False
    op.drop_column("remediation_executions", "diagnostic_result")
    op.alter_column(
        "remediation_executions",
        "simulation_result",
        existing_type=sa.JSON().with_variant(
            postgresql.JSONB(astext_type=sa.Text()), "postgresql"
        ),
        nullable=False,
    )

    # 3. Revert check constraints
    op.drop_constraint(
        "valid_execution_status", "remediation_executions", type_="check"
    )
    op.create_check_constraint(
        "valid_execution_status",
        "remediation_executions",
        "status IN ('pending', 'running', 'simulated', 'failed', 'rejected', 'timed_out')",
    )

    op.drop_constraint("valid_execution_mode", "remediation_executions", type_="check")
    op.create_check_constraint(
        "valid_execution_mode",
        "remediation_executions",
        "mode IN ('simulation')",
    )
