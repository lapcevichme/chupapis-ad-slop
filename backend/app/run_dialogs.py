import asyncio
import json
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import httpx
from langgraph.checkpoint.memory import InMemorySaver

from app.agent.api_client import CampaignsApi
from app.agent.factory import build_chat_service
from app.core.config import BACKEND_DIR, Settings
from app.db import Base
from app.agent.sessions import SessionRegistry
from app.main import create_app
from app.seed import seed

DIALOGS = BACKEND_DIR.parent / "docs" / "dialogs"
TRANSCRIPTS = DIALOGS / "transcripts"
ROLE_NAMES = {"campaignManager": "Менеджер", "campaignModerator": "Модератор"}


def _events(body: str) -> list[tuple[str, dict]]:
    result = []
    for block in body.split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line and not line.startswith(":"))
        if "event" in lines:
            result.append((lines["event"], json.loads(lines["data"])))
    return result


def _render_turn(events: list[tuple[str, dict]]) -> tuple[list[str], dict | None]:
    """Ответ агента в markdown в порядке событий потока и карточка подтверждения, если она появилась."""
    out: list[str] = []
    text, steps, confirmation = "", {}, None
    marks = {"done": "✓", "failed": "✗", "running": "…"}

    def flush() -> None:
        nonlocal text, steps
        if steps:
            out.append("_" + " · ".join(f"{marks.get(s['status'], '')} {s['label']}" for s in steps.values()) + "_")
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
            groups: dict[str, list[str]] = {}
            for item in data["items"]:
                groups.setdefault(item.get("group") or "Варианты", []).append(item["label"])
            out += [f"> 🔘 {group}: " + " · ".join(f"[{label}]" for label in labels) for group, labels in groups.items()]
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


async def run_dialog(path: Path) -> Path:
    settings = Settings(
        database_url=f"sqlite:///{Path(tempfile.mkdtemp()) / 'dialogs.db'}",
        checkpoint_db=Path(tempfile.mkdtemp()) / 'checkpoints.db',
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessions() as session:
            seed(session, settings.seed_dir)
        transport = httpx.ASGITransport(app=app)
        app.state.chat = build_chat_service(
            InMemorySaver(), settings, SessionRegistry(app.state.db.sessions),
            api_factory=lambda user, role: CampaignsApi(user, role, base_url="http://api", transport=transport),
        )
        return await _run_dialog(path, settings, transport)


async def _run_dialog(path, settings, transport) -> Path:
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
    pending: dict[str, dict | None] = {}
    async with httpx.AsyncClient(transport=transport, base_url="http://api", timeout=600) as client:
        for number, step in enumerate(scenario["steps"], 1):
            user, role = step.get("as", scenario["user"]), step.get("role", scenario["role"])
            headers = {"X-User": user, "X-Role": role}
            if user not in sessions:
                body = {"campaignId": scenario["campaignId"]} if scenario.get("campaignId") else {}
                sessions[user] = (await client.post("/chat", json=body, headers=headers)).json()["sessionId"]
            sid, who = sessions[user], f"{ROLE_NAMES.get(role, role)} ({user})"
            lines.append(f"## {number}.")
            lines.append("")
            if "say" in step:
                lines.append(f"**{who}:** {step['say']}")
                response = await client.post(f"/chat/{sid}/messages", json={"text": step["say"]}, headers=headers)
            else:
                card = pending.get(user)
                if card is None:
                    lines += ["_Карточки подтверждения нет, шаг пропущен._", ""]
                    continue
                approved = bool(step["confirm"])
                lines.append(f"**{who}** нажимает «{'Подтвердить' if approved else 'Не подтверждать'}» в карточке «{card['title']}».")
                response = await client.post(f"/chat/{sid}/confirmations/{card['id']}", json={"approved": approved}, headers=headers)
            rendered, pending[user] = _render_turn(_events(response.text))
            lines += [""] + rendered + [""]
            print(f"  {path.stem}: шаг {number} готов", flush=True)

        snapshot = (await client.get(f"/chat/{sessions[scenario['user']]}", headers={"X-User": scenario["user"]})).json()
        if snapshot.get("campaignId"):
            campaign = (await client.get(f"/campaigns/{snapshot['campaignId']}")).json()
            audit = (await client.get(f"/campaigns/{snapshot['campaignId']}/audit")).json()
            lines += [
                "## Итог",
                "",
                f"Кампания {campaign['id']} «{campaign['name']}»: состояние `{campaign['state']}`, "
                f"баннеров {len(campaign['banners'])}, промо-экранов {len(campaign['contents'])}, креативов {len(campaign['creatives'])}.",
                "",
                "Журнал аудита: " + ", ".join(f"{a['entity']} {a['action']} ({a['actor']})" for a in audit),
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
