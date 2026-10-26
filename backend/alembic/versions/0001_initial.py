"""Initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-25

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "proteins",
        sa.Column("accession", sa.String(length=20), nullable=False),
        sa.Column("canonical_sequence", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("retrieved_at", sa.String(length=40), nullable=False),
        sa.Column("source_version", sa.String(length=120), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("accession"),
    )
    op.create_table(
        "structures",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("accession", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("model_version", sa.String(length=40), nullable=False),
        sa.Column("chain", sa.String(length=8), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("mapping_json", sa.JSON(), nullable=False),
        sa.Column("retrieved_at", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["accession"], ["proteins.accession"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("accession", "source", "model_version", "chain", name="uq_structure"),
    )
    op.create_index("ix_structures_accession", "structures", ["accession"])
    op.create_table(
        "analyses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("accession", sa.String(length=20), nullable=False),
        sa.Column("structure_id", sa.Integer(), nullable=True),
        sa.Column("variant", sa.String(length=16), nullable=False),
        sa.Column("protein_name", sa.String(length=255), nullable=False),
        sa.Column("organism", sa.String(length=255), nullable=False),
        sa.Column("parameters_json", sa.JSON(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("algorithm_version", sa.String(length=20), nullable=False),
        sa.Column("schema_version", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("warnings_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["accession"], ["proteins.accession"]),
        sa.ForeignKeyConstraint(["structure_id"], ["structures.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analyses_accession", "analyses", ["accession"])
    op.create_index("ix_analyses_created_at", "analyses", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_analyses_created_at", table_name="analyses")
    op.drop_index("ix_analyses_accession", table_name="analyses")
    op.drop_table("analyses")
    op.drop_index("ix_structures_accession", table_name="structures")
    op.drop_table("structures")
    op.drop_table("proteins")
