import asyncio
from pathlib import Path

from app.core.config import Settings
from app.infra.speech import OpenRouterSynthesizer

CUES = {
    "greet": "Здравствуйте! Расскажите, что будем рекламировать.",
    "wait-1": "Секунду, смотрю.",
    "wait-2": "Сейчас гляну.",
    "wait-3": "Давайте я подумаю.",
    "wait-4": "Так, минутку.",
    "wait-5": "Хорошо, сейчас посмотрю.",
    "more-1": "Ещё немного, собираю.",
    "more-2": "Ещё чуть-чуть.",
    "more-3": "Проверяю детали.",
    "form": "Есть пара вопросов, они на экране.",
    "confirm": "Проверьте и подтвердите кнопкой.",
}
TARGET = Path(__file__).resolve().parents[2] / "frontend" / "public" / "voice"


async def main() -> None:
    synthesizer = OpenRouterSynthesizer(Settings())
    TARGET.mkdir(parents=True, exist_ok=True)
    for name, text in CUES.items():
        (TARGET / f"{name}.mp3").write_bytes(await synthesizer.synthesize(text))


if __name__ == "__main__":
    asyncio.run(main())
