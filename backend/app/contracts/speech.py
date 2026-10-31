from pydantic import BaseModel, Field

# Предложение браузера занимает единицы килобайт; ограничение не даёт пересылать в OpenAI большие тела.
MAX_SDP_CHARS = 64 * 1024


class Transcription(BaseModel):
    text: str


class SynthesisBody(BaseModel):
    text: str


class LiveSessionBody(BaseModel):
    sdp: str = Field(min_length=1, max_length=MAX_SDP_CHARS)


class LiveSessionStart(BaseModel):
    sessionId: str
    sdp: str
