from pydantic import BaseModel


class UploadedImage(BaseModel):
    url: str
