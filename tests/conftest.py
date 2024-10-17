import asyncio
import datetime
from typing import Any, AsyncIterator, Awaitable, Coroutine, List, Optional
import os
from uuid import UUID, uuid4
from fastapi.testclient import TestClient
import pytest
import socketio
import uvicorn
from app.main import app
from socketio import ASGIApp, AsyncClient
from app.models.authorization_code import AuthorizationCode, generate_auth_code
from app.models.user import User
from app.services.data_access.auth_code import create_auth_code

from app.services.data_access.user import create_or_update_user, get_user
from tests.auth_helper import create_api_user, create_auth_code_for_user

PORT = 8000
LISTENING_IF = "127.0.0.1"
BASE_URL = f"http://{LISTENING_IF}:{PORT}"

# quart_server, socket_io = create_app()

# quart_server.config['connection_string'] = 'mongodb://localhost:27017'

# app = socketio.ASGIApp(app, quart_server)

TEST_USER_UUID = UUID('ff268568-5829-4bf4-90d1-a865e36d49a3')


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True, scope="session")
def test_client():
    client = TestClient(app)
    return client

@pytest.fixture(scope="session")
async def client() -> AsyncIterator[AsyncClient]:
    sio = socketio.AsyncClient()
    await sio.connect(BASE_URL)
    yield sio
    await sio.disconnect()

@pytest.fixture(scope="function")
async def test_user():

    existing_user = await get_user(TEST_USER_UUID)

    if existing_user is not None:
        return existing_user
    
    new_user = await create_api_user(TEST_USER_UUID)

    return new_user

@pytest.fixture(scope="function")
async def test_user_auth_code(test_user: Coroutine[User, None, User]):
    user = await test_user
    assert user is not None

    code = await create_auth_code_for_user(user)

    return code.id

@pytest.fixture(scope="function")
async def test_user_bearer(test_client: TestClient, test_user_auth_code: Coroutine[User, None, User]):
    user_code = await test_user_auth_code
    assert user_code is not None

    token_response = test_client.post('/auth/authorization_code_flow', data=user_code)

    return token_response.json()['token']

