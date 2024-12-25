import base64
from dataclasses import dataclass
import datetime
import random
import secrets
from uuid import UUID
from pydantic import BaseModel, Field
from app.helper.datetime_model import AwareDatetimeModel


def generate_auth_code(length: int):
    return base64.b64encode(secrets.token_bytes(length)).decode()


class AuthorizationCode(AwareDatetimeModel):
    '''A token that can be used for authentication'''

    id: str = Field(..., alias='_id')

    corresponding_user: UUID

    single_use: bool

    valid_until: datetime.datetime


class CreateAuthorizationCode(AwareDatetimeModel):

    valid_until: datetime.datetime

class TokenPair(BaseModel):

    token: str

    refresh_token: str

