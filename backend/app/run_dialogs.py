import asyncio
import json
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from alembic.config import Config
from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import command
from app.bootstrap import build_chat_service
from app.core.config import BACKEND_DIR, Settings, get_settings
from app.db.models import User
from app.db.seed import seed
from app.infra.campaigns_api import CampaignsApi
from app.main import create_app
from app.service.chat_sessions import SessionRegistry

DIALOGS = BACKEND_DIR.parent / "docs" / "dialogs"
TRANSCRIPTS = DIALOGS / "transcripts"
ROLE_NAMES = {"campaignManager": "Менеджер", "campaignModerator": "Модератор"}


def _events(body: str) -> list[tuple[str, dict[str, Any]]]:
    result = []
    for block in body.split("\n\n"):
        lines = dict(
            line.split(": ", 1)
            for line in block.splitlines()
            if ": " in line and not line.startswith(":")
        )
        if "event" in lines:
            result.append((lines["event"], json.loads(lines["data"])))
    return result


def _render_turn(
    events: list[tuple[str, dict[str, Any]]],
) -> tuple[list[str], dict[str, Any] | None]:
    """Ответ агента в markdown в порядке событий потока и карточка подтверждения, если она появилась."""
    out: list[str] = []
    text = ""
    steps: dict[str, Any] = {}
    confirmation = None
    marks = {"done": "✓", "failed": "✗", "running": "…"}

    def flush() -> None:
        nonlocal text, steps
        if steps:
            out.append(
                "_"
                + " · ".join(f"{marks.get(s['status'], '')} {s['label']}" for s in steps.values())
                + "_"
            )
        if text.strip():
            out.append(f"**Агент:** {text.strip()}")
        text, steps = "", {}

    for kind, data in events:
        if kind == "step":
            if text.strip():
                flush()
            steps[data["id"]] = data
        elif kind == "message_delta":
            text += data["text"]
        elif kind == "warning":
            flush()
            out.append(f"> ⚠️ **Предупреждение:** {data['message']}")
        elif kind == "suggestions":
            flush()
            out += [
                f"> 🔘 {q['header']}: "
                + " · ".join(f"[{o['label']}]" for o in q["options"])
                + " · [свой вариант]"
                for q in data["questions"]
            ]
        elif kind == "confirmation_required":
            flush()
            confirmation = data
            out.append(f"> 🟩 **Карточка подтверждения: {data['title']}**")
            out += [f"> - {op['label']}" for op in data["operations"]]
        elif kind == "error":
            flush()
            out.append(f"> ❌ **Ошибка {data.get('code', '')}:** {data['message']}")
    flush()
    return [line for item in out for line in (item, "")][:-1], confirmation


@asynccontextmanager
async def scratch_database(base_url: str) -> AsyncIterator[str]:
    """Одноразовая база на том же сервере Postgres, чтобы прогон не трогал рабочие данные."""
    url = make_url(base_url)
    name = f"adpilot_dialogs_{uuid4().hex[:8]}"
    admin = create_async_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    async with admin.connect() as connection:
        await connection.execute(text(f'CREATE DATABASE "{name}"'))
    scratch = url.set(database=name).render_as_string(hide_password=False)
    try:
        yield scratch
    finally:
        async with admin.connect() as connection:
            await connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        await admin.dispose()


async def run_dialog(path: Path) -> Path:
    base = get_settings()
    async with scratch_database(base.database_url) as database_url:
        config = Config(str(BACKEND_DIR / "alembic.ini"))
        config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
        config.attributes["database_url"] = database_url
        config.attributes["configure_logger"] = False
        await asyncio.to_thread(command.upgrade, config, "head")

        settings = base.model_copy(update={"database_url": database_url})
        app = create_app(settings)
        async with app.router.lifespan_context(app):
            async with app.state.db.unit_of_work() as uow:
                await seed(uow.session, settings.seed_dir, demo_password=uuid4().hex)
            transport = httpx.ASGITransport(app=app)
            app.state.chat = build_chat_service(
                InMemorySaver(),
                settings,
                SessionRegistry(app.state.db),
                media=app.state.media_store,
                api_factory=lambda token: CampaignsApi(
                    token, base_url="http://api", transport=transport
                ),
            )
            tokens: dict[str, str] = {}
            async with app.state.db.unit_of_work() as uow:
                for user in await uow.session.scalars(select(User)):
                    tokens[user.username] = app.state.token_codec.issue_access(
                        user_id=user.id, session_id=uuid4(), auth_version=user.auth_version
                    )
            return await _run_dialog(path, settings, transport, tokens)


