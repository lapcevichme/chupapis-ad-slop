"""Сессии чата поверх графа: создание, снимок для восстановления и SSE-поток ответа."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import suppress
from typing import Any, cast

import httpx
import openai
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.errors import GraphRecursionError
from langgraph.types import Command, StateSnapshot

from app.core.errors import not_found
from app.domain.chat import StreamEvent
from app.infra.agent.graph import AgentGraph, AgentState, draft_report, refresh_campaign
from app.infra.campaigns_api import ApiFactory
from app.service.chat_sessions import SessionRegistry

KEEP_ALIVE_SECONDS = 15
logger = logging.getLogger(__name__)


def describe_failure(exc: Exception) -> tuple[str, str]:
    """Сбой хода → код и сообщение для пользователя. Сырой текст ошибки уходит только в лог сервера."""
    status = getattr(exc, "status_code", None) or getattr(
        getattr(exc, "response", None), "status_code", None
    )
    text = str(exc)
    if isinstance(exc, GraphRecursionError):
        return (
            "AGENT_LOOP",
            "Агент зациклился и остановился. Переформулируйте запрос или нажмите «Повторить».",
        )
    if isinstance(exc, (openai.APITimeoutError, httpx.TimeoutException, TimeoutError)):
        return "LLM_TIMEOUT", "Модель слишком долго не отвечает. Нажмите «Повторить»."
    if isinstance(exc, (openai.APIConnectionError, httpx.TransportError)):
        return (
            "LLM_UNAVAILABLE",
            "Нет связи с сервисом модели. Проверьте интернет и нажмите «Повторить».",
        )
    if status == 401:
        return "LLM_AUTH", "Ключ модели не подходит: проверьте LLM_API_KEY в .env."
    if status in (402, 403) and ("limit" in text.lower() or "credit" in text.lower()):
        return (
            "LLM_LIMIT",
            "Закончился лимит ключа модели. Поднимите лимит в OpenRouter и нажмите «Повторить».",
        )
    if status == 429:
        return (
            "LLM_RATE_LIMIT",
            "Сервис модели перегружен запросами. Подождите немного и нажмите «Повторить».",
        )
    if status is not None and status >= 500:
        return "LLM_UNAVAILABLE", "Сервис модели временно недоступен. Нажмите «Повторить»."
    if status is not None:
        return (
            "LLM_REJECTED",
            "Сервис модели отклонил запрос. Нажмите «Повторить»; если не поможет, начните новый диалог.",
        )
    return "AGENT_FAILED", "Агент не смог продолжить из-за внутренней ошибки. Нажмите «Повторить»."


def _text(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    return "".join(part.get("text", "") for part in content if isinstance(part, dict))


class ChatService:
    def __init__(self, graph: AgentGraph, api_factory: ApiFactory, sessions: SessionRegistry):
        self.graph = graph
        self.api_factory = api_factory
        self.sessions = sessions

    @staticmethod
    def _config(session_id: str, user: str = "", role: str = "") -> RunnableConfig:
        return {
            "configurable": {"thread_id": session_id, "user": user, "role": role},
            "recursion_limit": 60,
        }

    async def create_session(self, campaign_id: int | None, user: str, role: str) -> str:
        """У пары «кампания + логин» один диалог: повторный вызов возвращает существующий."""
        base = None
        if campaign_id is not None:
            async with self.api_factory(user, role) as client:
                base = await client.get(f"/campaigns/{campaign_id}")
            existing = await self.sessions.find(campaign_id, user)
            if existing is not None:
                snapshot = await self.graph.aget_state(self._config(existing))
                if snapshot.values and "pending" in snapshot.values:
                    return existing
                # Связь есть, а состояние диалога потеряно (например, удалили checkpoints.db): начинаем заново под тем же id.
                await self._init_state(existing, campaign_id, base)
                return existing
        session_id = await self.sessions.create(campaign_id, user)
        await self._init_state(session_id, campaign_id, base)
        return session_id

    async def _init_state(
        self, session_id: str, campaign_id: int | None, base: dict[str, Any] | None
    ) -> None:
        values: AgentState = {
            "messages": [],
            "campaign_id": campaign_id,
            "base": base,
            "pending": [],
            "id_map": {},
            "counter": 0,
            "awaiting": None,
        }
        await self.graph.aupdate_state(self._config(session_id), values, as_node="__start__")

    async def _state(self, session_id: str) -> StateSnapshot:
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
            # Кампанию могли изменить из другого диалога (решение модератора), поэтому берём её из API.
            values = values | await refresh_campaign(client, values.get("campaign_id"))
            draft, validation = await draft_report(client, values)
        return {
            "campaignId": values.get("campaign_id"),
            "messages": messages,
            "draft": draft,
            "validation": validation,
            "pendingConfirmation": snapshot.interrupts[0].value if snapshot.interrupts else None,
        }

    # --- Поток

    async def send_message(
        self, session_id: str, text: str, user: str, role: str
    ) -> AsyncIterator[StreamEvent]:
        await self._state(session_id)
        if await self.pending_confirmation(session_id):
            # Сообщение без ответа на подтверждение = отказ, текст уходит агенту как правка (chat-api.md §2).
            payload: Any = Command(resume={"approved": False, "comment": text, "viaMessage": True})
        else:
            payload = {"messages": [HumanMessage(text)], "asked": False}
        return self._stream(session_id, payload, user, role)

    async def answer_confirmation(
        self,
        session_id: str,
        confirmation_id: str,
        approved: bool,
        comment: str | None,
        user: str,
        role: str,
    ) -> AsyncIterator[StreamEvent]:
        pending = await self.pending_confirmation(session_id)
        if pending and pending["id"] == confirmation_id:
            return self._stream(
                session_id, Command(resume={"approved": approved, "comment": comment}), user, role
            )
        # Подтверждение уже выполнено: второй раз не пишем, а продолжаем ход как retry.
        return self._stream(session_id, None, user, role)

    async def retry(self, session_id: str, user: str, role: str) -> AsyncIterator[StreamEvent]:
        await self._state(session_id)
        return self._stream(session_id, None, user, role)

    async def _bind_campaign(self, session_id: str) -> None:
        snapshot = await self.graph.aget_state(self._config(session_id))
        await self.sessions.bind(session_id, (snapshot.values or {}).get("campaign_id"))

    async def _stream(
        self, session_id: str, payload: Any, user: str, role: str
    ) -> AsyncIterator[StreamEvent]:
        queue: asyncio.Queue[StreamEvent | None] = asyncio.Queue()
        config = self._config(session_id, user, role)

        async def produce() -> None:
            try:
                # Multiple v1 stream modes produce (mode, payload), unlike a single mode.
                stream = cast(
                    AsyncIterator[tuple[str, Any]],
                    self.graph.astream(
                        payload, config, stream_mode=["messages", "custom", "updates"]
                    ),
                )
                async for mode, chunk in stream:
                    if mode == "messages":
                        message, metadata = chunk
                        if metadata.get("langgraph_node") == "agent" and isinstance(
                            message, AIMessage
                        ):
                            text = _text(message)
                            if text:
                                await queue.put(StreamEvent("message_delta", {"text": text}))
                    elif mode == "custom":
                        await queue.put(StreamEvent(chunk["event"], chunk["data"]))
                    elif mode == "updates" and "__interrupt__" in chunk:
                        await queue.put(
                            StreamEvent("confirmation_required", chunk["__interrupt__"][0].value)
                        )
                await queue.put(StreamEvent("done", {}))
            except Exception as exc:  # сбой LLM или сети: фронт покажет «Повторить»
                logger.exception("Ход агента в сессии %s упал", session_id)
                code, message = describe_failure(exc)
                await queue.put(StreamEvent("error", {"code": code, "message": message}))
            finally:
                # Привязываем и после сбоя: кампания могла сохраниться до того, как упал следующий шаг.
                try:
                    await self._bind_campaign(session_id)
                except Exception:
                    logger.exception("Не удалось привязать сессию %s к кампании", session_id)
                await queue.put(None)

        task = asyncio.create_task(produce())
        try:
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=KEEP_ALIVE_SECONDS)
                except TimeoutError:
                    yield StreamEvent("")
                    continue
                if item is None:
                    break
                yield item
        finally:
            if not task.done():
                task.cancel()
            with suppress(asyncio.CancelledError):
                await task
