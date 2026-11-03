from typing import Annotated

from fastapi import APIRouter, Form, Path, UploadFile
from pydantic import ValidationError

from app.api.deps import ERROR_RESPONSES, CurrentUserDep, StudioServiceDep
from app.contracts.studio import (
    StoredStudioDocument,
    StudioDocument,
    StudioGenerationBody,
    StudioGenerationResult,
)
from app.core.errors import fail

router = APIRouter(prefix="/studio", tags=["studio"], responses=ERROR_RESPONSES)


@router.post("/documents", response_model=StoredStudioDocument, status_code=201)
async def save_studio_document(
    document: Annotated[str, Form(max_length=100000)],
    file: UploadFile,
    studio: StudioServiceDep,
    user: CurrentUserDep,
) -> StoredStudioDocument:
    if file.size is not None and file.size > studio.max_bytes:
        raise fail("IMAGE_TOO_LARGE", "file")
    try:
        parsed = StudioDocument.model_validate_json(document)
    except ValidationError as exc:
        raise fail("STUDIO_DOCUMENT_INVALID", "document", str(exc.errors()[0]["msg"])) from exc
    return await studio.save(parsed, await file.read(), user)


@router.get("/documents/{key}", response_model=StudioDocument)
async def get_studio_document(
    key: Annotated[str, Path(pattern=r"^[0-9a-f]{32}$")],
    studio: StudioServiceDep,
    _user: CurrentUserDep,
) -> StudioDocument:
    return await studio.get(key)


@router.post("/generate", response_model=StudioGenerationResult)
async def generate_studio_variants(
    body: StudioGenerationBody,
    studio: StudioServiceDep,
    user: CurrentUserDep,
) -> StudioGenerationResult:
    return await studio.generate(body, user)
