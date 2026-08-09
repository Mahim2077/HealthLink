from typing import Annotated
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr


class AdminLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: Annotated[SecretStr, Field(min_length=1, max_length=128)]


class AdminMeResponse(BaseModel):
    user_id: uuid.UUID
    admin_id: uuid.UUID
    email: EmailStr
    first_name: str
    last_name: str
    is_super_admin: bool
