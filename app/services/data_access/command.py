import asyncio
from datetime import datetime
from typing import Any, Collection, Coroutine, Union, cast
from quart import current_app
from blinker import Namespace, NamedSignal
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from motor.core import AgnosticDatabase, AgnosticCollection

from models.command import CommandSchema, Command
from models.flight_measurement import FlightMeasurementSchema
from services.data_access.common.collection_managment import get_or_init_collection

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
        return await db.create_collection(n, timeseries = {
            'timeField': 'create_time',
            'granularity': 'seconds',
            'metaField': 'metadata'
        }) # type: ignore

    return await get_or_init_collection(f'commands', create_collection)

#endregion


# Removes all bson objects from the returned measurement
def from_db_object(command: dict):
    if 'create_time' in command:
        command['create_time'] = cast(datetime, command['create_time']).isoformat()
    
    command['_part_id'] = command['metadata']['part_id']
    command['_command_type'] = command['metadata']['command_type']

    del command['metadata']

def to_db_object(flight_id: str, command_raw: dict):
    command_raw['create_time'] = datetime.fromisoformat(command_raw['create_time'])
    command_raw['metadata'] = { 'flight_id': flight_id, 'part_id': command_raw['_part_id'], 'command_type': command_raw['_command_type'] }
    del command_raw['_part_id']
    del command_raw['_command_type']

# Inserts new measured flight data
async def insert_commands(commands: list[Command], flight_id: str, from_client: bool):

    collection = await get_or_init_command_collection()

    # Convert into a datetime object, because mongodb
    # suddenly wants datetime objects instead of strings here
    commands_raw = CommandSchema(many=True).dump_list(commands)

    for c in commands_raw:
        to_db_object(flight_id, c)

    res = await collection.insert_many(commands_raw) # type: ignore

    get_commands_new_signal().send(current_app._get_current_object(), flight_id=flight_id, commands = commands, from_client = from_client)  # type: ignore

# Inserts new measured flight data
async def insert_or_update_commands(commands: Collection[Command], flight_id: str, from_client: bool):

    collection = await get_or_init_command_collection()

    # Convert into a datetime object, because mongodb
    # suddenly wants datetime objects instead of strings here
    commands_raw = cast(list[dict[str, Any]], CommandSchema().dump_list(commands))

    for c in commands_raw:
        to_db_object(flight_id, c) 

    tasks = list[Coroutine]()

    for c in commands_raw:
       cast(Coroutine, tasks.append(collection.update_one({'_id': c['_id']}, commands_raw, upsert=True))) # type: ignore

    await asyncio.wait(tasks)


    get_command_update_signal().send(current_app._get_current_object(), flight_id=flight_id, commands = commands, from_client = from_client)  # type: ignore


async def get_commands_in_range(flight_id: str, start: datetime, end: datetime, part: Union[None, str] = None, command_type: Union[None, str] = None) -> list[Command]:
    """
    Returns the list of commands in a certain range, regardless of their state
    
    Additional kwargs -
    """
    collection = await get_or_init_command_collection()

    query: dict[str, Any] = {
        'create_time': { '$gte': start, '$lt': end },
        'metadata.flight_id': { '$eq': flight_id }
    }

    if command_type is not None:
        query['metadata.command_type'] = { '$eq': command_type }

    if part is not None:
        query['metadata.part_id'] = { '$eq': part }


    # Get all measurements in the date range
    res = await collection.find(query).to_list(1000) # type: ignore

    logic_objects = [from_db_object(r) for r in res]

    return CommandSchema().load_list_safe(Command, res)


