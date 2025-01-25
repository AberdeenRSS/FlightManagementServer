from typing import Union, cast
from uuid import UUID

from blinker import NamedSignal, Namespace
from motor.core import AgnosticCollection

from .mongodb.mongodb_connection import get_db
from app.models.flight import Flight

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
    result = await collection.replace_one({'_id': flight.id}, flight.model_dump(by_alias=True), upsert = True) # type: ignore

    if result.upserted_id is not None:
        get_flight_update_signal().send(None, flight = flight)  # type: ignore
    else:
        get_flight_new_signal().send(None, flight = flight)  # type: ignore

    return flight

async def get_all_flights_for_vessels(_vessel_id: UUID):
    collection = get_flight_collection()
    raw = await collection.find({'_vessel_id': _vessel_id }).to_list(1000) # type: ignore
    return [Flight(**r) for r in raw]

async def get_all_flights_for_vessels_by_name(_vessel_id: UUID, name: str):
    collection = get_flight_collection()
    raw = await collection.find({'_vessel_id': _vessel_id, 'name': name }).to_list(1000) # type: ignore
    return [Flight(**r) for r in raw]

async def get_flight(_id: UUID) -> Union[Flight, None]:
    collection = get_flight_collection()
    raw = await collection.find({'_id': _id}).to_list(1000) # type: ignore

    if len(raw) > 0:
        return Flight(**raw[0])

    return None

async def delete_flight_by_id(_id:UUID) -> bool:
    collection = get_flight_collection()
    result = await collection.delete_one({'_id': _id})
    return result.deleted_count > 0

    