from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

COLOR = r"^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$"


class StudioModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class StudioLayer(StudioModel):
    id: str = Field(min_length=1, max_length=80)
    name: str = Field(max_length=100)
    kind: Literal["text", "shape", "image"]
    role: Literal["title", "body", "button", "decoration"] = "decoration"
    x: float = Field(ge=-2400, le=2400)
    y: float = Field(ge=-2400, le=2400)
    width: float = Field(gt=0, le=2400)
    height: float = Field(gt=0, le=2400)
    rotation: float = Field(0, ge=-180, le=180)
    opacity: float = Field(1, ge=0, le=1)
    hidden: bool = False
    locked: bool = False
    text: str = Field("", max_length=5000)
    fontSize: float = Field(24, ge=8, le=120)
    fontWeight: Literal[400, 500, 600, 700, 800] = 600
    textAlign: Literal["left", "center", "right"] = "left"
    fill: str = Field("#ffffff", pattern=COLOR)
    shape: Literal["rect", "ellipse"] = "rect"
    radius: float = Field(0, ge=0, le=600)
    src: str = Field("", max_length=2000)
    fit: Literal["cover", "contain"] = "cover"

    @model_validator(mode="after")
    def image_source(self) -> "StudioLayer":
        if self.kind == "image" and not self.src.startswith(("https://", "/api/media/")):
            raise ValueError("Изображение должно быть загружено в медиа или доступно по https")
        return self


class StudioDocument(StudioModel):
    version: Literal[1] = 1
    name: str = Field(min_length=1, max_length=100)
    format: Literal["STORY", "SMART_BANNER", "PROMO"]
    width: int = Field(300, ge=120, le=1200)
    height: int = Field(600, ge=120, le=2400)
    background: str = Field("#3155ff", pattern=COLOR)
    layers: list[StudioLayer] = Field(max_length=40)

    @model_validator(mode="after")
    def unique_layers_and_copy_limits(self) -> "StudioDocument":
        if len({layer.id for layer in self.layers}) != len(self.layers):
            raise ValueError("Идентификаторы слоёв должны быть уникальны")
        if self.format != "PROMO":
            title = " ".join(x.text for x in self.layers if x.kind == "text" and x.role == "title")
            body = " ".join(x.text for x in self.layers if x.kind == "text" and x.role != "title")
            title_max, body_max = (100, 500) if self.format == "STORY" else (250, 1000)
            if len(title) > title_max or len(body) > body_max:
                raise ValueError(f"Лимит текста: заголовок {title_max}, остальные блоки {body_max}")
        return self


class StoredStudioDocument(StudioModel):
    id: str
    url: str
    document: StudioDocument


class StudioGenerationBody(StudioModel):
    document: StudioDocument
    prompt: str = Field(min_length=1, max_length=2000)
    count: int = Field(3, ge=1, le=3)


class StudioGenerationResult(StudioModel):
    variants: list[StudioDocument] = Field(min_length=1, max_length=3)
