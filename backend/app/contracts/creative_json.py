from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ActionType, FontWeight

COLOR_PATTERN = r"^#[0-9A-Fa-f]{8}$"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TextStyle(StrictModel):
    fontSize: int | None = Field(None, ge=10, le=40)
    fontWeight: FontWeight | None = None
    textColor: str | None = Field(None, pattern=COLOR_PATTERN, description="#RRGGBBAA")


class Background(StrictModel):
    color: str | None = Field(None, pattern=COLOR_PATTERN, description="#RRGGBBAA")


class Image(StrictModel):
    url: str = Field(description="https-ссылка на изображение")


class ActionLink(StrictModel):
    iOS: str | None = None
    android: str | None = None
    web: str | None = None


class BannerContent(StrictModel):
    title: str | None = Field(
        None, description="Лимит длины зависит от типа: STORY 100, SMART_BANNER 250"
    )
    titleStyle: TextStyle | None = None
    text: str | None = Field(
        None, description="Лимит длины зависит от типа: STORY 500, SMART_BANNER 1000"
    )
    textStyle: TextStyle | None = None
    background: Background | None = None
    image: Image | None = None
    buttonName: str | None = None
    actionType: ActionType
    link: ActionLink | None = Field(
        None,
        description="Обязателен при externalLink/openSmartLink, запрещён при closeCampaign/doneCampaign",
    )
    voiceOver: str | None = Field(None, max_length=200)


# Диапазоны стилей компонентов контента в MVP не валидируются (§2.7), поэтому модели стилей мягче, чем у баннера.
class ComponentTextStyle(StrictModel):
    fontSize: float | None = None
    fontWeight: str | None = None
    textColor: str | None = None


class ComponentStyle(StrictModel):
    backgroundColor: str | None = None


class PromoText(StrictModel):
    role: Literal["text"]
    format: Literal["none", "html"]
    text: str
    textStyle: ComponentTextStyle | None = None


class PromoImage(StrictModel):
    role: Literal["image"]
    url: str
    aspectRatio: float | None = None


class PromoButton(StrictModel):
    role: Literal["button"]
    text: str
    actionType: ActionType
    link: ActionLink | None = None
    textStyle: ComponentTextStyle | None = None
    style: ComponentStyle | None = None


PromoComponent = Annotated[PromoText | PromoImage | PromoButton, Field(discriminator="role")]


class LinearContainer(StrictModel):
    role: Literal["linearContainer"]
    axis: Literal["v"]
    aligns: str | None = None
    style: ComponentStyle | None = None
    components: list[PromoComponent] = Field(min_length=1, max_length=6)


class PromoContent(StrictModel):
    role: Literal["promo"]
    component: LinearContainer
