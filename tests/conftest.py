import asyncio
import datetime
from typing import Any, AsyncIterator, Awaitable, Coroutine, List, Optional
import os
from uuid import UUID, uuid4
import pytest
from quart import Quart
import socketio
import uvicorn
from main import create_app
from socketio import ASGIApp
from socketio.asyncio_client import AsyncClient
from models.authorization_code import AuthorizationCode, generate_auth_code
from models.user import User
from services.data_access.auth_code import create_auth_code

from services.data_access.user import create_or_update_user, get_user

PORT = 8000
LISTENING_IF = "127.0.0.1"
BASE_URL = f"http://{LISTENING_IF}:{PORT}"

quart_server, socket_io = create_app()

quart_server.config['connection_string'] = 'mongodb://localhost:27017'

app = socketio.ASGIApp(socket_io, quart_server)

TEST_USER_UUID = UUID('ff268568-5829-4bf4-90d1-a865e36d49a3')

class UvicornTestServer(uvicorn.Server):
    def __init__(self, app: ASGIApp = app, host: str = LISTENING_IF, port: int = PORT):
        self._startup_done = asyncio.Event()
        self._serve_task: Optional[Awaitable[Any]] = None
        super().__init__(config=uvicorn.Config(app, host=host, port=port))

    async def startup(self) -> None:
        """Override uvicorn startup"""
        await super().startup()
        self.config.setup_event_loop()
        self._startup_done.set()

    async def start_up(self) -> None:
        """Start up server asynchronously"""
        self._serve_task = asyncio.create_task(self.serve())
        await self._startup_done.wait()

    async def tear_down(self) -> None:
        """Shut down server asynchronously"""
        self.should_exit = True
        if self._serve_task:
            await self._serve_task


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def quart():
    return quart_server

@pytest.fixture(autouse=True, scope="session")
async def startup_and_shutdown_server():
    server = UvicornTestServer()
    await server.start_up()
    yield
    await server.tear_down()


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
    
    new_user = User(TEST_USER_UUID, None, str(TEST_USER_UUID), 'Test user')

    await create_or_update_user(new_user)

    return new_user

@pytest.fixture(scope="function")
async def test_user_auth_code(test_user: Coroutine[User, None, User]):
    user = await test_user
    assert user is not None

    code = AuthorizationCode(generate_auth_code(265), TEST_USER_UUID, True, datetime.datetime.utcnow() + datetime.timedelta(0, 10_000))

    await create_auth_code(code)

    return code._id

@pytest.fixture(scope="function")
async def test_user_bearer(quart: Quart, test_user_auth_code: Coroutine[User, None, User]):
    user_code = await test_user_auth_code
    assert user_code is not None

    client = quart.test_client()

    token_response = await client.post('/auth/authorization_code_flow', data=user_code)

    return (await token_response.json)['token']

