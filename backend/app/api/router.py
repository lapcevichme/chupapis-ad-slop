from fastapi import APIRouter

from app.api.system import router as system_router
from app.api.v1 import (
    admin,
    auth,
    campaigns,
    cbro,
    chat,
    children,
    dictionaries,
    me,
    media,
    speech,
    studio,
)

api_router = APIRouter()
for router in (
    auth.router,
    me.router,
    admin.router,
    dictionaries.router,
    campaigns.router,
    children.router,
    cbro.router,
    chat.router,
    speech.router,
    media.router,
    studio.router,
):
    api_router.include_router(router)

api_router.include_router(system_router)
