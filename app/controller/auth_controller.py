import datetime
from os import environ
from typing import Annotated
from fastapi import APIRouter, Body, Depends, HTTPException, Request
from app.middleware.auth.requireAuth import user_required

from app.services.auth.jwt_user_info import UserInfo
from ..models.auth_models import LoginModel, RegisterModel
from ..models.authorization_code import TokenPair
from ..models.user import User, hash_password
from ..services.data_access.auth_code import create_auth_code
from uuid import uuid4
from ..services.auth.jwt_auth_service import generate_access_token, generate_refresh_token

from ..services.data_access.user import get_user, get_user_by_unique_name, create_or_update_user
from ..services.data_access.auth_code import get_code, delete_code

client_id = environ.get('FLIGHT_MANAGEMENT_SERVER_CLIENT_ID')
client_secret = environ.get('FLIGHT_MANAGEMENT_SERVER_CLIENT_SECRET')

auth_controller = APIRouter(
    prefix="/auth",
    tags=["auth"],
    dependencies=[],
)

async def generate_token_with_refresh(user: User):
    refresh_token = generate_refresh_token(user)

    await create_auth_code(refresh_token) 
    
    return TokenPair(token=generate_access_token(user), refresh_token=refresh_token.id)


@auth_controller.post('/register')
async def register(data: RegisterModel) -> TokenPair:

    existing_user = await get_user_by_unique_name(data.unique_name)

    if existing_user is not None:
        raise HTTPException(400, 'User with that name already exists')

    user_id = uuid4()

    user = User(_id=user_id, pw=hash_password(user_id, data.pw), unique_name=data.unique_name, name=data.name, roles=[])

    await create_or_update_user(user)

    return await generate_token_with_refresh(user)


@auth_controller.post("/login")
async def login(data: LoginModel) -> TokenPair:
    
    existing_user = await get_user_by_unique_name(data.unique_name)

    if existing_user is None:
        raise HTTPException(401, 'User does not exist')

    if existing_user.pw is None:
        raise HTTPException(401, 'Password login available for user')
    
    if existing_user.pw != hash_password(existing_user.id, data.pw):
        raise HTTPException(401, 'Password incorrect')
    
    return await generate_token_with_refresh(existing_user)
  

@auth_controller.post("/authorization_code_flow")
async def authorization_code_flow(request: Request) -> TokenPair:

    data = str(await request.body(), encoding='utf-8')

    data = data.replace('\n', '').replace('\r', '').replace(' ', '')

    print(f'Using token: {data}')

    token = await get_code(data)

    if token is None:
        raise HTTPException(401, 'Invalid token')
    
    if datetime.datetime.now(datetime.UTC).timestamp() > token.valid_until.timestamp():
        await delete_code(data)
        raise HTTPException(401, 'Token expired')
    
    user = await get_user(token.corresponding_user)

    # If the user doesn't exist yet create it
    if user is None:

        user = User(_id=token.corresponding_user, pw=None, unique_name=str(token.corresponding_user), name='', roles=['vessel'])

        await create_or_update_user(user)
    
    if token.single_use:
        await delete_code(data)

    return await generate_token_with_refresh(user)

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

