import asyncio
from datetime import datetime
from typing import Any, Collection, Coroutine, Union, cast
from uuid import UUID
from blinker import Namespace, NamedSignal
from motor.core import AgnosticDatabase, AgnosticCollection
from app.models.command import Command
from app.services.data_access.common.collection_managment import get_or_init_collection

#region Signals

COMMAND_NEW = 'COMMAND_NEW'
COMMAND_UPDATE = 'COMMAND_UPDATE'

command_signals = Namespace()

def get_commands_new_signal() -> NamedSignal:
    return command_signals.signal(COMMAND_NEW)

def get_command_update_signal() -> NamedSignal:
    return command_signals.signal(COMMAND_UPDATE)

#endregion

#region Collection management

async def get_or_init_command_collection():

    async def create_collection(db: AgnosticDatabase, n: str) -> AgnosticCollection:
        collection = db['command']
        await collection.create_index('create_time', unique=False) # type: ignore
        await collection.create_index('_command_type', unique =False) # type: ignore
        await collection.create_index('_part_id', unique =False) # type: ignore
        await collection.create_index('_flight_id', unique =False) # type: ignore
        return collection

    return await get_or_init_collection(f'command', create_collection)

#endregion

# Removes all bson objects from the returned measurement
def from_db_object(command: dict):

    del command['_flight_id']

    return command

def to_db_object(flight_id: UUID, command_raw: dict):
    command_raw['_flight_id'] = flight_id
    return command_raw


# Inserts new measured flight data
async def insert_commands(commands: list[Command], flight_id: UUID, from_client: bool):

    collection = await get_or_init_command_collection()

    # Convert into a datetime object, because mongodb
    # suddenly wants datetime objects instead of strings here
    commands_raw = [to_db_object(flight_id, c.model_dump(by_alias=True)) for c in commands]

    res = await collection.insert_many(commands_raw) # type: ignore

    get_commands_new_signal().send(None, flight_id=flight_id, commands = commands, from_client = from_client)  # type: ignore

# Inserts new measured flight data
async def insert_or_update_commands(commands: Collection[Command], flight_id: UUID, from_client: bool):

    collection = await get_or_init_command_collection()

    # Convert into a datetime object, because mongodb
    # suddenly wants datetime objects instead of strings here
    commands_raw = [to_db_object(flight_id, c.model_dump(by_alias=True)) for c in commands]

    tasks = list[asyncio.Task]()

    for c in commands_raw:
       task = collection.replace_one({'_id': c['_id']}, c, upsert=True)  # type: ignore
       tasks.append(task)

    await asyncio.wait(tasks)

    get_command_update_signal().send(None, flight_id=flight_id, commands = commands, from_client = from_client)  # type: ignore


async def get_commands_in_range(flight_id: UUID, start: datetime, end: datetime, part: Union[None, UUID] = None, command_type: Union[None, str] = None) -> list[Command]:
    """
    Returns the list of commands in a certain range, regardless of their state
    
    Additional kwargs -
    """
    collection = await get_or_init_command_collection()

    query: dict[str, Any] = {
        'create_time': { '$gte': start, '$lt': end },
        '_flight_id': { '$eq': flight_id }
    }

    if command_type is not None:
        query['_command_type'] = { '$eq': command_type }

    if part is not None:
        query['_part_id'] = { '$eq': part }

    # Get all measurements in the date range
    res = await collection.find(query).to_list(1000) # type: ignore

    logic_objects = [from_db_object(r) for r in res]

    return [Command(**r) for r in logic_objects]


