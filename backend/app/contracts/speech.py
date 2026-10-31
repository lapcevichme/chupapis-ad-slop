from pydantic import BaseModel


class Transcription(BaseModel):
    text: str
