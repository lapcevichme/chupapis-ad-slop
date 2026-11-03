from fastapi import APIRouter, UploadFile
from fastapi.responses import Response

from app.api.deps import ERROR_RESPONSES, CurrentUserDep, MediaServiceDep
from app.contracts.media import UploadedImage
from app.core.errors import fail

router = APIRouter(prefix="/media", tags=["media"], responses=ERROR_RESPONSES)


@router.post("/images", response_model=UploadedImage, status_code=201)
async def upload_image(
    file: UploadFile, media: MediaServiceDep, user: CurrentUserDep
) -> UploadedImage:
    # Размер проверяем до чтения в память.
    if file.size is not None and file.size > media.max_bytes:
        raise fail("IMAGE_TOO_LARGE", "file")
    return UploadedImage(url=await media.upload_image(await file.read(), user))


@router.get(
    "/{key}",
    summary="Файл из хранилища",
    # Без авторизации: ссылки вставляются в <img>, а JSON баннера уходит за пределы приложения.
    # Имена случайные и неизменные, поэтому кеш вечный.
    responses={200: {"content": {"image/*": {}}}},
    response_class=Response,
)
async def get_media(key: str, media: MediaServiceDep) -> Response:
    data, content_type = await media.read(key)
    return Response(
        data,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
