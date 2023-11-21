
import datetime
from uuid import UUID

from quart.typing import TestClientProtocol
from models.authorization_code import AuthorizationCode, generate_auth_code

from models.user import User
from services.data_access.auth_code import create_auth_code
from services.data_access.user import create_or_update_user


def get_auth_headers(token):
    return {'Authorization': f'Bearer {token}'}

async def create_api_user(uuid: UUID):
    new_user = User(uuid, None, str(uuid), 'Test user')

    await create_or_update_user(new_user)

    return new_user

async def create_auth_code_for_user(user: User):
    code = AuthorizationCode(generate_auth_code(265), user._id, True, datetime.datetime.utcnow() + datetime.timedelta(0, 10_000))

    await create_auth_code(code)

    return code

async def get_bearer_for_user(user: User, api_client: TestClientProtocol):

    code = await create_auth_code_for_user(user)

    token_response = await api_client.post('/auth/authorization_code_flow', data=code._id)

    return (await token_response.json)['token']