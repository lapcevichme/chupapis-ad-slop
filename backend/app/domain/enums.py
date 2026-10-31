from enum import StrEnum


class CampaignState(StrEnum):
    DRAFT = "DRAFT"
    ON_MODERATION = "ON_MODERATION"
    NEEDS_WORK = "NEEDS_WORK"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    ACTIVE_EDITING = "ACTIVE_EDITING"
    STOPPED = "STOPPED"
    ARCHIVED = "ARCHIVED"


class AudienceType(StrEnum):
    ALL_USERS = "ALL_USERS"
    SEGMENTED = "SEGMENTED"


class Topic(StrEnum):
    EXTRA = "EXTRA"
    EVENT = "EVENT"
    RECOMMENDATION = "RECOMMENDATION"
    SALES = "SALES"
    FINANCIAL_TIPS = "FINANCIAL_TIPS"
    LIFESTYLE = "LIFESTYLE"
    RETARGET = "RETARGET"
    ADVICES = "ADVICES"
    HINTS = "HINTS"
    COURSES = "COURSES"
    OTHER = "OTHER"


class Role(StrEnum):
    MANAGER = "campaignManager"
    MODERATOR = "campaignModerator"


class ActionType(StrEnum):
    DEFAULT = "default"
    EXTERNAL_LINK = "externalLink"
    OPEN_SMART_LINK = "openSmartLink"
    CLOSE_CAMPAIGN = "closeCampaign"
    DONE_CAMPAIGN = "doneCampaign"


class FontWeight(StrEnum):
    THIN = "thin"
    LIGHT = "light"
    REGULAR = "regular"
    MEDIUM = "medium"
    SEMI_BOLD = "semi-bold"
    BOLD = "bold"


class SegmentState(StrEnum):
    ACTIVE = "ACTIVE"
    NEW = "NEW"


class PlaceState(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class AuditEntity(StrEnum):
    CAMPAIGN = "CAMPAIGN"
    BANNER = "BANNER"
    CONTENT = "CONTENT"
    CREATIVE = "CREATIVE"
    SEGMENTS = "SEGMENTS"
    PLACE = "PLACE"
    TAG = "TAG"


class AuditAction(StrEnum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    TO_MODERATION = "TO_MODERATION"
    DECLINE = "DECLINE"
    APPROVE = "APPROVE"
    ACTIVATE = "ACTIVATE"
    STOP = "STOP"
