"""Сессии чата поверх графа: создание, снимок для восстановления и SSE-поток ответа."""

import asyncio
import uuid
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from app.agent.api_client import CampaignsApi
from app.agent.events import sse
from app.agent.graph import AgentState, draft_report
from app.errors import not_found

KEEP_ALIVE_SECONDS = 15


def _text(message) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    return "".join(part.get("text", "") for part in content if isinstance(part, dict))


class ChatService:
    def __init__(self, graph, api_factory):
        self.graph = graph
        self.api_factory = api_factory

    @staticmethod
    def _config(session_id: str, user: str = "", role: str = "") -> dict[str, Any]:
        return {"configurable": {"thread_id": session_id, "user": user, "role": role}, "recursion_limit": 60}

    async def create_session(self, campaign_id: int | None, user: str, role: str) -> str:
        base = None
        if campaign_id is not None:
            async with self.api_factory(user, role) as client:
                base = await client.get(f"/campaigns/{campaign_id}")
        session_id = uuid.uuid4().hex
        values: AgentState = {"messages": [], "campaign_id": campaign_id, "base": base, "pending": [], "id_map": {}, "counter": 0, "awaiting": None}
        await self.graph.aupdate_state(self._config(session_id), values, as_node="__start__")
        return session_id

    async def _state(self, session_id: str):
        snapshot = await self.graph.aget_state(self._config(session_id))
        if not snapshot.values or "pending" not in snapshot.values:
            raise not_found("sessionId", session_id)
        return snapshot

    async def pending_confirmation(self, session_id: str) -> dict[str, Any] | None:
        snapshot = await self._state(session_id)
        return snapshot.interrupts[0].value if snapshot.interrupts else None

    async def snapshot(self, session_id: str, user: str, role: str) -> dict[str, Any]:
        snapshot = await self._state(session_id)
        values = snapshot.values
        messages = []
        for message in values.get("messages", []):
            text = _text(message).strip()
            if isinstance(message, HumanMessage) and text:
                messages.append({"role": "user", "text": text})
            elif isinstance(message, AIMessage) and text:
                messages.append({"role": "assistant", "text": text})
        async with self.api_factory(user, role) as client:
            draft, validation = await draft_report(client, values)
        return {
            "campaignId": values.get("campaign_id"),
            "messages": messages,
            "draft": draft,
            "validation": validation,
            "pendingConfirmation": snapshot.interrupts[0].value if snapshot.interrupts else None,
        }

    # --- Поток

    async def send_message(self, session_id: str, text: str, user: str, role: str) -> AsyncIterator[str]:
        await self._state(session_id)
        if await self.pending_confirmation(session_id):
            # Сообщение без ответа на подтверждение = отказ, текст уходит агенту как правка (chat-api.md §2).
            payload: Any = Command(resume={"approved": False, "comment": text, "viaMessage": True})
        else:
            payload = {"messages": [HumanMessage(text)]}
        return self._stream(session_id, payload, user, role)

    async def answer_confirmation(self, session_id: str, confirmation_id: str, approved: bool, comment: str | None, user: str, role: str) -> AsyncIterator[str]:
        pending = await self.pending_confirmation(session_id)
        if pending and pending["id"] == confirmation_id:
            return self._stream(session_id, Command(resume={"approved": approved, "comment": comment}), user, role)
        # Подтверждение уже выполнено: второй раз не пишем, а продолжаем ход как retry.
        return self._stream(session_id, None, user, role)

    async def retry(self, session_id: str, user: str, role: str) -> AsyncIterator[str]:
        await self._state(session_id)
        return self._stream(session_id, None, user, role)

    async def _stream(self, session_id: str, payload: Any, user: str, role: str) -> AsyncIterator[str]:
        queue: asyncio.Queue[str | None] = asyncio.Queue()
        config = self._config(session_id, user, role)

        async def produce():
            try:
                async for mode, chunk in self.graph.astream(payload, config, stream_mode=["messages", "custom", "updates"]):
                    if mode == "messages":
                        message, metadata = chunk
                        if metadata.get("langgraph_node") == "agent" and isinstance(message, AIMessage):
                            text = _text(message)
                            if text:
                                await queue.put(sse("message_delta", {"text": text}))
                    elif mode == "custom":
                        await queue.put(sse(chunk["event"], chunk["data"]))
                    elif mode == "updates" and "__interrupt__" in chunk:
                        await queue.put(sse("confirmation_required", chunk["__interrupt__"][0].value))
                await queue.put(sse("done", {}))
            except Exception as exc:  # сбой LLM или сети: фронт покажет «Повторить»
                message = str(exc)[:500] or "Агент не смог продолжить"
                if "Authentication" in type(exc).__name__ or "401" in message:
                    message = "LLM недоступна: проверьте LLM_API_KEY в .env"
                await queue.put(sse("error", {"code": type(exc).__name__, "message": message}))
            finally:
                await queue.put(None)

        task = asyncio.create_task(produce())
        try:
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=KEEP_ALIVE_SECONDS)
                except TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                if item is None:
                    break
                yield item
        finally:
            if not task.done():
                task.cancel()


def default_api_factory(user: str, role: str) -> CampaignsApi:
    return CampaignsApi(user, role)
