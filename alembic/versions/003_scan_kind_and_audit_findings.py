"""scan_kind on scans; audit fields on findings

Revision ID: 003
Revises: 002
Create Date: 2026-04-30

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scans",
        sa.Column("scan_kind", sa.String(32), nullable=False, server_default="finops"),
    )
    op.create_index("ix_scans_scan_kind", "scans", ["scan_kind"], unique=False)
    op.alter_column("scans", "scan_kind", server_default=None)

    op.add_column(
        "findings",
        sa.Column("finding_kind", sa.String(64), nullable=False, server_default="cost"),
    )
    op.add_column("findings", sa.Column("framework", sa.String(128), nullable=True))
    op.add_column("findings", sa.Column("control_id", sa.String(512), nullable=True))
    op.add_column("findings", sa.Column("audit_status", sa.String(32), nullable=True))
    op.create_index("ix_findings_finding_kind", "findings", ["finding_kind"], unique=False)
    op.create_index("ix_findings_framework", "findings", ["framework"], unique=False)
    op.alter_column("findings", "finding_kind", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_findings_framework", table_name="findings")
    op.drop_index("ix_findings_finding_kind", table_name="findings")
    op.drop_column("findings", "audit_status")
    op.drop_column("findings", "control_id")
    op.drop_column("findings", "framework")
    op.drop_column("findings", "finding_kind")
    op.drop_index("ix_scans_scan_kind", table_name="scans")
    op.drop_column("scans", "scan_kind")
