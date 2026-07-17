"""Unique key on rag_chunks for upsert (tenant_id, source_type, source_id)

Revision ID: 004
Revises: 003
Create Date: 2026-07-16

"""

from collections.abc import Sequence

from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Keep newest row when duplicates exist from pre-upsert ingest.
    op.execute(
        """
        DELETE FROM rag_chunks a
        USING rag_chunks b
        WHERE a.tenant_id = b.tenant_id
          AND a.source_type = b.source_type
          AND a.source_id IS NOT DISTINCT FROM b.source_id
          AND a.created_at < b.created_at
        """
    )
    op.create_unique_constraint(
        "uq_rag_chunks_tenant_source",
        "rag_chunks",
        ["tenant_id", "source_type", "source_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_rag_chunks_tenant_source", "rag_chunks", type_="unique")
