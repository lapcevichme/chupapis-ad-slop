from langchain_core.language_models import BaseChatModel

from app.agent.designer import Designer
from app.agent.graph import AgentDeps, build_graph
from app.agent.llm import ImageGenerator, chat_model, image_generator
from app.agent.service import ChatService, default_api_factory
from app.config import settings


def build_chat_service(
    checkpointer,
    *,
    chat: BaseChatModel | None = None,
    design: BaseChatModel | None = None,
    images: ImageGenerator | None = None,
    api_factory=default_api_factory,
) -> ChatService:
    """Модели по умолчанию берутся из конфига; тесты подставляют свои."""
    deps = AgentDeps(
        chat_model=chat or chat_model(settings.chat_model),
        designer=Designer(design or chat_model(settings.design_model, temperature=0.7), images or image_generator()),
        api_factory=api_factory,
    )
    return ChatService(build_graph(deps, checkpointer), api_factory)
