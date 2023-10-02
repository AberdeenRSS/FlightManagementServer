from typing import Union, cast

from blinker import NamedSignal, Namespace
from quart import current_app
from motor.core import AgnosticCollection

from .mongodb.mongodb_connection import get_db
from models.flight import Flight, FlightSchema

FLIGHT_NEW = 'FLIGHT_NEW'
FLIGHT_UPDATE = 'FLIGHT_UPDATE'

flight_signals = Namespace()

def get_flight_new_signal() -> NamedSignal:
    return flight_signals.signal(FLIGHT_NEW)

def get_flight_update_signal() -> NamedSignal:
    return flight_signals.signal(FLIGHT_UPDATE)

def get_flight_collection() -> AgnosticCollection:
    db = get_db()
    return db['flights']

# Creates or updates the vessel and returns the value written to the database
async def create_or_update_flight(flight: Flight) -> Flight:
    collection = get_flight_collection()
    result = await collection.replace_one({'_id': str(flight._id)}, FlightSchema().dump_single(flight), upsert = True) # type: ignore

    if result.upserted_id is not None:
        get_flight_update_signal().send(current_app._get_current_object(), flight = flight)  # type: ignore
    else:
        get_flight_new_signal().send(current_app._get_current_object(), flight = flight)  # type: ignore

    return flight

async def get_all_flights_for_vessels(_vessel_id: str):
    collection = get_flight_collection()
    raw = await collection.find({'_vessel_id': str(_vessel_id) }).to_list(1000) # type: ignore
    return FlightSchema().load_list_safe(Flight, raw)

async def get_all_flights_for_vessels_by_name(_vessel_id: str, name: str):
    collection = get_flight_collection()
    raw = await collection.find({'_vessel_id': str(_vessel_id), 'name': name }).to_list(1000) # type: ignore
    return FlightSchema().load_list_safe(Flight, raw)

async def get_flight(_id: str) -> Union[Flight, None]:
    collection = get_flight_collection()
    raw = await collection.find({'_id': _id}).to_list(1000) # type: ignore

    if len(raw) > 0:
        return FlightSchema().load_safe(Flight, raw[0])

    return None


    