"""Начальная схема под PostgreSQL.

Старые SQLite-ревизии (7dc609e004b8, 0727e0138c95, 91bc28e7a102) сведены сюда: демо-данные грузит сид.

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# Автогенерация не удаляет enum-типы Postgres, поэтому downgrade делает это сам.
ENUM_TYPES = (
    "audience_type", "audit_action", "audit_entity", "campaign_state", "client_kind",
    "content_type", "media_kind", "outbox_status", "place_state", "segment_kind",
    "segment_state", "user_role",
)  # fmt: skip


def upgrade() -> None:
    op.create_table(
        "banner_types",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("description", sa.String(length=100), nullable=False),
        sa.Column("preview_form", sa.String(length=32), nullable=False),
        sa.Column("title_max_length", sa.Integer(), nullable=False),
        sa.Column("text_max_length", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "title_max_length > 0 AND text_max_length > 0",
            name=op.f("ck_banner_types_max_lengths_positive"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_banner_types")),
        sa.UniqueConstraint("code", name=op.f("uq_banner_types_code")),
    )
    op.create_table(
        "channels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("description", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_channels")),
        sa.UniqueConstraint("code", name=op.f("uq_channels_code")),
    )
    op.create_table(
        "outbox_events",
        sa.Column("topic", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "done", "dead", name="outbox_status"),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox_events")),
    )
    op.create_index(
        "ix_outbox_events_pending",
        "outbox_events",
        ["available_at"],
        unique=False,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_table(
        "segment_types",
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_segment_types")),
    )
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tags")),
        sa.UniqueConstraint("name", name=op.f("uq_tags_name")),
    )
    op.create_table(
        "topics",
        sa.Column("value", sa.String(length=32), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("value", name=op.f("pk_topics")),
    )
    op.create_table(
        "users",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "role",
            sa.Enum("campaignManager", "campaignModerator", "admin", name="user_role"),
            nullable=False,
        ),
        sa.Column("banned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("auth_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
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
        sa.CheckConstraint("email = lower(email)", name=op.f("ck_users_email_lowercase")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index(
        "uq_users_username_lower", "users", [sa.literal_column("lower(username)")], unique=True
    )
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=True),
        sa.Column(
            "entity",
            sa.Enum(
                "CAMPAIGN",
                "BANNER",
                "CONTENT",
                "CREATIVE",
                "SEGMENTS",
                "PLACE",
                "TAG",
                name="audit_entity",
            ),
            nullable=False,
        ),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "action",
            sa.Enum(
                "CREATE",
                "UPDATE",
                "DELETE",
                "TO_MODERATION",
                "DECLINE",
                "APPROVE",
                "ACTIVATE",
                "STOP",
                name="audit_action",
            ),
            nullable=False,
        ),
        sa.Column("changes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name=op.f("fk_audit_log_actor_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_log")),
    )
    op.create_index(
        "ix_audit_log_campaign_at", "audit_log", ["campaign_id", "at", "id"], unique=False
    )
    op.create_table(
        "auth_sessions",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("client", sa.Enum("web", "mobile", name="client_kind"), nullable=False),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_auth_sessions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_sessions")),
    )
    op.create_index(op.f("ix_auth_sessions_user_id"), "auth_sessions", ["user_id"], unique=False)
    op.create_table(
        "banner_type_channels",
        sa.Column("banner_type_id", sa.Integer(), nullable=False),
        sa.Column("channel_code", sa.String(length=16), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["banner_type_id"],
            ["banner_types.id"],
            name=op.f("fk_banner_type_channels_banner_type_id_banner_types"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["channel_code"],
            ["channels.code"],
            name=op.f("fk_banner_type_channels_channel_code_channels"),
            onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "banner_type_id", "channel_code", name=op.f("pk_banner_type_channels")
        ),
    )
    op.create_table(
        "campaigns",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("marketing_name", sa.String(length=100), nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("topic", sa.String(length=32), nullable=False),
        sa.Column("keywords", sa.String(length=512), nullable=True),
        sa.Column(
            "audience_type", sa.Enum("ALL_USERS", "SEGMENTED", name="audience_type"), nullable=False
        ),
        sa.Column("weight", sa.Double(), server_default="0", nullable=False),
        sa.Column("initial_ctr", sa.Double(), server_default="15", nullable=False),
        sa.Column(
            "state",
            sa.Enum(
                "DRAFT",
                "ON_MODERATION",
                "NEEDS_WORK",
                "APPROVED",
                "ACTIVE",
                "ACTIVE_EDITING",
                "STOPPED",
                "ARCHIVED",
                name="campaign_state",
            ),
            nullable=False,
        ),
        sa.Column("published", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("last_editor_id", sa.Uuid(), nullable=False),
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
        sa.CheckConstraint(
            "NOT published OR state NOT IN ('STOPPED', 'ARCHIVED')",
            name=op.f("ck_campaigns_published_state"),
        ),
        sa.CheckConstraint(
            "end_at IS NULL OR end_at > start_at", name=op.f("ck_campaigns_period_valid")
        ),
        sa.CheckConstraint(
            "initial_ctr >= 0 AND initial_ctr <= 100", name=op.f("ck_campaigns_initial_ctr_range")
        ),
        sa.CheckConstraint("weight >= 0", name=op.f("ck_campaigns_weight_non_negative")),
        sa.ForeignKeyConstraint(
            ["author_id"], ["users.id"], name=op.f("fk_campaigns_author_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["last_editor_id"], ["users.id"], name=op.f("fk_campaigns_last_editor_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["topic"], ["topics.value"], name=op.f("fk_campaigns_topic_topics")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_campaigns")),
        sa.UniqueConstraint("name", name=op.f("uq_campaigns_name")),
    )
    op.create_index(op.f("ix_campaigns_author_id"), "campaigns", ["author_id"], unique=False)
    op.create_index("ix_campaigns_start_at", "campaigns", ["start_at"], unique=False)
    op.create_index("ix_campaigns_state", "campaigns", ["state"], unique=False)
    op.create_index(op.f("ix_campaigns_topic"), "campaigns", ["topic"], unique=False)
    op.create_table(
        "media_objects",
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("upload", "generated", "pattern", "studio", name="media_kind"),
            nullable=False,
        ),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("size_bytes > 0", name=op.f("ck_media_objects_size_positive")),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_media_objects_owner_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_media_objects")),
        sa.UniqueConstraint("key", name=op.f("uq_media_objects_key")),
    )
    op.create_index(op.f("ix_media_objects_kind"), "media_objects", ["kind"], unique=False)
    op.create_table(
        "places",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("default_banner", sa.String(length=32), nullable=True),
        sa.Column("state", sa.Enum("ACTIVE", "INACTIVE", name="place_state"), nullable=False),
        sa.ForeignKeyConstraint(
            ["default_banner"],
            ["banner_types.code"],
            name=op.f("fk_places_default_banner_banner_types"),
            onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_places")),
        sa.UniqueConstraint("code", name=op.f("uq_places_code")),
    )
    op.create_table(
        "segments",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("state", sa.Enum("ACTIVE", "NEW", name="segment_state"), nullable=False),
        sa.Column("count", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("count >= 0", name=op.f("ck_segments_count_non_negative")),
        sa.ForeignKeyConstraint(
            ["type"], ["segment_types.code"], name=op.f("fk_segments_type_segment_types")
        ),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_segments")),
    )
    op.create_index(op.f("ix_segments_type"), "segments", ["type"], unique=False)
    op.create_table(
        "banners",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("banner_type_id", sa.Integer(), nullable=False),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["banner_type_id"],
            ["banner_types.id"],
            name=op.f("fk_banners_banner_type_id_banner_types"),
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["campaigns.id"],
            name=op.f("fk_banners_campaign_id_campaigns"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_banners")),
        sa.UniqueConstraint("campaign_id", "id", name="uq_banners_campaign_id_id"),
    )
    op.create_index(op.f("ix_banners_banner_type_id"), "banners", ["banner_type_id"], unique=False)
    op.create_table(
        "campaign_places",
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["campaigns.id"],
            name=op.f("fk_campaign_places_campaign_id_campaigns"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["place_id"], ["places.id"], name=op.f("fk_campaign_places_place_id_places")
        ),
        sa.PrimaryKeyConstraint("campaign_id", "place_id", name=op.f("pk_campaign_places")),
    )
    op.create_index(
        op.f("ix_campaign_places_place_id"), "campaign_places", ["place_id"], unique=False
    )
    op.create_table(
        "campaign_segments",
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("segment_code", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.Enum("included", "excluded", name="segment_kind"), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["campaigns.id"],
            name=op.f("fk_campaign_segments_campaign_id_campaigns"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["segment_code"],
            ["segments.code"],
            name=op.f("fk_campaign_segments_segment_code_segments"),
        ),
        sa.PrimaryKeyConstraint("campaign_id", "segment_code", name=op.f("pk_campaign_segments")),
    )
    op.create_index(
        op.f("ix_campaign_segments_segment_code"),
        "campaign_segments",
        ["segment_code"],
        unique=False,
    )
    op.create_table(
        "campaign_tags",
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["campaigns.id"],
            name=op.f("fk_campaign_tags_campaign_id_campaigns"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], name=op.f("fk_campaign_tags_tag_id_tags")),
        sa.PrimaryKeyConstraint("campaign_id", "tag_id", name=op.f("pk_campaign_tags")),
    )
    op.create_index(op.f("ix_campaign_tags_tag_id"), "campaign_tags", ["tag_id"], unique=False)
    op.create_table(
        "chat_sessions",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["campaigns.id"],
            name=op.f("fk_chat_sessions_campaign_id_campaigns"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_chat_sessions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chat_sessions")),
    )
    op.create_index(
        op.f("ix_chat_sessions_campaign_id"), "chat_sessions", ["campaign_id"], unique=False
    )
    op.create_index(op.f("ix_chat_sessions_user_id"), "chat_sessions", ["user_id"], unique=False)
    op.create_index(
        "uq_chat_sessions_active",
        "chat_sessions",
        ["user_id", "campaign_id"],
        unique=True,
        postgresql_where=sa.text("archived_at IS NULL"),
    )
    op.create_table(
        "contents",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("content_type", sa.Enum("PROMO", name="content_type"), nullable=False),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["campaigns.id"],
            name=op.f("fk_contents_campaign_id_campaigns"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contents")),
        sa.UniqueConstraint("campaign_id", "id", name="uq_contents_campaign_id_id"),
    )
    op.create_table(
        "studio_documents",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("document", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("render_id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_studio_documents_owner_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["render_id"],
            ["media_objects.id"],
            name=op.f("fk_studio_documents_render_id_media_objects"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_studio_documents")),
    )
    op.create_table(
        "creatives",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("banner_id", sa.Integer(), nullable=False),
        sa.Column("content_id", sa.Integer(), nullable=True),
        sa.Column("channel_code", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(
            ["campaign_id", "banner_id"],
            ["banners.campaign_id", "banners.id"],
            name="fk_creatives_banner_same_campaign",
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id", "content_id"],
            ["contents.campaign_id", "contents.id"],
            name="fk_creatives_content_same_campaign",
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["campaigns.id"],
            name=op.f("fk_creatives_campaign_id_campaigns"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["channel_code"], ["channels.code"], name=op.f("fk_creatives_channel_code_channels")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_creatives")),
        sa.UniqueConstraint("campaign_id", "banner_id", "channel_code", name="uq_creatives_slot"),
    )
    op.create_index("ix_creatives_banner_id", "creatives", ["banner_id"], unique=False)
    op.create_index("ix_creatives_content_id", "creatives", ["content_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_creatives_content_id", table_name="creatives")
    op.drop_index("ix_creatives_banner_id", table_name="creatives")
    op.drop_table("creatives")
    op.drop_table("studio_documents")
    op.drop_table("contents")
    op.drop_index(
        "uq_chat_sessions_active",
        table_name="chat_sessions",
        postgresql_where=sa.text("archived_at IS NULL"),
    )
    op.drop_index(op.f("ix_chat_sessions_user_id"), table_name="chat_sessions")
    op.drop_index(op.f("ix_chat_sessions_campaign_id"), table_name="chat_sessions")
    op.drop_table("chat_sessions")
    op.drop_index(op.f("ix_campaign_tags_tag_id"), table_name="campaign_tags")
    op.drop_table("campaign_tags")
    op.drop_index(op.f("ix_campaign_segments_segment_code"), table_name="campaign_segments")
    op.drop_table("campaign_segments")
    op.drop_index(op.f("ix_campaign_places_place_id"), table_name="campaign_places")
    op.drop_table("campaign_places")
    op.drop_index(op.f("ix_banners_banner_type_id"), table_name="banners")
    op.drop_table("banners")
    op.drop_index(op.f("ix_segments_type"), table_name="segments")
    op.drop_table("segments")
    op.drop_table("places")
    op.drop_index(op.f("ix_media_objects_kind"), table_name="media_objects")
    op.drop_table("media_objects")
    op.drop_index(op.f("ix_campaigns_topic"), table_name="campaigns")
    op.drop_index("ix_campaigns_state", table_name="campaigns")
    op.drop_index("ix_campaigns_start_at", table_name="campaigns")
    op.drop_index(op.f("ix_campaigns_author_id"), table_name="campaigns")
    op.drop_table("campaigns")
    op.drop_table("banner_type_channels")
    op.drop_index(op.f("ix_auth_sessions_user_id"), table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_index("ix_audit_log_campaign_at", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_index("uq_users_username_lower", table_name="users")
    op.drop_table("users")
    op.drop_table("topics")
    op.drop_table("tags")
    op.drop_table("segment_types")
    op.drop_index(
        "ix_outbox_events_pending",
        table_name="outbox_events",
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.drop_table("outbox_events")
    op.drop_table("channels")
    op.drop_table("banner_types")
    for name in ENUM_TYPES:
        op.execute(f"DROP TYPE IF EXISTS {name}")
