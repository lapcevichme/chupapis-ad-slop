from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # Один .env в корне репо: его читают и локальный запуск, и Docker Compose.
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR.parent / ".env", BACKEND_DIR / ".env"), extra="ignore"
    )

    database_url: str = f"sqlite:///{(BACKEND_DIR / 'data' / 'adpilot.db').as_posix()}"
    seed_dir: Path = BACKEND_DIR / "seed"
    media_dir: Path = BACKEND_DIR / "data" / "media"
    # Картинки, которые раздаёт сам бэкенд. Валидатор баннера принимает их наравне с https-ссылками.
    media_base_url: str = "/api/media"
    cors_origins: list[str] = ["http://localhost:5173"]

    log_level: str = "INFO"
    log_json: bool = False

    # --- Агент
    # Любой OpenAI-совместимый провайдер; по умолчанию OpenRouter.
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_api_key: str = ""
    # Ведёт диалог и вызывает инструменты: нужен надёжный tool calling и быстрый ответ.
    chat_model: str = "anthropic/claude-haiku-5.5"
    # Собирает JSON баннера и контента и пишет тексты: важнее качество, чем скорость.
    design_model: str = "anthropic/claude-sonnet-5.5"
    # Генерация картинок для баннера. Пустая строка выключает генерацию.
    image_model: str = "openai/gpt-image-2.5-sunburst"
    llm_timeout_seconds: float = 90.0
    # Провайдеры OpenRouter в порядке приоритета, через запятую. Кеш промпта живёт у конкретного провайдера:
    # без фиксации OpenRouter раскидывает запросы по разным и кеш не попадает. Пустая строка — выбор OpenRouter.
    llm_providers: str = "anthropic"
    # Точки кеша Anthropic (cache_control) в запросах чат- и дизайн-агента.
    llm_prompt_cache: bool = True
    # Агент ходит в API кампаний по HTTP, поэтому заглушку можно заменить реальным бэкендом.
    campaigns_api_url: str = "http://localhost:8000"
    checkpoint_db: Path = BACKEND_DIR / "data" / "checkpoints.db"
