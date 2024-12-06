import pytest
from fastapi.testclient import TestClient
from app.main import app
from uuid import UUID, uuid4
from app.services.data_access.user import create_or_update_user, get_user
from tests.auth_helper import create_api_user,create_auth_code_for_user

TEST_USER_UUID = UUID('ff268568-5829-4bf4-90d1-a865e36d49a3')

@pytest.fixture(scope="session")
def test_client():
    # A shared client across all tests
    return TestClient(app)

@pytest.fixture(scope="function")
async def test_user():

    existing_user = await get_user(TEST_USER_UUID)

    if existing_user is not None:
        return existing_user
    
    new_user = await create_api_user(TEST_USER_UUID)

    return new_user

@pytest.fixture(scope="function")
async def test_user_auth_code(test_user):
    user = await test_user
    assert user is not None

    code = await create_auth_code_for_user(user)

    return code.id

@pytest.fixture(scope="function")
async def test_user_bearer(test_client: TestClient, test_user_auth_code):
    user_code = await test_user_auth_code
    assert user_code is not None

    token_response = test_client.post('/auth/authorization_code_flow', json={'token': user_code})

    assert token_response.status_code == 200
    return token_response.json()['token']