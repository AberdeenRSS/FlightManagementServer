import asyncio
import datetime
from os import environ
from typing import Annotated, Any, Coroutine
from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from app.middleware.auth.requireAuth import user_required

from app.models.flight import Flight
from app.models.vessel import Vessel
from app.services.auth.jwt_user_info import UserInfo, user_info_from_user
from app.services.auth.permission_service import has_flight_permission
from app.services.data_access.flight import get_flight
from app.services.data_access.vessel import get_vessel
from ..models.auth_models import LoginModel, RefreshTokenModel, RegisterModel
from ..models.authorization_code import TokenPair
from ..models.user import User, hash_password
from ..services.data_access.auth_code import create_auth_code
from uuid import uuid4, UUID
from ..services.auth.jwt_auth_service import generate_access_token, generate_refresh_token

from ..services.data_access.user import get_user, get_user_by_unique_name, create_or_update_user
from ..services.data_access.auth_code import get_code, delete_code

from ..services.auth.jwt_auth_service import get_public_key

client_id = environ.get('FLIGHT_MANAGEMENT_SERVER_CLIENT_ID')
client_secret = environ.get('FLIGHT_MANAGEMENT_SERVER_CLIENT_SECRET')

auth_controller = APIRouter(
    prefix="/auth",
    tags=["auth"],
    dependencies=[],
)

async def generate_token_with_refresh(user: User, resources: list[tuple[str, str]]):
    refresh_token = generate_refresh_token(user)

    await create_auth_code(refresh_token) 
    
    return TokenPair(token=generate_access_token(user, resources), refresh_token=refresh_token.id)

@auth_controller.get('/public_key', response_class=PlainTextResponse)
def public_key() -> str:

    key =  get_public_key()

    return key

@auth_controller.post('/register')
async def register(data: RegisterModel) -> TokenPair:

    existing_user = await get_user_by_unique_name(data.unique_name)

    if existing_user is not None:
        raise HTTPException(400, 'User with that name already exists')

    user_id = uuid4()

    user = User(_id=user_id, pw=hash_password(user_id, data.pw), unique_name=data.unique_name, name=data.name, roles=[])

    await create_or_update_user(user)

    return await generate_token_with_refresh(user, [])


@auth_controller.post("/login")
async def login(data: LoginModel) -> TokenPair:
    
    existing_user = await get_user_by_unique_name(data.unique_name)

    if existing_user is None:
        raise HTTPException(401, 'User does not exist')

    if existing_user.pw is None:
        raise HTTPException(401, 'Password login available for user')
    
    if existing_user.pw != hash_password(existing_user.id, data.pw):
        raise HTTPException(401, 'Password incorrect')
    
    return await generate_token_with_refresh(existing_user, [])
  

@auth_controller.post("/authorization_code_flow")
async def authorization_code_flow(data: RefreshTokenModel) -> TokenPair:

    token_value = data.token

    # This is to clean the token from any newlines or spaces
    token_value = token_value.replace('\n', '').replace('\r', '').replace(' ', '')
    
    token = await get_code(token_value)

    if token is None:
        raise HTTPException(401, 'Invalid token')
    
    if datetime.datetime.now(datetime.timezone.utc).timestamp() > token.valid_until.timestamp():
        await delete_code(token_value)
        raise HTTPException(401, 'Token expired')
    
    user = await get_user(token.corresponding_user)

    # If the user doesn't exist yet create it
    if user is None:

        user = User(_id=token.corresponding_user, pw=None, unique_name=str(token.corresponding_user), name='', roles=['vessel'])

        await create_or_update_user(user)

    if data.resources is not None:

        flight_load_tasks: list[Coroutine[Any, Any, Flight | None]] = []

        for resource_type, resource_uuid in data.resources:

            if resource_type == 'flight':

                if not isinstance(resource_uuid, UUID):
                    raise HTTPException(401, f'Invalid resource uuid {resource_uuid}')
                
                flight_load_tasks.append(get_flight(resource_uuid))
            else:
                raise HTTPException(401, f'Invalid resource type: {resource_type}')

        flights = await asyncio.gather(*flight_load_tasks)

        vessel_load_tasks = list[Coroutine[Any, Any, Vessel | None]]()

        i = -1
        for flight in flights:
            i += 1
            if flight is None:
                raise HTTPException(401, f'Flight {data.resources[i][1]} does not exist')

            vessel_load_tasks.append(get_vessel(flight.vessel_id))
        
        vessels = await asyncio.gather(*vessel_load_tasks)

        user_info = user_info_from_user(user)

        i = -1
        for vessel in vessels:
            i += 1

            flight = flights[i]

            if vessel is None or flight is None:
                raise HTTPException(401, f'Flight {data.resources[i][1]} does not exist')

            if not has_flight_permission(flight, vessel, 'write', user_info):
                raise HTTPException(401, f'No permission for flight {data.resources[i][1]}')

    
    if token.single_use:
        await delete_code(token_value)

    return await generate_token_with_refresh(user, [(r[0], str(r[1])) for r in data.resources] if isinstance(data.resources, list) else []) 

@auth_controller.post('/auth_code/rewoke')
async def rewoke_auth_code(request: Request):
    '''
    Deletes the auth code. This controller does not have any authorization on it, 
    as having the auth code is authorization in itself
    '''

    code = str(await request.body(), encoding='utf-8')

    if await delete_code(code):
        return 'deleted'
    
    return 'did_not_exist'

@auth_controller.get('/verify_authenticated')
async def verify_authenticated(user: Annotated[UserInfo, Depends(user_required)]):
    return 'success'

