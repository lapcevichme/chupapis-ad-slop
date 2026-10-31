from fastapi import APIRouter

from app.api.system import router as system_router
from app.api.v1 import campaigns, cbro, chat, children, dictionaries, speech

api_router = APIRouter()
for router in (
    dictionaries.router,
    campaigns.router,
    children.router,
    cbro.router,
    chat.router,
    speech.router,
):
    api_router.include_router(router)

api_router.include_router(system_router)
