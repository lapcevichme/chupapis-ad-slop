from fastapi import APIRouter, Response

from app.api.deps import ERROR_RESPONSES, ActorDep, CreativeServiceDep
from app.contracts import campaigns as api

router = APIRouter(prefix="/campaigns/{campaign_id}", tags=["creatives"], responses=ERROR_RESPONSES)


@router.post("/banners", response_model=api.BannerDto, status_code=201)
async def create_banner(
    campaign_id: int, body: api.BannerCreate, actor: ActorDep, service: CreativeServiceDep
) -> api.BannerDto:
    return api.BannerDto.from_domain(await service.create_banner(campaign_id, body, actor))


@router.put("/banners/{banner_id}", response_model=api.BannerDto)
async def update_banner(
    campaign_id: int,
    banner_id: int,
    body: api.BannerCreate,
    actor: ActorDep,
    service: CreativeServiceDep,
) -> api.BannerDto:
    return api.BannerDto.from_domain(
        await service.update_banner(campaign_id, banner_id, body, actor)
    )


@router.delete("/banners/{banner_id}", status_code=204)
async def delete_banner(
    campaign_id: int, banner_id: int, actor: ActorDep, service: CreativeServiceDep
) -> Response:
    await service.delete_banner(campaign_id, banner_id, actor)
    return Response(status_code=204)


@router.post("/contents", response_model=api.ContentDto, status_code=201)
async def create_content(
    campaign_id: int, body: api.ContentCreate, actor: ActorDep, service: CreativeServiceDep
) -> api.ContentDto:
    return api.ContentDto.from_domain(await service.create_content(campaign_id, body, actor))


@router.put("/contents/{content_id}", response_model=api.ContentDto)
async def update_content(
    campaign_id: int,
    content_id: int,
    body: api.ContentCreate,
    actor: ActorDep,
    service: CreativeServiceDep,
) -> api.ContentDto:
    return api.ContentDto.from_domain(
        await service.update_content(campaign_id, content_id, body, actor)
    )


@router.delete("/contents/{content_id}", status_code=204)
async def delete_content(
    campaign_id: int, content_id: int, actor: ActorDep, service: CreativeServiceDep
) -> Response:
    await service.delete_content(campaign_id, content_id, actor)
    return Response(status_code=204)


@router.post("/creatives", response_model=api.CreativeDto, status_code=201)
async def create_creative(
    campaign_id: int, body: api.CreativeCreate, actor: ActorDep, service: CreativeServiceDep
) -> api.CreativeDto:
    return api.CreativeDto.from_domain(await service.create_creative(campaign_id, body, actor))


@router.put("/creatives/{creative_id}", response_model=api.CreativeDto)
async def update_creative(
    campaign_id: int,
    creative_id: int,
    body: api.CreativeCreate,
    actor: ActorDep,
    service: CreativeServiceDep,
) -> api.CreativeDto:
    return api.CreativeDto.from_domain(
        await service.update_creative(campaign_id, creative_id, body, actor)
    )


@router.delete("/creatives/{creative_id}", status_code=204)
async def delete_creative(
    campaign_id: int, creative_id: int, actor: ActorDep, service: CreativeServiceDep
) -> Response:
    await service.delete_creative(campaign_id, creative_id, actor)
    return Response(status_code=204)
