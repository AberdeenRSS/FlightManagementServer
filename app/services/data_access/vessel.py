import json
from typing import Union
from uuid import UUID
from motor.core import AgnosticCollection

from app.models.vessel import Vessel, VesselHistoric, VesselHistoricKey
from app.services.data_access.flight import bulk_delete_flights_by_ids, get_all_flights_for_vessels
from .mongodb.mongodb_connection import get_db
import asyncio

def get_vessel_collection() -> AgnosticCollection:
    db = get_db()
    return db['vessels']

def get_historic_vessel_collection() -> AgnosticCollection:
    db = get_db()
    return db['vessels_historic']

async def update_vessel_without_version_change(vessel: Vessel):
    vessel_collection = get_vessel_collection()

    result = await vessel_collection.replace_one({'_id': vessel.id}, vessel.model_dump(by_alias=True), upsert = True) # type: ignore


# Creates or updates the vessel and returns the value written to the database
async def create_or_update_vessel(vessel: Vessel) -> Vessel:
    vessel_collection = get_vessel_collection()

    # Check if the vessel already exists, if so put the old version in the
    # Old vessel collection
    vessels_raw = await vessel_collection.find({'_id': vessel.id}).to_list(1000) # type: ignore

    if len(vessels_raw) > 0:
        old_vessel = Vessel(**vessels_raw[0])

        # Put the versions equal to ensure comparison works
        vessel.version = old_vessel.version

        # Use the name already in the DB it is the one the user set up
        vessel.name = old_vessel.name

        vessel.permissions = old_vessel.permissions

        # Compare the two vessels, if they are equal don't update
        # the database and don't increase the version
        if old_vessel.model_dump_json() == vessel.model_dump_json():
            return old_vessel

        # Update the version of the current vessel to be one more than the current one
        vessel.version = old_vessel.version + 1

        historic_vessel = VesselHistoric(_id = VesselHistoricKey(version=old_vessel.version, id=old_vessel.id), _version=old_vessel.version, name=old_vessel.name, parts=old_vessel.parts)

        # Put the historic vessel in the historic collection
        await get_historic_vessel_collection().insert_one(historic_vessel.model_dump(by_alias=True)) # type: ignore
    else:
        # If this is the first time this vessel appears put it as version 0
        vessel.version = 1

    # Update or create the current vessel
    result = await vessel_collection.replace_one({'_id': vessel.id}, vessel.model_dump(by_alias=True), upsert = True) # type: ignore

    return vessel

# Get a list of all vessels
async def get_all_vessels() -> list[Vessel]:
    vessel_collection = get_vessel_collection()
    vessels_raw = await vessel_collection.find({}).to_list(2000) # type: ignore

    return [Vessel(**v) for v in vessels_raw]

# Gets the current version of the vessel
async def get_vessel(_id: UUID) -> Union[Vessel, None]:
    vessel_collection = get_vessel_collection()
    vessels_raw = await vessel_collection.find({"_id": _id}).to_list(1) # type: ignore

    if len(vessels_raw) > 0:
        return Vessel(**vessels_raw[0])

    return None

async def get_vessel_by_name(name: str):
    vessel_collection = get_vessel_collection()
    vessels_raw = await vessel_collection.find({"name": name}).to_list(1000)

    return [Vessel(**v) for v in vessels_raw]


# Gets an old version of the vessel
async def get_historic_vessel(_id: UUID, _version: int):
    vessel_collection = get_historic_vessel_collection()
    vessels_raw = await vessel_collection.find({'_id.version': int(_version), '_id.id': _id}).to_list(1000) # type: ignore
    if len(vessels_raw) > 0:
        return VesselHistoric(**vessels_raw[0])

    return None

async def delete_vessel_by_id(_id:UUID) -> bool:
    """
    Deleting a vessel by id deletes the vessel, it's historic versions, 
    all flights associated with it and all data with those flights, including flight measurements and commands
    """
    vessel_collection = get_vessel_collection()

    # Get all flights associated with the vessel
    flights = await get_all_flights_for_vessels(_id)
    flight_ids = [flight.id for flight in flights]

    if flight_ids:
        results = await asyncio.gather(
            bulk_delete_flights_by_ids(flight_ids),
            delete_all_historic_vessels(_id),
            vessel_collection.delete_one({'_id': _id})
        )
    else:
        results = await asyncio.gather(
            delete_all_historic_vessels(_id),
            vessel_collection.delete_one({'_id': _id})
        )
    return results[-1].deleted_count > 0


async def delete_historic_vessel(_id:UUID, _version:int):
    vessel_collection = get_historic_vessel_collection()

    result = await vessel_collection.delete_one({'_id.version': int(_version), '_id.id': _id})

    return result.deleted_count > 0
    
async def delete_all_historic_vessels(_id: UUID) -> bool:
    """
    Deletes all historic vessels for a vessel of _id
    """
    vessel_collection = get_historic_vessel_collection()
    
    result = await vessel_collection.delete_many({
        '_id.id': _id
    })
    
    return result.deleted_count > 0