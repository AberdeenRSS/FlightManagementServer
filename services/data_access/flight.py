from typing import Union, cast

from .mongodb.mongodb_connection import get_db
from models.flight import Flight, FlightSchema

def get_flight_collection():
    db = get_db()
    return db['flights']

# Creates or updates the vessel and returns the value written to the database
def create_or_update_flight(flight: Flight) -> Flight:
    collection = get_flight_collection()
    result = collection.replace_one({'_id': str(flight._id)}, FlightSchema().dump_single(flight), upsert = True)

    return flight

def get_all_flights_for_vessels(_vessel_id: str):
    collection = get_flight_collection()
    raw = list(collection.find({'_vessel_id': str(_vessel_id) }))
    return FlightSchema().load_list_safe(Flight, raw)

def get_flight(_id: str) -> Union[Flight, None]:
    collection = get_flight_collection()
    raw = list(collection.find({'_id': _id}))

    if len(raw) > 0:
        return FlightSchema().load_safe(Flight, raw[0])

    return None


    