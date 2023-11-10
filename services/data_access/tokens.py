from typing import Union, cast

from blinker import NamedSignal, Namespace
from quart import current_app
from motor.core import AgnosticCollection
from models.token import Token, TokenSchema

from .mongodb.mongodb_connection import get_db

def get_token_collection() -> AgnosticCollection:
    db = get_db()
    return db['tokens']

async def create_token(token: Token):

    collection = get_token_collection()

    await collection.replace_one({'_id': str(token._id)}, TokenSchema().dump_single(token), upsert = True) # type: ignore

async def get_token(id: str):
    collection = get_token_collection()

    raw = await collection.find({'_id': id}).to_list(1) # type: ignore

    if len(raw) < 1:
        return None
    
    return TokenSchema().load_safe(Token, raw[0])

async def delete_token(id: str):
    collection = get_token_collection()

    result = await collection.delete_one({'_id': id}) # type: ignore

    print(result)
    