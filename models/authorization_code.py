import base64
from dataclasses import dataclass
import datetime
import random
import secrets
from uuid import UUID
from marshmallow import fields

from helper.model_helper import make_safe_schema

def generate_auth_code(length: int):
    return base64.b64encode(secrets.token_bytes(length)).decode()

@dataclass
class AuthorizationCode:
    '''A token that can be used for authentication'''

    _id: str

    corresponding_user: UUID

    single_use: bool

    valid_until: datetime.datetime


class AuthorizationCodeSchema(make_safe_schema(AuthorizationCode)):

    _id = fields.String()

    corresponding_user = fields.UUID(required=True)

    single_use = fields.Boolean()

    valid_until = fields.AwareDateTime(required = True, default_timezone=datetime.timezone.utc)

@dataclass
class TokenPair:

    token: str

    refresh_token: str

class TokenPairSchema(make_safe_schema(TokenPair)):

    token = fields.String()

    refresh_token = fields.String()
