import asyncio
import logging
from collections.abc import Awaitable
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.deps import DatabaseDep, RedisDep, StorageDep

logger = logging.getLogger(__name__)

router = APIRouter(tags=["service"])

_CHECK_TIMEOUT_SEC = 2.0


@router.get("/health", summary="Liveness: процесс жив, зависимости не трогаем")
async def health() -> dict[str, str]:
    return {"status": "ok"}


async def _check(name: str, probe: Awaitable[Any]) -> tuple[str, bool]:
    try:
        await asyncio.wait_for(probe, timeout=_CHECK_TIMEOUT_SEC)
    except Exception:  # проба готовности сообщает о любом сбое, а не пробрасывает его
        logger.warning("readiness check %s failed", name, exc_info=True)
        return name, False
    return name, True


@router.get(
    "/ready",
    summary="Readiness: Postgres, Redis и хранилище отвечают",
    responses={503: {"description": "Зависимость недоступна"}},
)
async def ready(db: DatabaseDep, redis: RedisDep, storage: StorageDep) -> JSONResponse:
    results = await asyncio.gather(
        _check("database", db.ping()),
        _check("redis", redis.ping()),
        _check("storage", storage.ping()),
    )
    checks = {name: "ok" if ok else "error" for name, ok in results}
    healthy = all(ok for _, ok in results)
    return JSONResponse(
        {"status": "ready" if healthy else "not_ready", "checks": checks},
        status_code=200 if healthy else 503,
    )
