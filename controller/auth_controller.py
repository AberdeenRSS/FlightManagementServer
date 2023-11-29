from dataclasses import dataclass
import datetime
from os import environ
from fastapi import APIRouter
from quart import Blueprint, request
import httpx
import urllib.parse
from middleware.auth.requireAuth import auth_required
from models.auth_models import LoginModel, RegisterModel
from models.authorization_code import TokenPair, TokenPairSchema
from models.user import User, hash_password
from services.data_access.auth_code import create_auth_code
from uuid import uuid4
from services.auth.jwt_auth_service import generate_access_token, generate_refresh_token

from services.data_access.user import get_user, get_user_by_unique_name, create_or_update_user
from services.data_access.auth_code import get_code, delete_code

from quart_schema import DataSource, documentation
import quart_schema
from pydantic import RootModel

client_id = environ.get('FLIGHT_MANAGEMENT_SERVER_CLIENT_ID')
client_secret = environ.get('FLIGHT_MANAGEMENT_SERVER_CLIENT_SECRET')

auth_controller  = APIRouter(
    prefix="/user",
    tags=["user"],
    dependencies=[],
    # responses={404: {"description": "Not found"}},
)

async def generate_token_with_refresh(user: User):
    refresh_token = generate_refresh_token(user)

    await create_auth_code(refresh_token) 
    
    return TokenPair(generate_access_token(user), refresh_token._id)




@auth_controller.post('/register')
async def register(data: RegisterModel):

    existing_user = await get_user_by_unique_name(data.unique_name)

    if existing_user is not None:
        return 'User with that name already exists', 400
    
    user_id = uuid4()

    user = User(user_id, hash_password(user_id, data.pw), data.unique_name, data.name)

    await create_or_update_user(user)

    return await generate_token_with_refresh(user)


@auth_controller.post("/login")
async def login(data: LoginModel):
    
    existing_user = await get_user_by_unique_name(data.unique_name)

    if existing_user is None:
        return 'User does not exist', 401
    
    if existing_user.pw is None:
        return 'Password login available for user', 401
    
    if existing_user.pw != hash_password(existing_user._id, data.pw):
        return 'Password incorrect', 401
    
    return await generate_token_with_refresh(existing_user)
  

@auth_controller.post("/authorization_code_flow")
async def authorization_code_flow(code_id: str):

    token = await get_code(code_id)

    if token is None:
        return 'Invalid token', 401
    
    if datetime.datetime.utcnow().timestamp() > token.valid_until.timestamp():
        await delete_code(code_id)
        return 'Token expired', 401
    
    user = await get_user(token.corresponding_user)

    # If the user doesn't exist yet create it
    if user is None:

        user = User(token.corresponding_user, None, str(token.corresponding_user), '', ['vessel'])

        await create_or_update_user(user)
    
    if token.single_use:
        await delete_code(code_id)

    return await generate_token_with_refresh(user)

@auth_controller.post('/auth_code/rewoke')
async def rewoke_auth_code(code: str):
    '''
    Deletes the auth code. This controller does not have any authorization on it, 
    as having the auth code is authorization in itself
    '''

    if await delete_code(code):
        return 'deleted', 200
    
    return 'did_not_exist', 200

@auth_controller.get('/verify_authenticated')
async def verify_authenticated():
    return 'success', 200

