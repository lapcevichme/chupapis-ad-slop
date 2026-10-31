from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # Один .env в корне репо: его читают и локальный запуск, и Docker Compose.
    model_config = SettingsConfigDict(env_file=(BACKEND_DIR.parent / ".env", BACKEND_DIR / ".env"), extra="ignore")

    database_url: str = f"sqlite:///{(BACKEND_DIR / 'data' / 'adpilot.db').as_posix()}"
    seed_dir: Path = BACKEND_DIR / "seed"
    media_dir: Path = BACKEND_DIR / "data" / "media"
    # Картинки, которые раздаёт сам бэкенд. Валидатор баннера принимает их наравне с https-ссылками.
    media_base_url: str = "/api/media"
    cors_origins: list[str] = ["http://localhost:5173"]

    # --- Агент
    # Любой OpenAI-совместимый провайдер; по умолчанию OpenRouter.
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_api_key: str = ""
    # Ведёт диалог и вызывает инструменты: нужен надёжный tool calling и быстрый ответ.
    chat_model: str = "anthropic/claude-haiku-5.5"
    # Собирает JSON баннера и контента и пишет тексты: важнее качество, чем скорость.
    design_model: str = "anthropic/claude-sonnet-5.5"
    # Генерация картинок для баннера. Пустая строка выключает генерацию.
    image_model: str = "google/gemini-nano-banana-2.1"
    llm_timeout_seconds: float = 90.0
    # Агент ходит в API кампаний по HTTP, поэтому заглушку можно заменить реальным бэкендом.
    campaigns_api_url: str = "http://localhost:8000"
    checkpoint_db: Path = BACKEND_DIR / "data" / "checkpoints.db"


settings = Settings()
