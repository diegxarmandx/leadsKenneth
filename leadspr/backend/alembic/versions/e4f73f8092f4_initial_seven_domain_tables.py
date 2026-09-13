"""initial seven domain tables

Revision ID: e4f73f8092f4
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e4f73f8092f4"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_app_settings")),
        sa.UniqueConstraint("key", name=op.f("uq_app_settings_key")),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "actor_type",
            sa.Enum(
                "ADMIN", "SYSTEM", name="actor_type", native_enum=False, create_constraint=True
            ),
            nullable=False,
        ),
        sa.Column("actor_identifier", sa.Text(), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=True),
        sa.Column("entity_id", sa.Text(), nullable=True),
        sa.Column("old_values", sa.Text(), nullable=True),
        sa.Column("new_values", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("lead_date", sa.Date(), nullable=False),
        sa.Column("first_name", sa.Text(), nullable=False),
        sa.Column("last_name", sa.Text(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("municipality", sa.Text(), nullable=True),
        sa.Column("insurance_type", sa.Text(), server_default="Life Insurance", nullable=False),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("campaign", sa.Text(), nullable=True),
        sa.Column("language", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_leads")),
    )
    with op.batch_alter_table("leads", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_leads_external_id"), ["external_id"], unique=True)
        batch_op.create_index(
            batch_op.f("ix_leads_insurance_type"), ["insurance_type"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_leads_lead_date"), ["lead_date"], unique=False)
        batch_op.create_index(batch_op.f("ix_leads_municipality"), ["municipality"], unique=False)
        batch_op.create_index(batch_op.f("ix_leads_source_active"), ["source_active"], unique=False)

    op.create_table(
        "pricing_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("min_age_days", sa.Integer(), nullable=False),
        sa.Column("max_age_days", sa.Integer(), nullable=True),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("exclusion_days", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "exclusion_days >= 0", name=op.f("ck_pricing_rules_nonnegative_exclusion")
        ),
        sa.CheckConstraint(
            "max_age_days IS NULL OR max_age_days >= min_age_days",
            name=op.f("ck_pricing_rules_valid_range"),
        ),
        sa.CheckConstraint("min_age_days >= 0", name=op.f("ck_pricing_rules_nonnegative_min_age")),
        sa.CheckConstraint("price_cents > 0", name=op.f("ck_pricing_rules_positive_price")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pricing_rules")),
    )
    op.create_table(
        "purchases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.Text(), nullable=False),
        sa.Column("buyer_name", sa.Text(), nullable=False),
        sa.Column("buyer_email", sa.Text(), nullable=False),
        sa.Column("buyer_phone", sa.Text(), nullable=True),
        sa.Column("insurance_type", sa.Text(), server_default="Life Insurance", nullable=False),
        sa.Column("municipality", sa.Text(), nullable=True),
        sa.Column("requested_quantity", sa.Integer(), nullable=False),
        sa.Column("price_per_lead_cents", sa.Integer(), nullable=False),
        sa.Column("total_amount_cents", sa.Integer(), nullable=False),
        sa.Column("stripe_checkout_id", sa.Text(), nullable=True),
        sa.Column("stripe_payment_intent", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "PAID",
                "FULFILLED",
                "FAILED",
                "FULFILLMENT_FAILED",
                name="purchase_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fulfilled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("price_per_lead_cents > 0", name=op.f("ck_purchases_positive_price")),
        sa.CheckConstraint("requested_quantity > 0", name=op.f("ck_purchases_positive_quantity")),
        sa.CheckConstraint(
            "total_amount_cents = requested_quantity * price_per_lead_cents",
            name=op.f("ck_purchases_correct_total"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_purchases")),
        sa.UniqueConstraint("public_id", name=op.f("uq_purchases_public_id")),
        sa.UniqueConstraint("stripe_checkout_id", name=op.f("uq_purchases_stripe_checkout_id")),
    )
    with op.batch_alter_table("purchases", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_purchases_created_at"), ["created_at"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_purchases_stripe_payment_intent"), ["stripe_payment_intent"], unique=True
        )

    op.create_table(
        "sync_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "RUNNING",
                "SUCCESS",
                "FAILED",
                name="sync_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("rows_received", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("leads_created", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("leads_updated", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("leads_deactivated", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("leads_reactivated", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sync_runs")),
    )
    op.create_table(
        "purchase_leads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("purchase_id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("pricing_rule_id", sa.Integer(), nullable=False),
        sa.Column("price_paid_cents", sa.Integer(), nullable=False),
        sa.Column("purchased_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("excluded_until", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "excluded_until >= purchased_at", name=op.f("ck_purchase_leads_valid_exclusion")
        ),
        sa.CheckConstraint("price_paid_cents > 0", name=op.f("ck_purchase_leads_positive_price")),
        sa.ForeignKeyConstraint(
            ["lead_id"],
            ["leads.id"],
            name=op.f("fk_purchase_leads_lead_id_leads"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["pricing_rule_id"],
            ["pricing_rules.id"],
            name=op.f("fk_purchase_leads_pricing_rule_id_pricing_rules"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["purchase_id"],
            ["purchases.id"],
            name=op.f("fk_purchase_leads_purchase_id_purchases"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_purchase_leads")),
        sa.UniqueConstraint("purchase_id", "lead_id", name=op.f("uq_purchase_leads_purchase_id")),
    )
    with op.batch_alter_table("purchase_leads", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_purchase_leads_excluded_until"), ["excluded_until"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_purchase_leads_lead_id"), ["lead_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("purchase_leads", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_purchase_leads_lead_id"))
        batch_op.drop_index(batch_op.f("ix_purchase_leads_excluded_until"))

    op.drop_table("purchase_leads")
    op.drop_table("sync_runs")
    with op.batch_alter_table("purchases", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_purchases_stripe_payment_intent"))
        batch_op.drop_index(batch_op.f("ix_purchases_created_at"))

    op.drop_table("purchases")
    op.drop_table("pricing_rules")
    with op.batch_alter_table("leads", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_leads_source_active"))
        batch_op.drop_index(batch_op.f("ix_leads_municipality"))
        batch_op.drop_index(batch_op.f("ix_leads_lead_date"))
        batch_op.drop_index(batch_op.f("ix_leads_insurance_type"))
        batch_op.drop_index(batch_op.f("ix_leads_external_id"))

    op.drop_table("leads")
    op.drop_table("audit_logs")
    op.drop_table("app_settings")
