from langchain_core.language_models import BaseChatModel

from app.agent.api_client import CampaignsApi
from app.agent.designer import Designer
from app.agent.graph import AgentDeps, build_graph
from app.agent.llm import ImageGenerator, chat_model, image_generator
from app.agent.service import ChatService
from app.agent.sessions import SessionRegistry
from app.core.config import Settings


def build_chat_service(
    checkpointer,
    settings: Settings,
    sessions: SessionRegistry,
    *,
    chat: BaseChatModel | None = None,
    design: BaseChatModel | None = None,
    images: ImageGenerator | None = None,
    api_factory=None,
) -> ChatService:
    if api_factory is None:
        def api_factory(user: str, role: str) -> CampaignsApi:
            return CampaignsApi(user, role, base_url=settings.campaigns_api_url)

    deps = AgentDeps(
        chat_model=chat or chat_model(settings, settings.chat_model),
        designer=Designer(
            design or chat_model(settings, settings.design_model, temperature=0.7),
            images or image_generator(settings),
            cache_enabled=settings.llm_prompt_cache,
        ),
        api_factory=api_factory,
        cache_enabled=settings.llm_prompt_cache,
    )
    return ChatService(build_graph(deps, checkpointer), api_factory, sessions)
