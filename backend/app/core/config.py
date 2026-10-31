from pathlib import Path
from typing import Literal

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
    # Фото от менеджера. Клиент сжимает его сам, сервер только не пускает лишнее и не даёт забить том.
    media_upload_max_bytes: int = 5 * 1024 * 1024
    media_upload_max_total_bytes: int = 300 * 1024 * 1024
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
    # Фон-паттерн в SVG: тема передаётся цветом. Дешёвая альтернатива иллюстрации и её запасной вариант.
    pattern_model: str = "anthropic/claude-haiku-5.5"
    # mixed — фон сторис и смарт-баннера паттерном, картинка промо-экрана иллюстрацией; ask — агент спрашивает кнопками,
    # что нужно; pattern или illustration — только этот вид.
    image_mode: Literal["mixed", "ask", "pattern", "illustration"] = "mixed"
    llm_timeout_seconds: float = 90.0
    # Провайдеры OpenRouter в порядке приоритета, через запятую. Кеш промпта живёт у конкретного провайдера:
    # без фиксации OpenRouter раскидывает запросы по разным и кеш не попадает. Пустая строка — выбор OpenRouter.
    llm_providers: str = "anthropic"
    # Точки кеша Anthropic (cache_control) в запросах чат- и дизайн-агента.
    llm_prompt_cache: bool = True
    # Распознавание речи через {llm_base_url}/audio/transcriptions. Пустая строка выключает диктовку.
    stt_model: str = "openai/whisper-large-v3"
    # Код языка ISO-639-1. С явным языком Whisper не ошибается в определении на коротких фразах.
    stt_language: str = "ru"
    # Озвучка через {llm_base_url}/audio/speech. Нужна модель, отдающая MP3. Пустая строка выключает её.
    tts_model: str = "elevenlabs/eleven-flash-v2.5"
    tts_voice: str = "sarah"
    # Платим за символ, поэтому длину реплики ограничивает сервер.
    tts_max_chars: int = 1000
    speech_timeout_seconds: float = 30.0
    stt_max_audio_bytes: int = 5 * 1024 * 1024
    # Голосовой режим на GPT-Live. Модели нет в OpenRouter, нужен свой ключ OpenAI; без него режим работает как раньше.
    openai_api_key: str = ""
    live_base_url: str = "https://api.openai.com/v1"
    live_model: str = "gpt-live-1"
    live_voice: str = "marin"
    # Агент ходит в API кампаний по HTTP, поэтому заглушку можно заменить реальным бэкендом.
    campaigns_api_url: str = "http://localhost:8000"
    checkpoint_db: Path = BACKEND_DIR / "data" / "checkpoints.db"
