from pydantic import BaseModel

from app.core.errors import ApiError


class ErrorResponse(BaseModel):
    errors: list[ApiError]
