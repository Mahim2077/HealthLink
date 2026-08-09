from typing import Literal

from pydantic import BaseModel, PositiveInt

from app.auth.constants import Portal


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: PositiveInt
    portal: Portal


class MessageResponse(BaseModel):
    detail: str
