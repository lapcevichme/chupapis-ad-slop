from fastapi import APIRouter

from app.api.deps import ERROR_RESPONSES, ActorDep, DictionaryServiceDep
from app.contracts import campaigns as api

router = APIRouter(prefix="", tags=["dictionaries"], responses=ERROR_RESPONSES)


@router.get("/topics", response_model=list[api.TopicDto])
async def list_topics(service: DictionaryServiceDep) -> list[api.TopicDto]:
    return [api.TopicDto.from_domain(value) for value in await service.list_topics()]


@router.get("/tags", response_model=list[api.TagDto])
async def list_tags(service: DictionaryServiceDep) -> list[api.TagDto]:
    return [api.TagDto.from_domain(value) for value in await service.list_tags()]


@router.get("/channels", response_model=list[api.ChannelDto])
async def list_channels(service: DictionaryServiceDep) -> list[api.ChannelDto]:
    return [api.ChannelDto.from_domain(value) for value in await service.list_channels()]


@router.get("/banner-types", response_model=list[api.BannerTypeDto])
async def list_banner_types(service: DictionaryServiceDep) -> list[api.BannerTypeDto]:
    return [api.BannerTypeDto.from_domain(value) for value in await service.list_banner_types()]


@router.get("/segment-types", response_model=list[api.SegmentTypeDto])
async def list_segment_types(service: DictionaryServiceDep) -> list[api.SegmentTypeDto]:
    return [api.SegmentTypeDto.from_domain(value) for value in await service.list_segment_types()]


@router.get("/segments", response_model=list[api.SegmentDto])
async def list_segments(service: DictionaryServiceDep) -> list[api.SegmentDto]:
    return [api.SegmentDto.from_domain(value) for value in await service.list_segments()]


@router.get("/places", response_model=list[api.PlaceDto])
async def list_places(service: DictionaryServiceDep) -> list[api.PlaceDto]:
    return [api.PlaceDto.from_domain(value) for value in await service.list_places()]


@router.post("/places", response_model=api.PlaceDto, status_code=201)
async def create_place(
    body: api.PlaceCreate, actor: ActorDep, service: DictionaryServiceDep
) -> api.PlaceDto:
    return api.PlaceDto.from_domain(await service.create_place(body, actor))


@router.post("/tags", response_model=api.TagDto, status_code=201)
async def create_tag(
    body: api.TagCreate, actor: ActorDep, service: DictionaryServiceDep
) -> api.TagDto:
    return api.TagDto.from_domain(await service.create_tag(body, actor))
