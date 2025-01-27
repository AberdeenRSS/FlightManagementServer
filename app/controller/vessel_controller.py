import datetime
from typing import cast
from uuid import UUID, uuid4
from fastapi import APIRouter, HTTPException


from pydantic import RootModel
from app.middleware.auth.requireAuth import AuthOptional, AuthRequired, verify_role

from app.models.vessel import Vessel, VesselHistoric
from app.models.authorization_code import AuthorizationCode, generate_auth_code
from app.models.user import User
from app.services.auth.jwt_user_info import get_socket_user_info
from app.services.auth.permission_service import has_vessel_permission, modify_vessel_permission
from app.services.data_access.auth_code import create_auth_code, get_auth_codes_for_user
from app.services.data_access.user import create_or_update_user, get_user_by_unique_name
from app.services.data_access.vessel import create_or_update_vessel, get_all_vessels, get_vessel, get_historic_vessel, get_vessel_by_name, update_vessel_without_version_change

vessel_controller = APIRouter(
    prefix="/vessel",
    tags=["vessel"],
    dependencies=[],
)

# Method for a vessel to register
@vessel_controller.post("/register", response_model_by_alias=True)
async def registerVessel(data: Vessel, user: AuthRequired) -> Vessel:
    """
    Method to be called by a vessel to register itself. 
    The vessel is supposed to transmit how it is made up so others know what data
    it can provide and what commands it can receive. If a vessel changes
    over time the old version of the vessel will be saved and the new information
    will then be used. All old flights that where performed with a previous version
    of the vessel can therefore still be used with the old version
    """

    verify_role(user, 'vessel')

    if user is None or UUID(user._id) != data.id:
        raise HTTPException(403, 'The vessel id has to match the current user id')

    acc = await create_or_update_vessel(data)

    return acc

@vessel_controller.get("/get_all")
async def get_all(user: AuthOptional) -> list[Vessel]:
    """
    Returns all vessels known to server
    """

    vessels = await get_all_vessels()
    res = [v for v in vessels if has_vessel_permission(v, 'view', user)]
    return res

@vessel_controller.get("/get/{vessel_id}/{version}")
async def get_vessel_historic(vessel_id: UUID, version: int, user: AuthOptional) -> Vessel:
    """
    Retrieves a historic version of a vessel
    """

    vessel = await get_vessel(vessel_id)

    if vessel is None:
        raise HTTPException(404, 'Vessel does not exist')
    
    if not has_vessel_permission(vessel, 'view', user):
        raise HTTPException(403, 'You don\'t have permission to view this vessel')
    
    if vessel.version == int(version):
        return vessel
    
    vessel_historic = await get_historic_vessel(vessel_id, version)

    if vessel_historic is None:
        raise HTTPException(404, 'Vessel does not exist')

    vessel = Vessel(_id = vessel_historic.id.id, _version=version, name=vessel_historic.name, parts=vessel_historic.parts)

    return vessel

@vessel_controller.get("/get_by_name/{name}")
async def get_by_name(name: str, user: AuthOptional) -> list[Vessel]:
    vessels = await get_vessel_by_name(name)

    return [v for v in vessels if has_vessel_permission(v, 'view', user)]

@vessel_controller.get("/get_test_vessels")
async def get_test_vessels() -> Vessel:
    """
    Returns a test response. Returned vessel gets a new random uuid
    """

    vessel = Vessel(_id = uuid4(), _version = 1)
    vessel.name = 'Test vessel'
    return vessel

@vessel_controller.post('/set_permission/{vessel_id}/{unique_user_name}/{permission}')
async def set_permission(vessel_id: UUID, unique_user_name: str, permission: str, user: AuthOptional):

  vessel = await get_vessel(vessel_id)

  if vessel is None:
      raise HTTPException(404, 'Vessel does not exist')
  
  if not has_vessel_permission(vessel, 'owner', user):
      raise HTTPException(403, 'You are not authorized to perform this action')
  
  other_user = await get_user_by_unique_name(unique_user_name)

  if other_user is None:
      raise HTTPException(400, 'User you are trying to give permission to does not exist')
  
  modify_vessel_permission(vessel, permission, other_user.id)

  await update_vessel_without_version_change(vessel)

  return 'success'

@vessel_controller.post('/create_vessel/{name}')
async def create_vessel(name: str, user: AuthRequired) -> Vessel:
    '''
    Creates a new empty vessel with the current user as the owner.
    A auth token can then be created for the vessel
    '''

    permissions = dict()
        
    permissions[user._id] = 'owner'
    
    vessel = Vessel(_id=uuid4(), _version=0, name=name, parts=list(), permissions=permissions, no_auth_permission=None)

    result_vessel = await create_or_update_vessel(vessel)

    vessel_user = User(_id=result_vessel.id, pw=None, unique_name=str(result_vessel.id), name=name, roles=['vessel'])

    await create_or_update_user(vessel_user)

    return result_vessel
    

@vessel_controller.post('/create_auth_code/{vessel_id}/{valid_until}')
async def create_authorization_code(vessel_id: UUID, valid_until: datetime.datetime, user: AuthOptional) -> AuthorizationCode:

    if valid_until.tzinfo is None:
        valid_until = valid_until.replace(tzinfo=datetime.timezone.utc)

    vessel = await get_vessel(vessel_id)

    if vessel is None:
        raise HTTPException(404, 'Vessel does not exist')

    if not has_vessel_permission(vessel, 'owner', user):
        raise HTTPException(403, 'You are not authorized to perform this action')

    if  valid_until.timestamp() > (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(266)).timestamp():
        raise HTTPException(400, 'Maximum allowed date the token is valid until is one year')

    code = AuthorizationCode(_id=generate_auth_code(256), corresponding_user=vessel_id, single_use=False, valid_until=valid_until)

    await create_auth_code(code)

    return code
  
@vessel_controller.get('/get_auth_codes/{vessel_id}')
async def get_auth_codes(vessel_id: UUID, user: AuthOptional) -> list[AuthorizationCode]:
    
  vessel = await get_vessel(vessel_id)

  if vessel is None:
      raise HTTPException(404, 'Vessel does not exist')
  
  if not has_vessel_permission(vessel, 'owner', user):
      raise HTTPException(403, 'You are not authorized to perform this action')
  
  auth_codes = await get_auth_codes_for_user(str(vessel_id))

  return auth_codes