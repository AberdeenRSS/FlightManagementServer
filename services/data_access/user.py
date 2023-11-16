import asyncio
from datetime import datetime
from typing import Any, Collection, Coroutine, Union, cast
from uuid import UUID
from quart import current_app
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from motor.core import AgnosticDatabase, AgnosticCollection

from models.user import User, UserSchema
from services.data_access.common.collection_managment import get_or_init_collection

#region Signals

#endregion

#region Collection management


async def get_or_init_user_collection():

    async def create_collection(db: AgnosticDatabase, n: str) -> AgnosticCollection:
        collection = db['user']
        await collection.create_index('name', unique=False) # type: ignore
        await collection.create_index('unique_name', unique = True) # type: ignore
        return collection

    return await get_or_init_collection(f'user', create_collection)

#endregion

async def create_or_update_user(user: User):

    collection = await get_or_init_user_collection()
    result = await collection.replace_one({'_id': str(user._id)}, UserSchema().dump_single(user), upsert = True) # type: ignore

async def get_user(id: UUID):
    collection = await get_or_init_user_collection()

    raw = await collection.find({'_id': str(id)}).to_list(1) # type: ignore

    if len(raw) > 0:
        return UserSchema().load_safe(User, raw[0])
    
    return None

async def get_user_by_unique_name(name: str):
    collection = await get_or_init_user_collection()

    raw = await collection.find({'unique_name': name}).to_list(1) # type: ignore

    if len(raw) > 0:
        return UserSchema().load_safe(User, raw[0])
    
    return None

async def get_users_by_name(name: str):
    collection = await get_or_init_user_collection()

    raw = await collection.find({'name': name}).to_list(100) # type: ignore

    return UserSchema().load_list_safe(User, raw)
