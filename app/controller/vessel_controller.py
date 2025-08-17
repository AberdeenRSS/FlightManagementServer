import datetime
from typing import Annotated, Optional, cast
from uuid import UUID, uuid4
from fastapi import APIRouter, Body, Depends, HTTPException, Query


from pydantic import RootModel
from app.middleware.auth.requireAuth import AuthOptional, AuthRequired, verify_role

from app.models.vessel import Vessel, VesselHistoric, CreateVessel, UpdateVessel
from app.models.authorization_code import AuthorizationCode, generate_auth_code,CreateAuthorizationCode
from app.models.user import User
from app.models.permissions import Permission
from app.services.auth.jwt_user_info import get_socket_user_info
from app.services.auth.permission_service import has_vessel_permission, modify_vessel_permission
from app.services.data_access.auth_code import create_auth_code, get_auth_codes_for_user
from app.services.data_access.user import create_or_update_user, get_user_by_unique_name
from app.services.data_access.vessel import create_or_update_vessel, get_all_vessels, get_vessel, get_historic_vessel, get_vessel_by_name, update_vessel_without_version_change, delete_vessel_by_id
from app.services.vessel_service import VesselService

vessel_controller = APIRouter(
    prefix="/vessel",
    tags=["vessel"],
    dependencies=[],
)

vessels_controller = APIRouter(
    prefix="/v1/vessels",
    tags=["v1/vessels"],
    dependencies=[],
)

# Method for a vessel to register
@vessels_controller.post("/register", response_model_by_alias=True)
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

    for part in data.parts:
        if part.id is None:
            part.id = uuid4()
            
    acc = await create_or_update_vessel(data)

    return acc

@vessels_controller.get("/")
@vessel_controller.get("/get_all")
async def get_all(user: AuthOptional,name: Optional[str] = Query(default=None, description="Filter vessels by name")
) -> list[Vessel]:
    """
    Returns all vessels known to server
    """

    if name is not None and name != '':
        vessels = await get_vessel_by_name(name.lower())
    else:
        vessels = await get_all_vessels()

    vessels = [v for v in vessels if has_vessel_permission(v, 'view', user)]

    return vessels


@vessel_controller.get("/get/{vessel_id}/{version}")
async def get_vessel_historic_legacy(user:AuthOptional,vessel_id:UUID,version:int) -> Vessel:
    """
    Retrieves a historic version of a vessel
    """
    return await get_vessel_historic(user, vessel_id, version)

@vessels_controller.get("/{vessel_id}")
async def get_vessel_controller(user:AuthOptional, vessel_id:UUID) -> Vessel:
    '''
    Retreives a vessel and returns the latest version
    '''

    return await get_vessel_historic(user, vessel_id, None)


@vessels_controller.get("/{vessel_id}/versions/{version}")
async def get_vessel_historic(user: AuthOptional,vessel_id: UUID, version: Optional[int]=None) -> Vessel:
    """
    Retrieves a historic version of a vessel
    """
    
    vessel = await get_vessel(vessel_id)

    if vessel is None:
        raise HTTPException(404, 'Vessel does not exist')
    
    if not has_vessel_permission(vessel, 'view', user):
        raise HTTPException(403, 'You don\'t have permission to view this vessel')
    
    if version is None or vessel.version == version:
        return vessel
    
    vessel_historic = await get_historic_vessel(vessel_id, version)

    if vessel_historic is None:
        raise HTTPException(404, 'Vessel does not exist')

    vessel = Vessel(_id = vessel_historic.id.id, _version=version, name=vessel_historic.name, parts=vessel_historic.parts)

    return vessel

# Removed in v1
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
async def set_permission_legacy(user:AuthOptional,vessel_id:UUID,unique_user_name:str,permission:str) -> str:
    permission_data = Permission(
        unique_user_name=unique_user_name,
        permission=permission
    )
    return await set_permission(user,vessel_id,permission_data)

