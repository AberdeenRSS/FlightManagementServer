from functools import lru_cache
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings

connection_string = None

# Provide the mongodb atlas url to connect python to mongodb using pymongo
full_connection_string = None

def get_db() -> AsyncIOMotorDatabase: # type: ignore

    # Case for when there is no global context available
    # e.g. during setup
    client = AsyncIOMotorClient(full_connection_string, uuidRepresentation='standard')
    return client['rocketry4']

def init_app(app: FastAPI):
    global full_connection_string
    connection_string = get_settings().connection_string
    full_connection_string = f"{connection_string}/rocketDatabase1"
