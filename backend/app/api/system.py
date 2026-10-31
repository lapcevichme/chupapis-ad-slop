from fastapi import APIRouter

router = APIRouter(tags=["service"])


@router.get("/health", response_model=None)
def health() -> dict[str, str]:
    return {"status": "ok"}
