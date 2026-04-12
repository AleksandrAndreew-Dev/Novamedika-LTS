"""initial schema — all models

Revision ID: c1ccc306e9ec
Revises:
Create Date: 2026-04-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c1ccc306e9ec"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === EXTENSIONS ===
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "unaccent"')

    # === TABLE: pharmacies ===
    op.create_table(
        "pharmacies",
        sa.Column(
            "uuid",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("name", sa.String(30), nullable=False),
        sa.Column("pharmacy_number", sa.String(100), nullable=False),
        sa.Column("city", sa.String(30), nullable=True),
        sa.Column("address", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(100), nullable=True),
        sa.Column("opening_hours", sa.String(255), nullable=True),
        sa.Column("chain", sa.String(50), nullable=False),
        sa.UniqueConstraint("name", "pharmacy_number", name="uq_pharmacy_name_number"),
    )

    # === TABLE: products ===
    op.create_table(
        "products",
        sa.Column(
            "uuid",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("form", sa.String(255), nullable=False, server_default="-"),
        sa.Column("manufacturer", sa.String(255), nullable=False, server_default=""),
        sa.Column("country", sa.String(255), nullable=False, server_default=""),
        sa.Column("serial", sa.String(255), nullable=False, server_default=""),
        sa.Column("price", sa.Numeric(12, 2), server_default="0"),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("total_price", sa.Numeric(12, 2), server_default="0"),
        sa.Column("expiry_date", sa.Date, nullable=False),
        sa.Column("category", sa.String(255), nullable=False, server_default=""),
        sa.Column("import_date", sa.Date, nullable=True),
        sa.Column("internal_code", sa.String(255), nullable=True),
        sa.Column(
            "wholesale_price", sa.Numeric(12, 2), nullable=False, server_default="0"
        ),
        sa.Column("retail_price", sa.Numeric(12, 2), server_default="0"),
        sa.Column("distributor", sa.String(255), nullable=False, server_default=""),
        sa.Column("internal_id", sa.String(255), nullable=False, server_default=""),
        sa.Column(
            "pharmacy_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pharmacies.uuid"),
            index=True,
        ),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.Column("is_removed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("removed_at", sa.DateTime, nullable=True),
        sa.Column("search_vector", postgresql.TSVECTOR, nullable=True),
    )
    op.create_index(
        "idx_product_search_vector",
        "products",
        ["search_vector"],
        postgresql_using="gin",
    )
    op.create_index(
        "idx_product_name_gin", "products", ["name"], postgresql_using="gin"
    )
    op.create_index("idx_product_manufacturer", "products", ["manufacturer"])
    op.create_index("idx_product_form", "products", ["form"])
    op.create_index("idx_product_price", "products", ["price"])
    op.create_index("idx_product_is_removed", "products", ["is_removed"])

    # FTS trigger для products
    op.execute(
        """
        CREATE OR REPLACE FUNCTION products_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('russian', coalesce(NEW.name, '')), 'A') ||
                setweight(to_tsvector('russian', coalesce(NEW.manufacturer, '')), 'B') ||
                setweight(to_tsvector('russian', coalesce(NEW.form, '')), 'C') ||
                setweight(to_tsvector('russian', coalesce(NEW.distributor, '')), 'D');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    )
    op.execute(
        """
        CREATE TRIGGER tsvectorupdate_products BEFORE INSERT OR UPDATE
        ON products FOR EACH ROW EXECUTE FUNCTION products_search_vector_update();
    """
    )

    # === TABLE: qa_users ===
    op.create_table(
        "qa_users",
        sa.Column(
            "uuid",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("telegram_id", sa.BigInteger, unique=True, nullable=True),
        sa.Column("telegram_username", sa.String(100), nullable=True),
        sa.Column("first_name", sa.String(100), nullable=True),
        sa.Column("last_name", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("user_type", sa.String(20), server_default="customer"),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
    )

    # === TABLE: qa_pharmacists ===
    op.create_table(
        "qa_pharmacists",
        sa.Column(
            "uuid",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("qa_users.uuid"),
            nullable=False,
        ),
        sa.Column(
            "pharmacy_info", postgresql.JSON, nullable=False, server_default="{}"
        ),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("is_online", sa.Boolean, server_default="false"),
        sa.Column("last_seen", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
    )

    # === TABLE: qa_questions ===
    op.create_table(
        "qa_questions",
        sa.Column(
            "uuid",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("qa_users.uuid"),
            nullable=False,
        ),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("category", sa.String(50), server_default="general"),
        sa.Column(
            "assigned_to",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("qa_pharmacists.uuid"),
            nullable=True,
        ),
        sa.Column(
            "answered_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("qa_pharmacists.uuid"),
            nullable=True,
        ),
        sa.Column(
            "taken_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("qa_pharmacists.uuid"),
            nullable=True,
        ),
        sa.Column("taken_at", sa.DateTime, nullable=True),
        sa.Column("context_data", postgresql.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("answered_at", sa.DateTime, nullable=True),
    )

    # === TABLE: qa_answers ===
    op.create_table(
        "qa_answers",
        sa.Column(
            "uuid",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "question_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("qa_questions.uuid"),
            nullable=False,
        ),
        sa.Column(
            "pharmacist_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("qa_pharmacists.uuid"),
            nullable=False,
        ),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
    )

    # === TABLE: qa_dialog_messages ===
    op.create_table(
        "qa_dialog_messages",
        sa.Column(
            "uuid",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "question_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("qa_questions.uuid"),
            nullable=False,
        ),
        sa.Column("message_type", sa.String(20), nullable=False),
        sa.Column("sender_type", sa.String(20), nullable=False),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("text", sa.Text, nullable=True),
        sa.Column("file_id", sa.String(500), nullable=True),
        sa.Column("caption", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("is_deleted", sa.Boolean, server_default="false"),
    )
    op.create_index("idx_dialog_question_id", "qa_dialog_messages", ["question_id"])
    op.create_index("idx_dialog_created_at", "qa_dialog_messages", ["created_at"])
    op.create_index(
        "idx_dialog_sender", "qa_dialog_messages", ["sender_type", "sender_id"]
    )

    # === TABLE: booking_orders ===
    op.create_table(
        "booking_orders",
        sa.Column(
            "uuid",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("external_order_id", sa.String(255), nullable=True, index=True),
        sa.Column(
            "pharmacy_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pharmacies.uuid"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.uuid"),
            nullable=True,
        ),
        sa.Column("product_name", sa.String(255), nullable=True),
        sa.Column("product_form", sa.String(255), nullable=True),
        sa.Column("product_manufacturer", sa.String(255), nullable=True),
        sa.Column("product_country", sa.String(255), nullable=True),
        sa.Column("product_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("product_serial", sa.String(255), nullable=True),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("customer_name", sa.String(100), nullable=False),
        sa.Column("customer_phone", sa.String(20), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("scheduled_pickup", sa.DateTime(timezone=True), nullable=True),
        sa.Column("telegram_id", sa.BigInteger, nullable=True, index=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.String(255), nullable=True),
        sa.CheckConstraint("quantity > 0", name="ck_booking_quantity_positive"),
    )
    op.create_index("idx_booking_status", "booking_orders", ["status"])
    op.create_index("idx_booking_pharmacy", "booking_orders", ["pharmacy_id"])
    op.create_index("idx_booking_created", "booking_orders", ["created_at"])
    op.create_index("idx_booking_product_id", "booking_orders", ["product_id"])

    # === TABLE: pharmacy_api_configs ===
    op.create_table(
        "pharmacy_api_configs",
        sa.Column(
            "uuid",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "pharmacy_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pharmacies.uuid"),
            nullable=False,
            unique=True,
        ),
        sa.Column("api_type", sa.String(50), nullable=False),
        sa.Column("endpoint_url", sa.String(500), nullable=False),
        sa.Column("auth_token", sa.LargeBinary, nullable=False),
        sa.Column("auth_type", sa.String(50), server_default="bearer"),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("sync_from_date", sa.DateTime(timezone=True), nullable=True),
    )

    # === TABLE: sync_logs ===
    op.create_table(
        "sync_logs",
        sa.Column(
            "uuid",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "pharmacy_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pharmacies.uuid"),
            nullable=False,
        ),
        sa.Column("sync_type", sa.String(50), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), server_default="running"),
        sa.Column("records_processed", sa.Integer, server_default="0"),
        sa.Column("details", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("sync_logs")
    op.drop_table("pharmacy_api_configs")
    op.drop_table("booking_orders")
    op.drop_table("qa_dialog_messages")
    op.drop_table("qa_answers")
    op.drop_table("qa_questions")
    op.drop_table("qa_pharmacists")
    op.drop_table("qa_users")
    op.execute("DROP TRIGGER IF EXISTS tsvectorupdate_products ON products")
    op.execute("DROP FUNCTION IF EXISTS products_search_vector_update()")
    op.drop_table("products")
    op.drop_table("pharmacies")
    op.execute('DROP EXTENSION IF EXISTS "unaccent"')
    op.execute('DROP EXTENSION IF EXISTS "pg_trgm"')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
