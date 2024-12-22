import pytest
from fastapi.testclient import TestClient
from app.main import app
from uuid import UUID, uuid4
from app.services.data_access.user import create_or_update_user, get_user
from tests.auth_helper import create_api_user,create_auth_code_for_user
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError


TEST_USER_UUID = UUID('ff268568-5829-4bf4-90d1-a865e36d49a3')

@pytest.fixture(scope="session")
def test_client():
    # A shared client across all tests
    test_client_app = TestClient(app)
    
    try:
        db_client = MongoClient('mongodb://localhost:27017', serverSelectionTimeoutMS=2000)
        # This is synchronous and will raise ServerSelectionTimeoutError if can't connect
        db_client.server_info()
    except ServerSelectionTimeoutError as e:
        pytest.fail(f"MongoDB connection failed - make sure MongoDB is running on port 27017. Error: {str(e)}")
    finally:
        db_client.close()

    return test_client_app

async def check_db_connection():
        try:
            client = AsyncIOMotorClient('mongodb://localhost:27017')
            # Ping the server to confirm connection
            await client.admin.command('ping')
        except Exception as e:
            pytest.fail(f"MongoDB connection failed - make sure MongoDB is running on port 27017. Error: {str(e)}")
        finally:
            client.close()

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
    """
    Returns a bearer token for a test user
    """
    user_code = await test_user_auth_code
    assert user_code is not None

    token_response = test_client.post('/auth/authorization_code_flow', json={'token': user_code})

    assert token_response.status_code == 200
    return token_response.json()['token']