async def _run_dialog(
    path: Path, settings: Settings, transport: httpx.ASGITransport, tokens: dict[str, str]
) -> Path:
    scenario = json.loads(path.read_text(encoding="utf-8"))
    lines = [
        f"# {scenario['title']}",
        "",
        scenario["description"],
        "",
        f"Прогон {datetime.now(UTC):%Y-%m-%d %H:%M} UTC, сценарий `{path.name}`. Чат-агент `{settings.chat_model}`, "
        f"дизайн-агент `{settings.design_model}`, картинки `{settings.image_model or 'выключены'}`. БД — свежие моки.",
        "",
    ]
    sessions: dict[str, str] = {}
    pending: dict[str, dict[str, Any] | None] = {}
    async with httpx.AsyncClient(transport=transport, base_url="http://api", timeout=600) as client:
        for number, step in enumerate(scenario["steps"], 1):
            user, role = step.get("as", scenario["user"]), step.get("role", scenario["role"])
            headers = {"Authorization": f"Bearer {tokens[user]}"}
            if user not in sessions:
                body = {"campaignId": scenario["campaignId"]} if scenario.get("campaignId") else {}
                sessions[user] = (await client.post("/chat", json=body, headers=headers)).json()[
                    "sessionId"
                ]
            sid, who = sessions[user], f"{ROLE_NAMES.get(role, role)} ({user})"
            lines.append(f"## {number}.")
            lines.append("")
            if "say" in step:
                lines.append(f"**{who}:** {step['say']}")
                response = await client.post(
                    f"/chat/{sid}/messages", json={"text": step["say"]}, headers=headers
                )
            else:
                card = pending.get(user)
                if card is None:
                    lines += ["_Карточки подтверждения нет, шаг пропущен._", ""]
                    continue
                approved = bool(step["confirm"])
                lines.append(
                    f"**{who}** нажимает «{'Подтвердить' if approved else 'Не подтверждать'}» в карточке «{card['title']}»."
                )
                response = await client.post(
                    f"/chat/{sid}/confirmations/{card['id']}",
                    json={"approved": approved},
                    headers=headers,
                )
            rendered, pending[user] = _render_turn(_events(response.text))
            lines += [""] + rendered + [""]
            print(f"  {path.stem}: шаг {number} готов", flush=True)

        snapshot = (
            await client.get(
                f"/chat/{sessions[scenario['user']]}",
                headers={"Authorization": f"Bearer {tokens[scenario['user']]}"},
            )
        ).json()
        if snapshot.get("campaignId"):
            reader = {"Authorization": f"Bearer {tokens[scenario['user']]}"}
            campaign = (
                await client.get(f"/campaigns/{snapshot['campaignId']}", headers=reader)
            ).json()
            audit = (
                await client.get(f"/campaigns/{snapshot['campaignId']}/audit", headers=reader)
            ).json()
            lines += [
                "## Итог",
                "",
                f"Кампания {campaign['id']} «{campaign['name']}»: состояние `{campaign['state']}`, "
                f"баннеров {len(campaign['banners'])}, промо-экранов {len(campaign['contents'])}, креативов {len(campaign['creatives'])}.",
                "",
                "Журнал аудита: "
                + ", ".join(f"{a['entity']} {a['action']} ({a['actor']})" for a in audit),
                "",
            ]
    TRANSCRIPTS.mkdir(parents=True, exist_ok=True)
    target = TRANSCRIPTS / f"{path.stem}.md"
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


async def main(names: list[str]) -> None:
    paths = sorted(DIALOGS.glob("*.json"))
    if names:
        paths = [p for p in paths if any(name in p.stem for name in names)]
    for path in paths:
        print(f"Диалог {path.stem}", flush=True)
        print(f"  → {await run_dialog(path)}", flush=True)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
