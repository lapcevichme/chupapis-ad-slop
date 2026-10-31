from fastapi import APIRouter, Response

from app.api.deps import ERROR_RESPONSES, ActorDep, UowDep
from app.contracts import campaigns as api
from app.service.campaigns import CampaignService

router = APIRouter(prefix="/campaigns", tags=["campaigns"], responses=ERROR_RESPONSES)


@router.get("", response_model=list[api.CampaignListItem])
async def list_campaigns(uow: UowDep) -> list[api.CampaignListItem]:
    return [
        api.CampaignListItem.from_domain(value)
        for value in await CampaignService(uow).list_campaigns()
    ]


@router.get("/{campaign_id}", response_model=api.CampaignDetails)
async def get_campaign_details(campaign_id: int, uow: UowDep) -> api.CampaignDetails:
    return api.CampaignDetails.from_domain(
        await CampaignService(uow).get_campaign_details(campaign_id)
    )


@router.post("", response_model=api.CampaignRef, status_code=201)
async def create_campaign(body: api.CampaignInfo, actor: ActorDep, uow: UowDep) -> api.CampaignRef:
    return api.CampaignRef.from_domain(await CampaignService(uow).create_campaign(body, actor))


@router.put("/{campaign_id}", response_model=api.CampaignRef)
async def update_campaign(
    campaign_id: int, body: api.CampaignInfo, actor: ActorDep, uow: UowDep
) -> api.CampaignRef:
    return api.CampaignRef.from_domain(
        await CampaignService(uow).update_campaign(campaign_id, body, actor)
    )


@router.delete("/{campaign_id}", status_code=204)
async def delete_campaign(campaign_id: int, actor: ActorDep, uow: UowDep) -> Response:
    await CampaignService(uow).delete_campaign(campaign_id, actor)
    return Response(status_code=204)


@router.put("/{campaign_id}/segments", response_model=api.Segments)
async def set_segments(
    campaign_id: int, body: api.Segments, actor: ActorDep, uow: UowDep
) -> api.Segments:
    return api.Segments.from_domain(
        await CampaignService(uow).set_segments(campaign_id, body, actor)
    )


@router.get("/{campaign_id}/warnings", response_model=api.ValidationReport)
async def get_warnings(campaign_id: int, uow: UowDep) -> api.ValidationReport:
    return api.ValidationReport.from_domain(await CampaignService(uow).get_warnings(campaign_id))


@router.get("/{campaign_id}/audit", response_model=list[api.AuditRecord])
async def get_audit(campaign_id: int, uow: UowDep) -> list[api.AuditRecord]:
    return [
        api.AuditRecord.from_domain(value)
        for value in await CampaignService(uow).get_audit(campaign_id)
    ]


@router.post("/{campaign_id}/to-moderation", response_model=api.CampaignRef)
async def send_to_moderation(campaign_id: int, actor: ActorDep, uow: UowDep) -> api.CampaignRef:
    return api.CampaignRef.from_domain(
        await CampaignService(uow).send_to_moderation(campaign_id, actor)
    )


@router.post("/{campaign_id}/decline", response_model=api.CampaignRef)
async def decline_campaign(
    campaign_id: int, body: api.DeclineBody, actor: ActorDep, uow: UowDep
) -> api.CampaignRef:
    return api.CampaignRef.from_domain(
        await CampaignService(uow).decline_campaign(campaign_id, body, actor)
    )


@router.post("/{campaign_id}/approve", response_model=api.CampaignRef)
async def approve_campaign(campaign_id: int, actor: ActorDep, uow: UowDep) -> api.CampaignRef:
    return api.CampaignRef.from_domain(
        await CampaignService(uow).approve_campaign(campaign_id, actor)
    )


@router.post("/{campaign_id}/activate", response_model=api.CampaignRef)
async def activate_campaign(campaign_id: int, actor: ActorDep, uow: UowDep) -> api.CampaignRef:
    return api.CampaignRef.from_domain(
        await CampaignService(uow).activate_campaign(campaign_id, actor)
    )


@router.post("/{campaign_id}/stop", response_model=api.CampaignRef)
async def stop_campaign(campaign_id: int, actor: ActorDep, uow: UowDep) -> api.CampaignRef:
    return api.CampaignRef.from_domain(await CampaignService(uow).stop_campaign(campaign_id, actor))
