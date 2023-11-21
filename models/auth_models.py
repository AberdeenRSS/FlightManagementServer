from dataclasses import dataclass


@dataclass
class RegisterModel:
    name: str

    unique_name: str

    pw: str

@dataclass
class LoginModel:

    unique_name: str

    pw: str