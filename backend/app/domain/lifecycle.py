from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from app.core.codes import ERRORS
from app.core.errors import fail
from app.domain.enums import AuditAction, CampaignState
from app.domain.users import Permission


class Editor(Protocol):
    id: UUID


class Campaign(Protocol):
    state: CampaignState
    published: bool
    last_editor: Any


S = CampaignState

EDITABLE_STATES = {S.DRAFT, S.NEEDS_WORK, S.APPROVED, S.ACTIVE, S.ACTIVE_EDITING}
DELETABLE_STATES = {S.DRAFT, S.NEEDS_WORK}


def ensure_editable(campaign: Campaign) -> None:
    if campaign.state not in EDITABLE_STATES:
        raise fail(
            "UPDATE_NOT_ALLOWED",
            message=f"Кампанию в состоянии {campaign.state} нельзя редактировать",
        )


def mark_edited(campaign: Campaign, editor: Editor) -> None:
    """Правка снимает одобрение (APPROVED → DRAFT), а у живой кампании открывает ACTIVE_EDITING."""
    if campaign.state == S.APPROVED:
        campaign.state = S.DRAFT
    elif campaign.state in {S.ACTIVE, S.ACTIVE_EDITING}:
        campaign.state = S.ACTIVE_EDITING
    campaign.last_editor = editor


@dataclass(frozen=True)
class Transition:
    action: AuditAction
    permission: Permission
    from_states: frozenset[CampaignState]
    to_state: CampaignState
    error_code: str


TRANSITIONS: dict[AuditAction, Transition] = {
    t.action: t
    for t in [
        Transition(
            AuditAction.TO_MODERATION,
            Permission.CAMPAIGNS_WRITE,
            frozenset({S.DRAFT, S.NEEDS_WORK, S.ACTIVE_EDITING}),
            S.ON_MODERATION,
            "TO_MODERATION_NOT_ALLOWED",
        ),
        Transition(
            AuditAction.DECLINE,
            Permission.CAMPAIGNS_MODERATE,
            frozenset({S.ON_MODERATION}),
            S.NEEDS_WORK,
            "DECLINE_NOT_ALLOWED",
        ),
        Transition(
            AuditAction.APPROVE,
            Permission.CAMPAIGNS_MODERATE,
            frozenset({S.ON_MODERATION}),
            S.APPROVED,
            "APPROVE_NOT_ALLOWED",
        ),
        Transition(
            AuditAction.ACTIVATE,
            Permission.CAMPAIGNS_WRITE,
            frozenset({S.APPROVED}),
            S.ACTIVE,
            "ACTIVATE_NOT_ALLOWED",
        ),
    ]
}


def ensure_transition(campaign: Campaign, action: AuditAction) -> Transition:
    transition = TRANSITIONS[action]
    if campaign.state not in transition.from_states:
        raise fail(
            transition.error_code,
            message=f"{ERRORS[transition.error_code]}; сейчас {campaign.state}",
        )
    return transition


def ensure_stoppable(campaign: Campaign) -> None:
    if not campaign.published:
        raise fail("STOP_NOT_ALLOWED")


def ensure_deletable(campaign: Campaign) -> None:
    if campaign.state not in DELETABLE_STATES or campaign.published:
        raise fail(
            "DELETE_NOT_ALLOWED",
            message=f"Удалить можно только неопубликованную кампанию в DRAFT или NEEDS_WORK; сейчас {campaign.state}, published={str(campaign.published).lower()}",
        )
