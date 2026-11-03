from enum import StrEnum


class Topic(StrEnum):
    """Темы outbox: побочные эффекты, которые должны случиться только после коммита."""

    USER_REGISTERED = "user.registered"
    CAMPAIGN_SENT_TO_MODERATION = "campaign.sent_to_moderation"
    CAMPAIGN_REVIEWED = "campaign.reviewed"
    CAMPAIGN_ACTIVATED = "campaign.activated"


class OutboxStatus(StrEnum):
    PENDING = "pending"
    DONE = "done"
    DEAD = "dead"
