from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.contracts.chat import EVENT_MODELS


class ApiApplication(FastAPI):
    def openapi(self) -> dict[str, Any]:
        if self.openapi_schema is not None:
            return self.openapi_schema
        schema = get_openapi(title=self.title, version=self.version, routes=self.routes)
        components = schema.setdefault("components", {}).setdefault("schemas", {})
        for model in EVENT_MODELS.values():
            model_schema = model.model_json_schema(
                ref_template="#/components/schemas/{model}", mode="serialization"
            )
            components.update(model_schema.pop("$defs", {}))
            components[model.__name__] = model_schema
        schema["x-chat-events"] = {
            event: f"#/components/schemas/{model.__name__}" for event, model in EVENT_MODELS.items()
        }
        self.openapi_schema = schema
        return schema
