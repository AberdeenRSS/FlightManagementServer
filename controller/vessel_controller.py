from typing import cast
from uuid import UUID, uuid4
from quart import Blueprint
from quart import request, flash, g, jsonify
from middleware.auth.requireAuth import auth_required

from models.vessel import VesselSchema, Vessel
from services.auth.jwt_user_info import User, get_user_info
from services.data_access.vessel import create_or_update_vessel, get_all_vessels



vessel_api = Blueprint('vessel', __name__, url_prefix='/vessel')

# Method for a vessel to register
@vessel_api.route("/register", methods = ['POST'])
@auth_required
async def registerVessel():
    """
    Method to be called by a vessel to register itself. 
    The vessel is supposed to transmit how it is made up so others know what data
    it can provide and what commands it can receive. If a vessel changes
    over time the old version of the vessel will be saved and the new information
    will then be used. All old flights that where performed with a previous version
    of the vessel can therefore still be used with the old version
    ---
    parameters:
      - name: body
        required: true
        in: body
        schema:
          $ref: "#/definitions/Vessel"
        description: The information about the vessel, including what parts it is made out of
    responses:
      200:
        description: The resulting vessel (contains the new version that was chosen by the server)
        schema:
          $ref: "#/definitions/Vessel"
    """

    raw_vessel = cast(dict, await request.get_json())

    user_info = cast(User, get_user_info())
    # Use the identity of the vessel as its id -> Only one entry per authentication code
    raw_vessel['_id'] = UUID(user_info.unique_id)

    vessel = VesselSchema().load_safe(Vessel, raw_vessel)

    acc = await create_or_update_vessel(vessel)

    return VesselSchema().dumps(acc)

@vessel_api.get("/get_all")
@auth_required
async def get_all():
    # """
    # Returns all vessels known to server
    # ---
    # responses:
    #   200:
    #     description: All vessels
    #     schema:
    #       type: array
    #       items:
    #         $ref: "#/definitions/Vessel"
    # """

    vessels = await get_all_vessels()
    res = VesselSchema(many=True).dumps(vessels)
    return res

@vessel_api.route("/get_test_vessels", methods = ['GET'])
async def get_test_vessels():
    """
    Returns a test response. Returned vessel gets a new random uuid
    ---
    tags:
      - vessel
    responses:
      200:
        description: The test vessel
        schema:
          $ref: "#/definitions/Vessel"
    """

    vessel = Vessel(_id = uuid4(), _version = 1)
    vessel.name = 'Test vessel'
    return VesselSchema().dumps(vessel)


