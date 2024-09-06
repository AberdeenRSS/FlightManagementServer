from dataclasses import dataclass

from pydantic import BaseModel


class RegisterModel(BaseModel):
    name: str

    unique_name: str

    pw: str

class LoginModel(BaseModel):

    unique_name: str

    pw: str

class RefreshTokenModel(BaseModel):
    token: str