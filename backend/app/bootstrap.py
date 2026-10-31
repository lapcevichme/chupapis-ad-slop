from typing import Any

from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.core.config import Settings
from app.infra.agent.designer import Designer
from app.infra.agent.graph import AgentDeps, build_graph
from app.infra.agent.patterns import SvgPatternGenerator
from app.infra.campaigns_api import ApiFactory, CampaignsApi
from app.infra.llm import ImageGenerator, chat_model, image_generator
from app.infra.speech import speech_transcriber
from app.service.chat import ChatService
from app.service.chat_sessions import SessionRegistry
from app.service.speech import SpeechService


def build_speech_service(settings: Settings) -> SpeechService:
    return SpeechService(speech_transcriber(settings), max_audio_bytes=settings.stt_max_audio_bytes)


def build_chat_service(
    checkpointer: BaseCheckpointSaver[Any],
    settings: Settings,
    sessions: SessionRegistry,
    *,
    chat: BaseChatModel | None = None,
    design: BaseChatModel | None = None,
    images: ImageGenerator | None = None,
    patterns: SvgPatternGenerator | None = None,
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
            # Без ключа паттерны не нужны: тесты подставляют свой генератор или работают без него.
            patterns
            or (
                SvgPatternGenerator(
                    chat_model(settings, settings.pattern_model, temperature=0.8, max_tokens=2000),
                    media_dir=settings.media_dir,
                    media_base_url=settings.media_base_url,
                )
                if settings.llm_api_key
                else None
            ),
            cache_enabled=settings.llm_prompt_cache,
            media_base_url=settings.media_base_url,
        ),
        api_factory=resolved_factory,
        cache_enabled=settings.llm_prompt_cache,
        image_mode=settings.image_mode,
    )
    return ChatService(build_graph(deps, checkpointer), resolved_factory, sessions)
