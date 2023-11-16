import datetime
from os import environ
from quart import Blueprint, request
import httpx
import urllib.parse
from middleware.auth.requireAuth import auth_required
from models.authorization_code import TokenPair, TokenPairSchema
from models.user import User, hash_password
from services.data_access.auth_code import create_auth_code
from uuid import uuid4
from services.auth.jwt_auth_service import generate_access_token, generate_refresh_token

from services.data_access.user import get_user, get_user_by_unique_name, create_or_update_user
from services.data_access.auth_code import get_code, delete_code

client_id = environ.get('FLIGHT_MANAGEMENT_SERVER_CLIENT_ID')
client_secret = environ.get('FLIGHT_MANAGEMENT_SERVER_CLIENT_SECRET')

auth_controller = Blueprint('auth', __name__, url_prefix='/auth')

async def generate_token_with_refresh(user: User):
    refresh_token = generate_refresh_token(user)

    await create_auth_code(refresh_token) 
    
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

    user = User(user_id, hash_password(user_id, request_body['pw']), request_body['unique_name'], request_body['name'])

    await create_or_update_user(user)

    return TokenPairSchema().dump(await generate_token_with_refresh(user))


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
    
    if existing_user.pw is None:
        return 'Password login available for user', 401
    
    if existing_user.pw != hash_password(existing_user._id, request_body['pw']):
        return 'Password incorrect', 401
    
    return TokenPairSchema().dump(await generate_token_with_refresh(existing_user))
  

@auth_controller.route("/authorization_code_flow", methods=['POST'])
async def authorization_code_flow():

    code_id = await request.get_data(True, True, False)

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

    return TokenPairSchema().dump(await generate_token_with_refresh(user))

@auth_controller.route('/auth_code/rewoke', methods=['POST'])
async def rewoke_auth_code():
    '''
    Deletes the auth code. This controller does not have any authorization on it, 
    as having the auth code is authorization in itself
    '''

    code = await request.get_data(True, True, False)

    if await delete_code(code):
        return 'deleted', 200
    
    return 'did_not_exist', 200

@auth_controller.route('/verify_authenticated')
@auth_required
async def verify_authenticated():
    return 'success', 200

