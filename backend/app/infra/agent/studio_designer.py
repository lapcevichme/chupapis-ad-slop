from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from app.contracts.studio import StudioGenerationBody, StudioGenerationResult
from app.core.errors import fail
from app.infra.agent.prompts import load_prompt


class StudioDesigner:
    def __init__(self, model: BaseChatModel) -> None:
        self.model = model.bind_tools([StudioGenerationResult], tool_choice="auto")

    async def generate(self, body: StudioGenerationBody) -> StudioGenerationResult:
        try:
            response = await self.model.ainvoke(
                [
                    SystemMessage(load_prompt("studio")),
                    HumanMessage(body.model_dump_json()),
                ]
            )
            call = next(c for c in response.tool_calls if c["name"] == "StudioGenerationResult")
            result = StudioGenerationResult.model_validate(call["args"])
            if len(result.variants) != body.count:
                raise ValueError("AI вернул не все варианты")
            original = {x.id: x.text for x in body.document.layers if x.kind == "text"}
            original_layers = {x.id: x for x in body.document.layers if x.kind == "text"}
            sources = {x.src for x in body.document.layers if x.kind == "image"}
            for document in result.variants:
                if (document.width, document.height, document.format) != (
                    body.document.width,
                    body.document.height,
                    body.document.format,
                ):
                    raise ValueError("AI поменял формат")
                if {x.id: x.text for x in document.layers if x.kind == "text"} != original:
                    raise ValueError("AI поменял текст оффера")
                for layer in document.layers:
                    if layer.kind != "text":
                        continue
                    source = original_layers[layer.id]
                    if layer.role != source.role or (
                        not source.hidden and (layer.hidden or layer.opacity < 0.8)
                    ):
                        raise ValueError("AI скрыл текст оффера")
                    if (
                        layer.x < 0
                        or layer.y < 0
                        or layer.x + layer.width > document.width
                        or layer.y + layer.height > document.height
                        or layer.height < layer.fontSize * 1.15
                    ):
                        raise ValueError("AI обрезал текстовый блок")
                if any(x.src not in sources for x in document.layers if x.kind == "image"):
                    raise ValueError("AI придумал ссылку на картинку")
            return result
        except (ValidationError, ValueError, StopIteration) as exc:
            raise fail(
                "STUDIO_AI_FAILED",
                message="AI вернул несовместимый макет. Попробуйте ещё раз; текущие варианты сохранены.",
            ) from exc
        except Exception as exc:
            raise fail(
                "STUDIO_AI_FAILED",
                message="Не удалось получить AI-варианты. Текущий макет сохранён, можно продолжить вручную.",
            ) from exc
