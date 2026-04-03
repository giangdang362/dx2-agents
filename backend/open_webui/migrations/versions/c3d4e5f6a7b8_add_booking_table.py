"""Add booking table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-02 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from open_webui.migrations.util import get_existing_tables

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing_tables = set(get_existing_tables())

    if "booking" not in existing_tables:
        op.create_table(
            "booking",
            sa.Column("id", sa.String(), nullable=False, primary_key=True),
            sa.Column("title", sa.Text(), nullable=True),
            sa.Column("client", sa.Text(), nullable=True),
            sa.Column("date", sa.String(), nullable=True),
            sa.Column("start_time", sa.String(), nullable=True),
            sa.Column("end_time", sa.String(), nullable=True),
            sa.Column("capacity", sa.Integer(), nullable=True),
            sa.Column("location", sa.String(), nullable=True),
            sa.Column("room_name", sa.String(), nullable=True),
            sa.Column("room_code", sa.String(), nullable=True),
            sa.Column("room_floor", sa.Integer(), nullable=True),
            sa.Column("room_building", sa.String(), nullable=True),
            sa.Column("room_equipment", sa.Text(), nullable=True),
            sa.Column("requester", sa.Text(), nullable=True),
            sa.Column("invitees", sa.Text(), nullable=True),
            sa.Column("status", sa.String(), server_default="draft"),
            sa.Column("approver", sa.Text(), nullable=True),
            sa.Column("admin_note", sa.Text(), nullable=True),
            sa.Column("catering", sa.Text(), nullable=True),
            sa.Column("email_sent", sa.Boolean(), server_default="0"),
            sa.Column("email_details", sa.Text(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=True),
            sa.Column("updated_at", sa.BigInteger(), nullable=True),
        )
        op.create_index("idx_booking_date", "booking", ["date"])
        op.create_index("idx_booking_status", "booking", ["status"])
        op.create_index("idx_booking_requester", "booking", ["requester"])


def downgrade() -> None:
    op.drop_index("idx_booking_requester", table_name="booking")
    op.drop_index("idx_booking_status", table_name="booking")
    op.drop_index("idx_booking_date", table_name="booking")
    op.drop_table("booking")
