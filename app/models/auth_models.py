from dataclasses import dataclass
from typing import Union
from uuid import UUID

from pydantic import BaseModel, Field


class RegisterModel(BaseModel):
    name: str

    unique_name: str

    pw: str

class LoginModel(BaseModel):

    unique_name: str

    pw: str

class RefreshTokenModel(BaseModel):
    token: str

    resources: list[tuple[str, UUID]] = Field(default_factory=list)