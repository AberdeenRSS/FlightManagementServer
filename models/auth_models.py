from dataclasses import dataclass

from pydantic import BaseModel


@dataclass
class RegisterModel(BaseModel):
    name: str

    unique_name: str

    pw: str

@dataclass
class LoginModel(BaseModel):

    unique_name: str

    pw: str