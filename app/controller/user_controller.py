from http.client import HTTPException
from typing import Dict, List
from fastapi import APIRouter
from uuid import UUID
from app.services.data_access.user import get_users
from pydantic import BaseModel, RootModel

user_controller = APIRouter(
    prefix="/user",
    tags=["user"],
    dependencies=[],
)

@user_controller.post("/get_names")
async def get_names(model: list[UUID]) -> dict[UUID, str]:

    users = await get_users(model)

    if not users:
        raise HTTPException(404, f'User id(s) do not exist')
    
    return dict([(u.id, u.name) for u in users])

