from datetime import datetime
from typing import Any, Union, cast
from flask import current_app
from pymongo import collection, database
from blinker import Namespace, NamedSignal

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


def get_or_init_command_collection(flight_id: str) -> collection.Collection:

    def create_collection(db: database.Database, n: str):
        return db.create_collection(n, timeseries = {
            'timeField': 'create_time',
            'granularity': 'seconds'
        })

    return get_or_init_collection(f'command_{flight_id.replace("-", "")}', create_collection)

#endregion


# Removes all bson objects from the returned measurement
def debsonify_commands(commands: list[dict]):
    for r in commands:
        if 'create_time' in r:
            r['create_time'] = cast(datetime, r['create_time']).isoformat()

# Inserts new measured flight data
def insert_commands(commands: list[Command], flight_id: str):

    collection = get_or_init_command_collection(flight_id)

    # Convert into a datetime object, because mongodb
    # suddenly wants datetime objects instead of strings here
    commands_raw = CommandSchema(many=True).dump_list(commands)

    for m in commands_raw:
        m['create_time'] = datetime.fromisoformat(m['create_time'])

    res = collection.insert_many(commands_raw)

    get_commands_new_signal().send(current_app._get_current_object(), flight_id=flight_id, commands = commands)  # type: ignore

# Inserts new measured flight data
def update_command(command: Command, flight_id: str):

    collection = get_or_init_command_collection(flight_id)

    # Convert into a datetime object, because mongodb
    # suddenly wants datetime objects instead of strings here
    command_raw = cast(dict[str, Any], CommandSchema().dump(command))

    command_raw['create_time'] = datetime.fromisoformat(command_raw['create_time'])

    res = collection.replace_one({"_id": command._id}, command_raw)

    get_command_update_signal().send(current_app._get_current_object(), flight_id=flight_id, command = command)  # type: ignore

def get_commands_in_range(flight_id: str, start: datetime, end: datetime, part: Union[None, str] = None, command_type: Union[None, str] = None) -> list[Command]:
    """
    Returns the list of commands in a certain range, regardless of their state
    
    Additional kwargs -
    """
    collection = get_or_init_command_collection(flight_id)

    query: dict[str, Any] = {
        'create_time': { '$gte': start, '$lt': end }  
    }

    if command_type is not None:
        query['command_type'] = { '$eq': command_type }

    if part is not None:
        query['part'] = { '$eq': part }


    # Get all measurements in the date range
    res = list(collection.find(query).limit(1000))

    debsonify_commands(res)

    return CommandSchema().load_list_safe(Command, res)


