from pydantic import BaseModel


class Transcription(BaseModel):
    text: str


class SynthesisBody(BaseModel):
    text: str
