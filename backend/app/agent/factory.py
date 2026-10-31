from langchain_core.language_models import BaseChatModel

from app.agent.designer import Designer
from app.agent.graph import AgentDeps, build_graph
from app.agent.llm import ImageGenerator, chat_model, image_generator
from app.agent.patterns import SvgPatternGenerator
from app.agent.service import ChatService, default_api_factory
from app.config import settings


def build_chat_service(
    checkpointer,
    *,
    chat: BaseChatModel | None = None,
    design: BaseChatModel | None = None,
    images: ImageGenerator | None = None,
    patterns: SvgPatternGenerator | None = None,
    api_factory=default_api_factory,
) -> ChatService:
    """Модели по умолчанию берутся из конфига; тесты подставляют свои."""
    deps = AgentDeps(
        chat_model=chat or chat_model(settings.chat_model),
        designer=Designer(
            design or chat_model(settings.design_model, temperature=0.7),
            images or image_generator(),
            # Без ключа паттерны не нужны: тесты подставляют свой генератор или работают без него.
            patterns or (SvgPatternGenerator(chat_model(settings.pattern_model, temperature=0.8, max_tokens=2000)) if settings.llm_api_key else None),
        ),
        api_factory=api_factory,
    )
    return ChatService(build_graph(deps, checkpointer), api_factory)
