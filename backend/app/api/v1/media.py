from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile

from app.api.deps import ERROR_RESPONSES, ActorDep, SettingsDep
from app.contracts.media import UploadedImage
from app.core.errors import fail
from app.infra.media_storage import MediaStorage
from app.service.media import MediaService

router = APIRouter(prefix="/media", tags=["media"], responses=ERROR_RESPONSES)


def media_service(config: SettingsDep) -> MediaService:
    return MediaService(
        MediaStorage(config.media_dir, config.media_base_url),
        max_bytes=config.media_upload_max_bytes,
        max_total_bytes=config.media_upload_max_total_bytes,
    )


MediaDep = Annotated[MediaService, Depends(media_service)]


@router.post("/images", response_model=UploadedImage, status_code=201)
async def upload_image(file: UploadFile, media: MediaDep, actor: ActorDep) -> UploadedImage:
    # Размер проверяем до чтения в память.
    if file.size is not None and file.size > media.max_bytes:
        raise fail("IMAGE_TOO_LARGE", "file")
    return UploadedImage(url=await media.upload_image(await file.read(), actor))
