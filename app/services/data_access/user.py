from typing import Any, Collection, Coroutine, Union, cast
from uuid import UUID
from motor.core import AgnosticDatabase, AgnosticCollection
from ...models.user import User
from ...services.data_access.common.collection_managment import get_or_init_collection

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
    result = await collection.replace_one({'_id': user.id}, user.model_dump(by_alias=True), upsert = True) # type: ignore

async def get_user(id: UUID):
    collection = await get_or_init_user_collection()

    raw = await collection.find({'_id': id}).to_list(1) # type: ignore

    if len(raw) > 0:
        return User(**raw[0])
    
    return None

async def get_users(ids: Collection[UUID]) -> list[User]:

    collection = await get_or_init_user_collection()
    
    string_ids = [str(id) for id in ids]

    raw = await collection.find({'_id': {'$in': string_ids }}).to_list(1000)

    return [User(**r) for r in raw]

async def get_user_by_unique_name(name: str):
    collection = await get_or_init_user_collection()

    raw = await collection.find({'unique_name': name}).to_list(1) # type: ignore

    if len(raw) > 0:
        return User(**raw[0])
    
    return None

async def get_users_by_name(name: str):
    collection = await get_or_init_user_collection()

    raw = await collection.find({'name': name}).to_list(100) # type: ignore

    return [User(**r) for r in raw]
