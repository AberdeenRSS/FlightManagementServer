from typing import Union, cast
from json import dumps
from motor.core import AgnosticCollection, AgnosticDatabase

from services.data_access.common.collection_managment import get_or_init_collection

from .mongodb.mongodb_connection import get_db
from models.vessel import Vessel, VesselHistoric, VesselHistoricKey, VesselSchema, VesselHistoricSchema

def get_vessel_collection() -> AgnosticCollection:
    db = get_db()
    return db['vessels']

def get_historic_vessel_collection() -> AgnosticCollection:
    db = get_db()
    return db['vessels_historic']

async def update_vessel_without_version_change(vessel: Vessel):
    vessel_collection = get_vessel_collection()

    result = await vessel_collection.replace_one({'_id': str(vessel._id)}, cast(dict, VesselSchema().dump(vessel)), upsert = True) # type: ignore


# Creates or updates the vessel and returns the value written to the database
async def create_or_update_vessel(vessel: Vessel) -> Vessel:
    vessel_collection = get_vessel_collection()

    # Check if the vessel already exists, if so put the old version in the
    # Old vessel collection
    vessels_raw = await vessel_collection.find({'_id': str(vessel._id)}).to_list(1000) # type: ignore

    if len(vessels_raw) > 0:
        old_vessel = VesselSchema().load_safe(Vessel, vessels_raw[0])

        # Put the versions equal to ensure comparison works
        vessel._version = old_vessel._version

        # Compare the two vessels, if they are equal don't update
        # the database and don't increase the version
        if VesselSchema().dumps(old_vessel) == VesselSchema().dumps(vessel):
            return old_vessel

        # Update the version of the current vessel to be one more than the current one
        vessel._version = old_vessel._version + 1

        historic_vessel = VesselHistoric(_id = VesselHistoricKey(version=old_vessel._version, id=old_vessel._id), _version=old_vessel._version, name=old_vessel.name, parts=old_vessel.parts)

        # Put the historic vessel in the historic collection
        await get_historic_vessel_collection().insert_one(cast(dict, VesselHistoricSchema().dump(historic_vessel))) # type: ignore
    else:
        # If this is the first time this vessel appears put it as version 0
        vessel._version = 1

    # Update or create the current vessel
    result = await vessel_collection.replace_one({'_id': str(vessel._id)}, cast(dict, VesselSchema().dump(vessel)), upsert = True) # type: ignore

    return vessel

# Get a list of all vessels
async def get_all_vessels() -> list[Vessel]:
    vessel_collection = get_vessel_collection()
    vessels_raw = await vessel_collection.find({}).to_list(2000) # type: ignore

    return VesselSchema().load_list_safe(Vessel, vessels_raw)

# Gets the current version of the vessel
async def get_vessel(_id: str) -> Union[Vessel, None]:
    vessel_collection = get_vessel_collection()
    vessels_raw = await vessel_collection.find({"_id": _id}).to_list(1) # type: ignore

    if len(vessels_raw) > 0:
        return VesselSchema().load_safe(Vessel, vessels_raw[0])

    return None

async def get_vessel_by_name(name: str):
    vessel_collection = get_vessel_collection()
    vessels_raw = await vessel_collection.find({"name": name}).to_list(1000)

    return VesselSchema().load_list_safe(Vessel, vessels_raw)


# Gets an old version of the vessel
async def get_historic_vessel(_id: str, _version: int):
    vessel_collection = get_historic_vessel_collection()
    vessels_raw = await vessel_collection.find({'_id.version': int(_version), '_id.id': _id}).to_list(1000) # type: ignore
    if len(vessels_raw) > 0:
        return VesselHistoricSchema().load_safe(VesselHistoric, vessels_raw[0])

    return None
