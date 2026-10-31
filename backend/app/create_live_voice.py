"""Создаёт голос GPT-Live из описания: среди встроенных нет русских.

Запуск: cd backend && uv run python -m app.create_live_voice female
Напечатанный id указать в LIVE_VOICE. Создание бесплатно, каждый запуск сохраняет новый голос.
"""

import asyncio
import sys
from typing import Any

import httpx

from app.core.config import Settings

SCRIPT_HINT = (
    "Здравствуйте! Расскажите, что будем рекламировать. "
    "Принято: вклад под шестнадцать процентов на год, показы с пятого ноября. "
    "Сейчас посмотрю подходящие сегменты и соберу макет для сторис и баннера в приложении. "
    "Кампания готова. Проверьте карточку на экране и нажмите кнопку подтверждения, "
    "голосом сохранить её нельзя. Если что-то нужно поправить, просто скажите мне. "
    "Выбор сегментов пока не окончательный: я предлагаю, а решение остаётся за вами. "
    "Хорошо, заголовок заменён. Отправляю на модерацию только после вашего подтверждения."
)

_DESIGN = (
    "Accent: native Russian, standard Moscow pronunciation. Age: around 30. "
    "Presentation: {presentation}. Timbre: {timbre}. Texture: clean. Pitch: {pitch}. "
    "Loudness: moderate. Speech rate: moderate. Distinctiveness: natural. "
    "A native speaker of Russian talking calmly with a colleague at work. Russian is the first "
    "and only language of this voice: correct Russian stress and intonation, palatalized and hard "
    "consonants, clear difference between the vowels ы and и, reduced unstressed vowels. "
    "Avoid any English or other foreign accent and avoid an announcer manner."
)

DESIGNS = {
    "female": _DESIGN.format(presentation="feminine", timbre="warm", pitch="medium"),
    "male": _DESIGN.format(presentation="masculine", timbre="warm", pitch="medium-low"),
}


async def create_voice(
    settings: Settings, design: str, transport: httpx.AsyncBaseTransport | None = None
) -> str:
    body: dict[str, Any] = {
        "type": "prompt",
        "name": f"adpilot-ru-{design}",
        "prompt": DESIGNS[design],
        "model": "auto",
        "script_hint": SCRIPT_HINT,
    }
    async with httpx.AsyncClient(
        timeout=settings.speech_timeout_seconds, transport=transport
    ) as client:
        response = await client.post(
            f"{settings.live_base_url}/audio/voices",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json=body,
        )
    if response.is_error:
        raise SystemExit(f"HTTP {response.status_code}: {response.text[:400]}")
    voice_id: str = response.json()["id"]
    return voice_id


def main() -> None:
    design = sys.argv[1] if len(sys.argv) > 1 else ""
    if design not in DESIGNS:
        raise SystemExit(f"Укажите голос: {', '.join(DESIGNS)}")
    settings = Settings()
    if not settings.openai_api_key:
        raise SystemExit("Не задан OPENAI_API_KEY")
    print(asyncio.run(create_voice(settings, design)))


if __name__ == "__main__":
    main()
