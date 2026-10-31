from fastapi import APIRouter

from app.api.v1 import campaigns, cbro, chat, children, dictionaries

api_router = APIRouter()
for router in (dictionaries.router, campaigns.router, children.router, cbro.router, chat.router):
    api_router.include_router(router)
