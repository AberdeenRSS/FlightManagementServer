from datetime import datetime, timedelta
from typing import Coroutine
import pytest
from quart import Quart

from tests.auth_helper import get_auth_headers

@pytest.mark.asyncio
async def test_create_vessel(quart: Quart, test_user_bearer: Coroutine[str, None, str]):

    bearer = await test_user_bearer

    vessel_name = 'Testing Vessel'

    client = quart.test_client()

    create_response = await client.post(f'/vessel/create_vessel/{vessel_name}', headers= get_auth_headers(bearer))

    assert create_response.status_code == 200

    vessel = await create_response.json

    assert vessel['name'] == vessel_name

@pytest.mark.asyncio
async def test_create_vessel_auth_code(quart: Quart, test_user_bearer: Coroutine[str, None, str]):

    bearer = await test_user_bearer

    vessel_name = 'Testing Vessel'

    client = quart.test_client()

    create_response = await client.post(f'/vessel/create_vessel/{vessel_name}', headers=get_auth_headers(bearer))

    assert create_response.status_code == 200

    vessel = await create_response.json
    vessel_id = vessel['_id']
    valid_until = datetime.utcnow() + timedelta(1)

    auth_code_response = await client.post(f'/vessel/create_auth_code/{vessel_id}/{valid_until.isoformat()}', headers=get_auth_headers(bearer))

    assert auth_code_response.status_code == 200

    auth_code_obj = await auth_code_response.json
    auth_code = auth_code_obj['_id']

    auth_code_response = await client.post(f'/auth/authorization_code_flow', data=auth_code)

    assert auth_code_response.status_code == 200

