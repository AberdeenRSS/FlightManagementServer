from dataclasses import dataclass, field
from typing import Union
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from hashlib import sha256
import base64

def hash_password(user_id: UUID, pw: str):
    as_bytes = (pw + str(user_id)).encode()
    return base64.b64encode(sha256(as_bytes).digest()).decode('utf-8')

class User(BaseModel):

    id: UUID = Field(..., alias='_id')

    pw: Union[str, None]
    ''' Password or access token (salted and hashed) '''

    unique_name: str = ""
    '''unique name of the user (e.g. an email address)'''

    name: str = ""

    roles: list[str]

