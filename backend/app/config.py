from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = f"sqlite:///{(BACKEND_DIR / 'data' / 'adpilot.db').as_posix()}"
    seed_dir: Path = BACKEND_DIR / "seed"
    media_dir: Path = BACKEND_DIR / "data" / "media"
    # Картинки, которые раздаёт сам бэкенд. Валидатор баннера принимает их наравне с https-ссылками.
    media_base_url: str = "http://localhost:8000/media"
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
