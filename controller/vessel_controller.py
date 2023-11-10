from typing import cast
from uuid import UUID, uuid4
from quart import Blueprint
from quart import request, flash, g, jsonify
from middleware.auth.requireAuth import auth_required, role_required
from quart_schema import QuartSchema, validate_request, validate_response

from models.vessel import VesselSchema, Vessel
from services.auth.jwt_user_info import User, get_user_info
from services.auth.permission_service import has_vessel_permission, modify_vessel_permission
from services.data_access.user import get_user_by_unique_name
from services.data_access.vessel import create_or_update_vessel, get_all_vessels, get_vessel, get_historic_vessel, get_vessel_by_name, update_vessel_without_version_change


vessel_api = Blueprint('vessel', __name__, url_prefix='/vessel')

# Method for a vessel to register
@vessel_api.route("/register", methods = ['POST'])
@role_required('Access.Vessel')
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

    # # Use the identity of the vessel as its id -> Only one entry per authentication code
    # raw_vessel['_id'] = UUID(user_info.unique_id)

    vessel = VesselSchema().load_safe(Vessel, raw_vessel)

    acc = await create_or_update_vessel(vessel)

    return VesselSchema().dumps(acc)

@vessel_api.get("/get_all")
async def get_all():
    """
    Returns all vessels known to server
    ---
    responses:
      200:
        description: All vessels
        schema:
          type: array
          items:
            $ref: "#/definitions/Vessel"
    """

    vessels = await get_all_vessels()
    res = VesselSchema(many=True).dumps(vessels)
    return res

@vessel_api.get("/get/<vessel_id>/<version>")
async def get_vessel_historic(vessel_id: str, version: int):
    """
    Retrieves a historic version of a vessel
    ---
    parameters:
      - name: vessel_id
        required: true
        in: path
        type: string
        description: The id of the vessel
    - name: version
        required: true
        in: path
        type: number
        description: The version of the vessel to get
    responses:
      200:
        description: The resulting vessel (contains the new version that was chosen by the server)
        schema:
          $ref: "#/definitions/Vessel"
      404:
        description: Vessel does not exist

    """

    vessel = await get_vessel(vessel_id)

    if vessel is None:
        return 'Vessel does not exist', 404
    
    if vessel._version == int(version):
        return VesselSchema().dump(vessel)
    
    vessel_historic = await get_historic_vessel(vessel_id, version)

    if vessel_historic is None:
        return 'Vessel does not exist', 404

    vessel = Vessel(_id = vessel_historic._id.id, _version=version, name=vessel_historic.name, parts=vessel_historic.parts)

    return VesselSchema().dump(vessel)

@vessel_api.get("/get_by_name/<name>")
async def get_by_name(name: str):
    vessels = await get_vessel_by_name(name)

    return VesselSchema(many=True).dumps(vessels)

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

@vessel_api.route('/give_permission/<vessel_id>/<unique_user_name>/<permission>')
async def give_permission(vessel_id: str, unique_user_name: str, permission: str):

  vessel = await get_vessel(vessel_id)

  if vessel is None:
      return 'Vessel does not exist', 400
  
  if not has_vessel_permission(vessel, permission):
      return 'You are not authorized to perform this action', 403
  
  other_user = await get_user_by_unique_name(unique_user_name)

  if other_user is None:
      return 'User you are trying to give permission to does not exist', 400
  
  modify_vessel_permission(vessel, permission, other_user._id)

  await update_vessel_without_version_change(vessel)

  return 'success', 200

