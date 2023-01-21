from typing import Union
from json import dumps

from helper.model_helper import import_list
from .mongodb.mongodb_connection import get_db
from models.vessel import Vessel

def get_vessel_collection():
    db = get_db()
    return db['vessels']

def get_historic_vessel_collection():
    db = get_db()
    return db['vessels_historic']

# Creates or updates the vessel and returns the value written to the database
def create_or_update_vessel(vessel: Vessel) -> Vessel:
    vessel_collection = get_vessel_collection()

    # Check if the vessel already exists, if so put the old version in the
    # Old vessel collection
    vessels_raw = list(vessel_collection.find({'_id': str(vessel._id)}))

    if len(vessels_raw) > 0:
        old_vessel = Vessel(vessels_raw[0])

        # Put the versions equal to ensure comparison works
        vessel._version = old_vessel._version

        # Compare the two vessels, if they are equal don't update
        # the database and don't increase the version
        if dumps(old_vessel.to_primitive()) == dumps(vessel.to_primitive()):
            return old_vessel

        # Update the version of the current vessel to be one more than the current one
        vessel._version = old_vessel._version + 1

        # Put the historic vessel in the historic collection
        get_historic_vessel_collection().insert_one(old_vessel.to_primitive())
    else:
        # If this is the first time this vessel appears put it as version 0
        vessel._version = 1

    # Update or create the current vessel
    result = vessel_collection.replace_one({'_id': str(vessel._id)}, vessel.to_primitive(), upsert = True)

    return vessel

# Get a list of all vessels
def get_all_vessels() -> list[Vessel]:
    vessel_collection = get_vessel_collection()
    vessels_raw = list(vessel_collection.find({}))

    return import_list(vessels_raw, Vessel)

# Gets the current version of the vessel
def get_vessel(_id: str) -> Union[Vessel, None]:
    vessel_collection = get_vessel_collection()
    vessels_raw = list(vessel_collection.find({"_id": _id}))

    if len(vessels_raw) > 0:
        return Vessel(vessels_raw[0])

    return None

# Gets an old version of the vessel
def get_historic_vessel(_id: str, _version: int):
    vessel_collection = get_historic_vessel_collection()
    vessels_raw = list(vessel_collection.find({"_id": _id, "_version": _version}))
    if len(vessels_raw) > 0:
        return Vessel(vessels_raw[0])

    return None
