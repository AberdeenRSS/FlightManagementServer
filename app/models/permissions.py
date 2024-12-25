from pydantic import BaseModel

class Permission(BaseModel):
    unique_user_name: str
    permission: str