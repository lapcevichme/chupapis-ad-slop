"""Граф агента на LangGraph.

    START → agent ⇄ tools → confirm → agent → … → END

- agent: чат-модель с инструментами чтения, `propose_*` и UI-инструментами;
- tools: выполняет инструменты, копит пакет операций и обновляет превью;
- confirm: `interrupt()` с пакетом, после «да» выполняет записи в API. Только этот узел пишет в API.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Any, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt

from app.agent.api_client import ApiCallError, CampaignsApi
from app.agent.designer import Designer
from app.agent.operations import apply_operations, confirmation_changes, draft_warnings, execute, public_draft
from app.agent.prompts import load_prompt
from app.agent.tools import ToolContext, run_tool, step_label, tool_schemas


def _replace(_old: Any, new: Any) -> Any:
    return new


class AgentState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    campaign_id: Annotated[int | None, _replace]
    base: Annotated[dict[str, Any] | None, _replace]
    pending: Annotated[list[dict[str, Any]], _replace]
    id_map: Annotated[dict[str, int], _replace]
    counter: Annotated[int, _replace]
    awaiting: Annotated[dict[str, Any] | None, _replace]


@dataclass
class AgentDeps:
    chat_model: BaseChatModel
    designer: Designer
    api_factory: Callable[[str, str], CampaignsApi]


def actor(config: RunnableConfig) -> tuple[str, str]:
    configurable = config.get("configurable", {})
    return configurable.get("user", ""), configurable.get("role", "")


async def refresh_campaign(client: CampaignsApi, campaign_id: int | None) -> dict[str, Any]:
    """Свежая кампания из API. Её меняют и вне этого диалога: модератор решает судьбу в своём чате."""
    if campaign_id is None:
        return {}
    try:
        return {"base": await client.get(f"/campaigns/{campaign_id}")}
    except ApiCallError as exc:
        if exc.status == 404:
            return {"campaign_id": None, "base": None}
        raise


async def draft_report(client: CampaignsApi, state: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Черновик для превью и его проверка: у сохранённой кампании без правок — ответ API, иначе локальные правила."""
    pending = state.get("pending") or []
    draft = apply_operations(state.get("base"), pending)
    if state.get("campaign_id") is not None and not pending:
        try:
            return public_draft(draft), await client.get(f"/campaigns/{state['campaign_id']}/warnings")
        except ApiCallError:
            pass
    places = {p["id"]: p for p in await client.get("/places")}
    banner_types = {t["id"]: t for t in await client.get("/banner-types")}
    return public_draft(draft), {"errors": [], "warnings": draft_warnings(draft, places, banner_types)}


def _context_note(state: AgentState, config: RunnableConfig) -> str:
    user, role = actor(config)
    base = state.get("base")
    lines = [
        "",
        "## Контекст",
        "Это состояние на текущий момент: блок пересобирается перед каждым твоим ответом и уже учитывает все выполненные записи. Если кампания здесь появилась после подтверждения — это та самая кампания, которую ты создал.",
        f"Сейчас {datetime.now(UTC):%Y-%m-%d %H:%M} UTC. Пользователь {user}, роль {role or 'не задана'}.",
    ]
    if base:
        lines.append(f"Текущая кампания: id {base['id']}, состояние {base['state']}, published={str(base['published']).lower()}.")
    else:
        lines.append("Кампания ещё не создана.")
    pending = state.get("pending") or []
    if pending:
        lines.append("Пакет ждёт подтверждения:")
        lines += [f"- {op['ref'] or '—'}: {op['label']}" for op in pending]
    draft = apply_operations(base, pending)
    if draft:
        lines.append("Черновик (то, что видит пользователь в превью):")
        lines.append(json.dumps(draft, ensure_ascii=False, default=str))
    return "\n".join(lines)


