from datetime import datetime
from typing import cast
from flask import current_app
from pymongo import collection, database
from blinker import Namespace, NamedSignal

from models.command import CommandSchema
from models.flight_measurement import FlightMeasurementSchema
from services.data_access.common.collection_managment import get_or_init_collection

#region Signals

COMMAND_NEW = 'COMMAND_NEW'
COMMAND_UPDATE = 'COMMAND_UPDATE'

command_signals = Namespace()

def get_command_new_signal() -> NamedSignal:
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

# Inserts new measured flight data
def insert_commands(commands: list[CommandSchema], flight_id: str):

    collection = get_or_init_command_collection(flight_id)

    commands_raw = cast(list[dict], export_list(commands))

    # Convert into a datetime object, because mongodb
    # suddenly wants datetime objects instead of strings here
    for m in commands_raw:
        m['create_time'] = datetime.fromisoformat(m['create_time'])
        m['dispatch_time'] = datetime.fromisoformat(m['dispatch_time'])
        m['receive_time'] = datetime.fromisoformat(m['receive_time'])
        m['complete_time'] = datetime.fromisoformat(m['complete_time'])

    res = collection.insert_many(commands_raw)

    get_command_new_signal().send(current_app._get_current_object(), flight_id=flight_id, commands = commands)  # type: ignore


def get_commands_in_range(flight_id: str, start: datetime, end: datetime) -> list[CommandSchema]:
    collection = get_or_init_command_collection(flight_id)

    # Get all measurements in the date range
    res = list(collection.find({'create_time': { '$gte': start, '$lt': end }  }).limit(1000))

    return import_list(res, CommandSchema)

# def get_not_received_commands(flight_id: str):
#     collection = get_or_init_command_collection(flight_id)

#     result = list(collection.find({'status': }))

#     return import_list(result, Command)

