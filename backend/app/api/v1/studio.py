from typing import Annotated

from fastapi import APIRouter, Depends, Form, Path, Request, UploadFile
from pydantic import ValidationError

from app.api.deps import ERROR_RESPONSES, ActorDep, SettingsDep
from app.contracts.studio import (
    StoredStudioDocument,
    StudioDocument,
    StudioGenerationBody,
    StudioGenerationResult,
)
from app.core.errors import fail
from app.infra.studio_storage import StudioStorage
from app.service.studio import StudioService

router = APIRouter(prefix="/studio", tags=["studio"], responses=ERROR_RESPONSES)


def studio_service(config: SettingsDep, request: Request) -> StudioService:
    return StudioService(
        StudioStorage(config.media_dir, config.media_base_url),
        max_bytes=config.media_upload_max_bytes,
        max_total_bytes=config.media_upload_max_total_bytes,
        generator=request.app.state.studio_designer,
    )


StudioDep = Annotated[StudioService, Depends(studio_service)]


@router.post("/documents", response_model=StoredStudioDocument, status_code=201)
async def save_studio_document(
    document: Annotated[str, Form(max_length=100000)],
    file: UploadFile,
    studio: StudioDep,
    actor: ActorDep,
) -> StoredStudioDocument:
    if file.size is not None and file.size > studio.max_bytes:
        raise fail("IMAGE_TOO_LARGE", "file")
    try:
        parsed = StudioDocument.model_validate_json(document)
    except ValidationError as exc:
        raise fail("STUDIO_DOCUMENT_INVALID", "document", str(exc.errors()[0]["msg"])) from exc
    return await studio.save(parsed, await file.read(), actor)


@router.get("/documents/{key}", response_model=StudioDocument)
async def get_studio_document(
    key: Annotated[str, Path(pattern=r"^[0-9a-f]{32}$")],
    studio: StudioDep,
    actor: ActorDep,
) -> StudioDocument:
    return await studio.get(key)


@router.post("/generate", response_model=StudioGenerationResult)
async def generate_studio_variants(
    body: StudioGenerationBody,
    studio: StudioDep,
    actor: ActorDep,
) -> StudioGenerationResult:
    return await studio.generate(body, actor)
