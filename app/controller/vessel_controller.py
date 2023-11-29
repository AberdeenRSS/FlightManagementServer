import datetime
from typing import cast
from uuid import UUID, uuid4
from quart import Blueprint
from quart import request, flash, g, jsonify
from middleware.auth.requireAuth import auth_required, role_required, use_auth
from quart_schema import QuartSchema, document_response, tag, validate_request, validate_response
from models.authorization_code import AuthorizationCode, AuthorizationCodeSchema, generate_auth_code
from models.user import User

from pydantic import RootModel

from models.vessel import VesselSchema, Vessel
from services.auth.jwt_user_info import get_user_info
from services.auth.permission_service import has_vessel_permission, modify_vessel_permission
from services.data_access.auth_code import create_auth_code, get_auth_codes_for_user
from services.data_access.user import create_or_update_user, get_user_by_unique_name
from services.data_access.vessel import create_or_update_vessel, get_all_vessels, get_vessel, get_historic_vessel, get_vessel_by_name, update_vessel_without_version_change

vessel_api = Blueprint('vessel', __name__, url_prefix='/vessel')

# Method for a vessel to register
@vessel_api.route("/register", methods = ['POST'])
@auth_required
@role_required('vessel')
@validate_request(Vessel)
@validate_response(Vessel)
async def registerVessel(data: Vessel):
    """
    Method to be called by a vessel to register itself. 
    The vessel is supposed to transmit how it is made up so others know what data
    it can provide and what commands it can receive. If a vessel changes
    over time the old version of the vessel will be saved and the new information
    will then be used. All old flights that where performed with a previous version
    of the vessel can therefore still be used with the old version
    """

    user = get_user_info()

    if user is None or UUID(user._id) != data._id:
        return 'The vessel id has to match the current user id', 403

    acc = await create_or_update_vessel(data)

    return acc

@vessel_api.get("/get_all")
@use_auth
@document_response(RootModel[list[Vessel]])
@tag(['vessel'])
async def get_all():
    """
    Returns all vessels known to server
    """

    vessels = await get_all_vessels()
    res = [v for v in vessels if has_vessel_permission(v, 'view')]
    return res

@vessel_api.get("/get/<vessel_id>/<version>")
@use_auth
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
    
    if not has_vessel_permission(vessel, 'view'):
        return 'You don\'t have permission to view this vessel', 403
    
    if vessel._version == int(version):
        return VesselSchema().dump(vessel)
    
    vessel_historic = await get_historic_vessel(vessel_id, version)

    if vessel_historic is None:
        return 'Vessel does not exist', 404

    vessel = Vessel(_id = vessel_historic._id.id, _version=version, name=vessel_historic.name, parts=vessel_historic.parts)

    return VesselSchema().dump(vessel)

@vessel_api.get("/get_by_name/<name>")
@use_auth
async def get_by_name(name: str):
    vessels = await get_vessel_by_name(name)

    return VesselSchema(many=True).dump([v for v in vessels if has_vessel_permission(v, 'view')])

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
    return VesselSchema().dump(vessel)

@vessel_api.route('/set_permission/<vessel_id>/<unique_user_name>/<permission>', methods=['POST'])
@use_auth
async def set_permission(vessel_id: str, unique_user_name: str, permission: str):

  vessel = await get_vessel(vessel_id)

  if vessel is None:
      return 'Vessel does not exist', 404
  
  if not has_vessel_permission(vessel, 'owner'):
      return 'You are not authorized to perform this action', 403
  
  other_user = await get_user_by_unique_name(unique_user_name)

  if other_user is None:
      return 'User you are trying to give permission to does not exist', 400
  
  modify_vessel_permission(vessel, permission, other_user._id)

  await update_vessel_without_version_change(vessel)

  return 'success', 200

@vessel_api.route('/create_vessel/<name>', methods=['POST'])
@auth_required
async def create_vessel(name: str):
    '''
    Creates a new empty vessel with the current user as the owner.
    A auth token can then be created for the vessel
    '''
    
    user = get_user_info()
    if user is None:
        return 'Unauthorized', 401

    permissions = dict()
        
    permissions[user._id] = 'owner'
    
    vessel = Vessel(uuid4(), 0, name, list(), permissions, None)

    result_vessel = await create_or_update_vessel(vessel)

    vessel_user = User(result_vessel._id, None, str(result_vessel._id), name, ['vessel'])

    await create_or_update_user(vessel_user)

    return VesselSchema().dump(result_vessel)
    

@vessel_api.route('/create_auth_code/<vessel_id>/<valid_until>', methods=['POST'])
@use_auth
async def create_authorization_code(vessel_id: UUID, valid_until: str):
    
  vessel = await get_vessel(str(vessel_id))

  valid_until_datetime = datetime.datetime.fromisoformat(valid_until)

  if vessel is None:
      return 'Vessel does not exist', 404
  
  if not has_vessel_permission(vessel, 'owner'):
      return 'You are not authorized to perform this action', 403
  
  if  valid_until_datetime.timestamp() > (datetime.datetime.utcnow() + datetime.timedelta(266)).timestamp():
      return 'Maximum allowed date the token is valid until is one year', 400
  
  code = AuthorizationCode(generate_auth_code(256), vessel_id, False, valid_until_datetime)

  await create_auth_code(code)

  return AuthorizationCodeSchema().dump(code)
  
@vessel_api.route('/get_auth_codes/<vessel_id>', methods=['GET'])
@use_auth
async def get_auth_codes(vessel_id):
    
  vessel = await get_vessel(str(vessel_id))

  if vessel is None:
      return 'Vessel does not exist', 404
  
  if not has_vessel_permission(vessel, 'owner'):
      return 'You are not authorized to perform this action', 403
  
  auth_codes = get_auth_codes_for_user(vessel_id)

  return AuthorizationCodeSchema().dump(auth_codes)