@vessels_controller.post("/{vessel_id}/permissions")
async def set_permission(
    user: AuthOptional,
    vessel_id: UUID, 
    permission_data: Permission = Body() # v1 only
    ) -> str:

  vessel = await get_vessel(vessel_id)

  if vessel is None:
      raise HTTPException(404, 'Vessel does not exist')
  
  if not has_vessel_permission(vessel, 'owner', user):
      raise HTTPException(403, 'You are not authorized to perform this action')
  
  other_user = await get_user_by_unique_name(permission_data.unique_user_name)

  if other_user is None:
      raise HTTPException(400, 'User you are trying to give permission to does not exist')
  
  modify_vessel_permission(vessel, permission_data.permission, other_user.id)

  await update_vessel_without_version_change(vessel)

  return 'success'


@vessel_controller.post('/create_vessel/{name}')
async def create_vessel_legacy(user:AuthRequired,name:str) -> Vessel:
    '''
    Creates a new empty vessel with the current user as the owner.
    A auth token can then be created for the vessel
    '''
    vessel_data = CreateVessel(
        name=name
    )
    return await create_vessel(user, vessel_data)

@vessels_controller.post('/')
async def create_vessel(user: AuthRequired,vessel_data:CreateVessel=Body()) -> Vessel:
    '''
    Creates a new empty vessel with the current user as the owner.
    A auth token can then be created for the vessel
    '''
    vessel_name = vessel_data.name

    if vessel_name is None:
        raise HTTPException(status_code=422, detail="Vessel name is required")
        
    permissions = dict()
        
    permissions[user._id] = 'owner'
    
    vessel = Vessel(_id=uuid4(), _version=0, name=vessel_name, parts=list(), permissions=permissions, no_auth_permission=None)

    result_vessel = await create_or_update_vessel(vessel)

    vessel_user = User(_id=result_vessel.id, pw=None, unique_name=str(result_vessel.id), name=vessel_name, roles=['vessel'])

    await create_or_update_user(vessel_user)

    return result_vessel
    

@vessel_controller.post('/create_auth_code/{vessel_id}/{valid_until}')
async def create_authorization_code_legacy(user:AuthOptional,vessel_id:UUID,valid_until:datetime.datetime) -> AuthorizationCode:
    '''
    Creates a new authorization code for a vessel
    '''

    auth_code_data = CreateAuthorizationCode(valid_until=valid_until)

    return await create_authorization_code(user, vessel_id, auth_code_data)

@vessels_controller.post("/{vessel_id}/auth_codes")
async def create_authorization_code(user: AuthOptional,vessel_id: UUID, auth_code_data:CreateAuthorizationCode) -> AuthorizationCode:

    valid_until = auth_code_data.valid_until

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
  
@vessels_controller.get("/{vessel_id}/auth_codes")
@vessel_controller.get('/get_auth_codes/{vessel_id}')
async def get_auth_codes(vessel_id: UUID, user: AuthOptional) -> list[AuthorizationCode]:
    
  vessel = await get_vessel(vessel_id)

  if vessel is None:
      raise HTTPException(404, 'Vessel does not exist')
  
  if not has_vessel_permission(vessel, 'owner', user):
      raise HTTPException(403, 'You are not authorized to perform this action')
  
  auth_codes = await get_auth_codes_for_user(str(vessel_id))

  return auth_codes


@vessels_controller.put("/{vessel_id}")
async def update_vessel(user: AuthOptional, vessel_id:UUID, vessel_update_data:UpdateVessel) -> Vessel:
    '''
    Updates a vessel, currently only accepts name changes
    '''

    if vessel_update_data.name is None or vessel_update_data.name == '':
        raise HTTPException(422, 'Name is required to update vessel')

    vessel = await get_vessel(vessel_id)

    if vessel is None:
        raise HTTPException(404, 'Vessel does not exist')
    
    if not has_vessel_permission(vessel, 'owner', user):
        raise HTTPException(403, 'You are not authorized to perform this action')
    
    vessel.name = vessel_update_data.name

    await update_vessel_without_version_change(vessel)

    return vessel

@vessels_controller.delete("/{vessel_id}")
async def delete_vessel(user: AuthOptional,vessel_id:UUID) -> str:
    '''
    Deletes a vessel
    '''
    
    vessel = await get_vessel(vessel_id)

    if vessel is None:
        raise HTTPException(404, 'Vessel does not exist')
    
    if not has_vessel_permission(vessel, 'owner', user):
        raise HTTPException(403, 'You are not authorized to perform this action')
    
    result = await VesselService.delete_vessel(vessel_id)

    if not result:
        raise HTTPException(500, 'Failed to delete vessel')
    
    return 'success'
