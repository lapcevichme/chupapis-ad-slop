from typing import Any

from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.core.config import Settings
from app.infra.agent.designer import Designer
from app.infra.agent.graph import AgentDeps, build_graph
from app.infra.campaigns_api import ApiFactory, CampaignsApi
from app.infra.llm import ImageGenerator, chat_model, image_generator
from app.service.chat import ChatService
from app.service.chat_sessions import SessionRegistry


def build_chat_service(
    checkpointer: BaseCheckpointSaver[Any],
    settings: Settings,
    sessions: SessionRegistry,
    *,
    chat: BaseChatModel | None = None,
    design: BaseChatModel | None = None,
    images: ImageGenerator | None = None,
    api_factory: ApiFactory | None = None,
) -> ChatService:
    def default_factory(user: str, role: str) -> CampaignsApi:
        return CampaignsApi(user, role, base_url=settings.campaigns_api_url)

    resolved_factory = api_factory or default_factory
    deps = AgentDeps(
        chat_model=chat or chat_model(settings, settings.chat_model),
        designer=Designer(
            design or chat_model(settings, settings.design_model, temperature=0.7),
            images or image_generator(settings),
            cache_enabled=settings.llm_prompt_cache,
        ),
        api_factory=resolved_factory,
        cache_enabled=settings.llm_prompt_cache,
    )
    return ChatService(build_graph(deps, checkpointer), resolved_factory, sessions)
