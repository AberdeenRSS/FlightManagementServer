from motor.core import AgnosticCollection
from ...models.authorization_code import AuthorizationCode
from ...services.data_access.common.collection_managment import get_or_init_collection
from motor.core import AgnosticDatabase, AgnosticCollection


AUTH_CODE_COLLECTION = 'auth_codes'

async def get_or_init_auth_code_collection():

    async def create_collection(db: AgnosticDatabase, n: str) -> AgnosticCollection:
        collection = db[AUTH_CODE_COLLECTION]
        await collection.create_index('corresponding_user') # type: ignore
        return collection

    return await get_or_init_collection(AUTH_CODE_COLLECTION, create_collection)


async def create_auth_code(code: AuthorizationCode):

    collection = await get_or_init_auth_code_collection()

    await collection.replace_one({'_id': code.id}, code.model_dump(by_alias=True), upsert = True) # type: ignore

async def get_code(id: str):
    collection = await get_or_init_auth_code_collection()

    raw = await collection.find({'_id': id}).to_list(1) # type: ignore

    if len(raw) < 1:
        return None
    
    return AuthorizationCode(**raw[0])

async def get_auth_codes_for_user(user_id: str):

    collection = await get_or_init_auth_code_collection()

    raw = await collection.find({'corresponding_user': user_id}).to_list(1000)

    return [AuthorizationCode(**r) for r in raw]

async def delete_code(id: str):
    collection = await get_or_init_auth_code_collection()

    result = await collection.delete_one({'_id': id}) # type: ignore

    return result.deleted_count > 0    