def build_graph(deps: AgentDeps, checkpointer):
    async def agent_node(state: AgentState, config: RunnableConfig):
        user, role = actor(config)
        async with deps.api_factory(user, role) as client:
            fresh = await refresh_campaign(client, state.get("campaign_id"))
        state = {**state, **fresh}
        model = deps.chat_model.bind_tools(tool_schemas())
        prompt = SystemMessage(load_prompt("chat") + _context_note(state, config))
        response = await model.ainvoke([prompt, *state["messages"]], config)
        return {"messages": [response], **fresh}

    async def tools_node(state: AgentState, config: RunnableConfig):
        writer = get_stream_writer()
        call_message: AIMessage = state["messages"][-1]
        user, role = actor(config)
        async with deps.api_factory(user, role) as client:
            ctx = ToolContext(
                client=client,
                designer=deps.designer,
                campaign_id=state.get("campaign_id"),
                base=state.get("base"),
                pending=list(state.get("pending") or []),
                counter=state.get("counter", 0),
                emit=lambda event, data: writer({"event": event, "data": data}),
            )
            replies: list[ToolMessage] = []
            awaiting = None
            for call in call_message.tool_calls:
                if call["name"] == "request_confirmation":
                    if awaiting is not None or not ctx.pending:
                        text = "Пакет пуст: нечего подтверждать." if not ctx.pending else "Подтверждение уже запрошено."
                        replies.append(ToolMessage(text, tool_call_id=call["id"], name=call["name"]))
                        continue
                    ctx.counter += 1
                    awaiting = {
                        "id": f"conf-{ctx.counter}",
                        "title": call["args"].get("title") or "Подтвердите изменения",
                        "operations": [{"kind": op["kind"], "label": op["label"]} for op in ctx.pending],
                        "changes": confirmation_changes(ctx.base, ctx.pending),
                        "toolCallId": call["id"],
                    }
                    continue

                label = step_label(call["name"])
                step_id = call["id"]
                if label:
                    writer({"event": "step", "data": {"id": step_id, "label": label, "status": "running"}})

                def progress(text: str, step_id=step_id):
                    writer({"event": "step", "data": {"id": step_id, "label": text, "status": "running"}})

                try:
                    content = await run_tool(ctx, call["name"], call["args"], progress)
                    status = "failed" if content.startswith("Ошибка") else "done"
                except ApiCallError as exc:
                    content, status = f"Ошибка API {exc.status}: {exc}", "failed"
                if label:
                    writer({"event": "step", "data": {"id": step_id, "label": label, "status": status}})
                replies.append(ToolMessage(content, tool_call_id=call["id"], name=call["name"]))

            if ctx.draft_changed:
                draft, validation = await draft_report(client, {**state, "pending": ctx.pending})
                writer({"event": "draft_updated", "data": {"draft": draft, "validation": validation}})
        return {"messages": replies, "pending": ctx.pending, "counter": ctx.counter, "awaiting": awaiting}

    async def confirm_node(state: AgentState, config: RunnableConfig):
        awaiting = state["awaiting"]
        answer = interrupt({k: v for k, v in awaiting.items() if k != "toolCallId"})
        writer = get_stream_writer()
        call_id = awaiting["toolCallId"]
        update: dict[str, Any] = {"awaiting": None}

        if not answer.get("approved"):
            comment = (answer.get("comment") or "").strip()
            text = "Пользователь не подтвердил пакет, операции остались в пакете."
            text += f" Комментарий: {comment}" if comment and not answer.get("viaMessage") else " Спроси, что изменить."
            messages: list[AnyMessage] = [ToolMessage(text, tool_call_id=call_id, name="request_confirmation")]
            if answer.get("viaMessage"):
                messages.append(HumanMessage(comment))
            return update | {"messages": messages}

        user, role = actor(config)
        writer({"event": "step", "data": {"id": awaiting["id"], "label": "Сохраняю изменения", "status": "running"}})
        async with deps.api_factory(user, role) as client:
            result = await execute(state.get("pending") or [], client, campaign_id=state.get("campaign_id"), id_map=state.get("id_map") or {})
            base = await client.get(f"/campaigns/{result.campaign_id}") if result.campaign_id is not None else None
        writer({"event": "step", "data": {"id": awaiting["id"], "label": "Сохраняю изменения", "status": "failed" if result.error else "done"}})
        writer({"event": "campaign_updated", "data": {"campaignId": result.campaign_id}})

        lines = ["Пользователь подтвердил."]
        if result.done:
            lines.append("Выполнено:")
            lines += [f"- {line}" for line in result.done]
        if result.error:
            lines.append(f"Ошибка: {result.error}")
            lines.append("Остальные операции пакета не выполнены и сняты. Объясни ошибку и предложи исправленный пакет.")
        return update | {
            "messages": [ToolMessage("\n".join(lines), tool_call_id=call_id, name="request_confirmation")],
            "pending": [],
            "campaign_id": result.campaign_id,
            "base": base,
            "id_map": result.id_map,
        }

    def after_agent(state: AgentState) -> str:
        last = state["messages"][-1]
        return "tools" if isinstance(last, AIMessage) and last.tool_calls else END

    def after_tools(state: AgentState) -> str:
        return "confirm" if state.get("awaiting") else "agent"

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.add_node("confirm", confirm_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", after_agent, ["tools", END])
    graph.add_conditional_edges("tools", after_tools, ["confirm", "agent"])
    graph.add_edge("confirm", "agent")
    return graph.compile(checkpointer=checkpointer)
