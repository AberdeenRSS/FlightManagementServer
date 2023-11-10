import datetime
from os import environ
from quart import Blueprint, request
import httpx
import urllib.parse
from models.token import TokenPair, TokenPairSchema
from models.user import User, hash_password
from services.data_access.tokens import create_token
from uuid import uuid4
from services.auth.jwt_auth_service import generate_access_token, generate_refresh_token

from services.data_access.user import get_user, get_user_by_unique_name, create_or_update_user
from services.data_access.tokens import get_token, delete_token

client_id = environ.get('FLIGHT_MANAGEMENT_SERVER_CLIENT_ID')
client_secret = environ.get('FLIGHT_MANAGEMENT_SERVER_CLIENT_SECRET')

auth_controller = Blueprint('auth', __name__, url_prefix='/auth')

async def generate_token_with_refresh(user: User):
    refresh_token = generate_refresh_token(user)

    await create_token(refresh_token)
    
    return TokenPair(generate_access_token(user), refresh_token._id)

@auth_controller.route("/register", methods=['POST'])
async def register():
    request_body = await request.get_json()

    if 'name' not in request_body:
        return 'User name required', 400
    
    if 'unique_name' not in request_body:
        return 'Unique name required', 400
    
    if 'pw' not in request_body:
        return 'Password required', 400
    
    existing_user = await get_user_by_unique_name(request_body['unique_name'])

    if existing_user is not None:
        return 'User with that name already exists', 400
    
    user_id = uuid4()

    user = User(user_id, request_body['unique_name'], request_body['name'], hash_password(user_id, request_body['pw']))

    await create_or_update_user(user)

    return TokenPairSchema().dumps(await generate_token_with_refresh(user))


@auth_controller.route("/login", methods=['POST'])
async def login():

    request_body = await request.get_json()
    
    if 'unique_name' not in request_body:
        return 'Unique name required', 400
    
    if 'pw' not in request_body:
        return 'Password required', 400
    
    existing_user = await get_user_by_unique_name(request_body['unique_name'])

    if existing_user is None:
        return 'User does not exist', 401
    
    if existing_user.pw != hash_password(existing_user._id, request_body['pw']):
        return 'Password incorrect', 401
    
    return TokenPairSchema().dumps(await generate_token_with_refresh(existing_user))
  

@auth_controller.route("/login_by_token", methods=['POST'])
async def login_with_token():
    token_id = await request.get_data(True, True, False)

    token = await get_token(token_id)

    if token is None:
        return 'Invalid token', 401
    
    if token.valid_until > datetime.datetime.utcnow():
        await delete_token(token_id)
        return 'Token expired', 401
    
    user = await get_user(token.corresponding_user)

    if user is None:
        await delete_token(token_id)
        return 'Invalid user', 401
    
    if token.single_use:
        await delete_token(token_id)

    return TokenPairSchema().dumps(await generate_token_with_refresh(user))



