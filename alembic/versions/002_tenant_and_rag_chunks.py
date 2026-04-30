"""Tenant id on scans and rag_chunks with pgvector

Revision ID: 002
Revises: 001
Create Date: 2026-04-23

"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Must stay aligned with packages.core.models.RagChunk and CLOUDOPT_EMBEDDING_DIMENSIONS default.
_EMBEDDING_DIM = 1024


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column(
        "scans",
        sa.Column("tenant_id", sa.String(255), nullable=False, server_default="default"),
    )
    op.create_index("ix_scans_tenant_id", "scans", ["tenant_id"], unique=False)
    op.alter_column("scans", "tenant_id", server_default=None)

    op.create_table(
        "rag_chunks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("source_id", sa.String(64), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(_EMBEDDING_DIM), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_rag_chunks_tenant_id", "rag_chunks", ["tenant_id"], unique=False)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_rag_chunks_embedding_hnsw ON rag_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_rag_chunks_embedding_hnsw")
    op.drop_index("ix_rag_chunks_tenant_id", table_name="rag_chunks")
    op.drop_table("rag_chunks")
    op.drop_index("ix_scans_tenant_id", table_name="scans")
    op.drop_column("scans", "tenant_id")
