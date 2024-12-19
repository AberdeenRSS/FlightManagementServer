from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient

from app.models.authorization_code import AuthorizationCode, generate_auth_code

from app.models.user import User
from app.services.data_access.auth_code import create_auth_code
from app.services.data_access.user import create_or_update_user


def get_auth_headers(token):
    return {'Authorization': f'Bearer {token}'}

async def create_api_user(uuid: UUID):
    new_user = User(
        _id=uuid, 
        pw=None, 
        unique_name=str(uuid), 
        name='Test user', 
        roles=[])

    await create_or_update_user(new_user)

    return new_user

async def create_auth_code_for_user(user: User):
    code = AuthorizationCode(_id=generate_auth_code(265), corresponding_user=user.id, single_use=True, valid_until=datetime.now(UTC) + timedelta(0, 10_000))

    await create_auth_code(code)

    return code

async def get_bearer_for_user(user: User, api_client: TestClient):

    code = await create_auth_code_for_user(user)

    token_response = api_client.post('/auth/authorization_code_flow', json={'token':code.id})

    return (token_response.json())['token']