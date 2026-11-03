from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]

DEV_CSRF_KEY = "change-me"
DEV_STORAGE_SECRET = "rustfsadmin"  # публичный пароль RustFS из compose, в prod запрещён
DEV_DATABASE_PASSWORD = "adpilot"  # пароль Postgres из compose, в prod запрещён


class Settings(BaseSettings):
    """Все настройки читаются один раз при старте и передаются явно: при импорте Settings() не зовёт никто."""

    # Один .env в корне репо: его читают и локальный запуск, и Docker Compose.
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR.parent / ".env", BACKEND_DIR / ".env"), extra="ignore"
    )

    # --- Окружение и диагностика
    app_stage: Literal["dev", "test", "prod"] = "dev"
    debug: bool = False
    log_level: str = "INFO"
    log_json: bool = False
    sql_echo: bool = False
    api_docs_enabled: bool | None = None
    cors_origins: list[str] = ["http://localhost:5173"]
    rate_limit_enabled: bool = True
    auth_rate_limit_per_minute: int = 10

    # --- Postgres и Redis
    database_url: str = "postgresql+asyncpg://adpilot:adpilot@localhost:5432/adpilot"
    db_pool_size: int = 10
    db_max_overflow: int = 10
    redis_url: str = "redis://localhost:6379/0"

    # --- Авторизация
    jwt_private_key: SecretStr | None = None
    jwt_public_key: str | None = None
    jwt_private_key_path: Path | None = BACKEND_DIR / "secrets" / "jwt_private_key.pem"
    jwt_public_key_path: Path | None = BACKEND_DIR / "secrets" / "jwt_public_key.pem"
    jwt_algo: str = "RS256"
    access_ttl: int = 15 * 60
    refresh_ttl: int = 30 * 24 * 60 * 60
    csrf_hmac_key: SecretStr = SecretStr(DEV_CSRF_KEY)
    # Открытая регистрация создаёт менеджера. Модераторов и админов заводит CLI или админ.
    registration_enabled: bool = True

    # --- Cookie. Браузер видит API под /api (прокси фронтенда), поэтому путь refresh-cookie такой же.
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cookie_domain: str | None = None
    refresh_cookie_path: str = "/api/auth"

    # --- S3-совместимое хранилище медиа (RustFS локально; AWS S3, R2 и т. п. в проде)
    storage_endpoint: str = "http://localhost:9000"
    storage_region: str = "us-east-1"
    storage_access_key: str = "rustfsadmin"
    storage_secret_key: SecretStr = SecretStr(DEV_STORAGE_SECRET)
    storage_bucket: str = "adpilot-media"
    storage_use_path_style: bool = True
    storage_auto_create_bucket: bool = True
    # Картинки раздаёт сам бэкенд по этому префиксу: бакет остаётся закрытым.
    media_base_url: str = "/api/media"
    # Фото от менеджера. Клиент сжимает его сам, сервер только не пускает лишнее и не даёт забить хранилище.
    media_upload_max_bytes: int = 5 * 1024 * 1024
    media_upload_max_total_bytes: int = 300 * 1024 * 1024

    # --- Уведомления (доставляет воркер через outbox)
    notifications_provider: Literal["log", "telegram"] = "log"
    telegram_bot_token: SecretStr = SecretStr("")
    telegram_chat_id: str = ""

    # --- Фоновый воркер
    outbox_batch_size: int = 20
    outbox_poll_interval_sec: float = 1.0
    outbox_max_attempts: int = 8

    # --- Данные
    seed_dir: Path = BACKEND_DIR / "seed"
    # Демо-пользователи (менеджер и модератор из кейса) создаются сидом только с этим паролем.
    demo_users_password: SecretStr | None = None

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
    image_mode: Literal["mixed", "ask", "pattern", "illustration"] = "illustration"
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
    # Legacy: озвучка запасного голосового режима через {llm_base_url}/audio/speech.
    # Нужна модель, отдающая MP3. Пустая строка выключает её.
    tts_model: str = "elevenlabs/eleven-flash-v2.5"
    tts_voice: str = "sarah"
    # Платим за символ, поэтому длину реплики ограничивает сервер.
    tts_max_chars: int = 1000
    speech_timeout_seconds: float = 30.0
    stt_max_audio_bytes: int = 5 * 1024 * 1024
    # Основной голосовой режим. GPT-Live нет в OpenRouter, нужен свой ключ OpenAI; без него запасная legacy-схема.
    openai_api_key: str = ""
    live_base_url: str = "https://api.openai.com/v1"
    live_model: str = "gpt-live-1"
    # Имя встроенного голоса или id созданного: среди встроенных нет русских, см. app.create_live_voice.
    live_voice: str = "marin"
    # Агент ходит в API кампаний по HTTP, поэтому заглушку можно заменить реальным бэкендом.
    campaigns_api_url: str = "http://localhost:8000"

    @property
    def show_api_docs(self) -> bool:
        if self.api_docs_enabled is not None:
            return self.api_docs_enabled
        return self.app_stage != "prod"

    @property
    def psycopg_url(self) -> str:
        """DSN для драйвера psycopg, которым пользуется checkpointer LangGraph."""
        url = self.database_url
        for prefix in ("postgresql+asyncpg://", "postgresql+psycopg://"):
            if url.startswith(prefix):
                return "postgresql://" + url.removeprefix(prefix)
        return url

    @field_validator("cookie_samesite", mode="before")
    @classmethod
    def _normalize_samesite(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("storage_endpoint")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @model_validator(mode="after")
    def _load_jwt_keys(self) -> Self:
        if self.jwt_private_key is None and _readable(self.jwt_private_key_path):
            assert self.jwt_private_key_path is not None
            self.jwt_private_key = SecretStr(_resolve(self.jwt_private_key_path).read_text())
        if self.jwt_public_key is None and _readable(self.jwt_public_key_path):
            assert self.jwt_public_key_path is not None
            self.jwt_public_key = _resolve(self.jwt_public_key_path).read_text()
        if self.jwt_private_key is None or self.jwt_public_key is None:
            raise ValueError(
                "Нужны ключи JWT: задайте JWT_PRIVATE_KEY/JWT_PUBLIC_KEY или создайте файлы командой make keys"
            )
        return self

    @model_validator(mode="after")
    def _refuse_unsafe_production(self) -> Self:
        if self.app_stage != "prod":
            return self
        problems = []
        if self.csrf_hmac_key.get_secret_value() == DEV_CSRF_KEY:
            problems.append("CSRF_HMAC_KEY имеет значение для разработки")
        if self.storage_secret_key.get_secret_value() == DEV_STORAGE_SECRET:
            problems.append("STORAGE_SECRET_KEY имеет значение для разработки")
        if f":{DEV_DATABASE_PASSWORD}@" in self.database_url:
            problems.append("DATABASE_URL содержит пароль из docker-compose")
        if not self.cookie_secure:
            problems.append("COOKIE_SECURE должен быть true")
        if self.debug:
            problems.append("DEBUG должен быть false")
        if self.demo_users_password is not None:
            problems.append("DEMO_USERS_PASSWORD не должен быть задан")
        if problems:
            raise ValueError("Небезопасные настройки prod: " + "; ".join(problems))
        return self


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else BACKEND_DIR / path


def _readable(path: Path | None) -> bool:
    return path is not None and _resolve(path).is_file()


class MigrationSettings(BaseSettings):
    """Alembic нужен только адрес БД: ключи JWT и остальное ему ни к чему."""

    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR.parent / ".env", BACKEND_DIR / ".env"), extra="ignore"
    )

    database_url: str = Settings.model_fields["database_url"].default


@lru_cache
def get_settings() -> Settings:
    """Только для точек входа (фабрика приложения, воркер, CLI, alembic); остальное получает настройки аргументом."""
    return Settings()
