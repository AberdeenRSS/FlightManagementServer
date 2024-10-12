from datetime import datetime, timedelta
from typing import Coroutine
from fastapi.testclient import TestClient
import pytest

from tests.auth_helper import get_auth_headers
from tests.conftest import TEST_USER_UUID

@pytest.mark.asyncio
async def test_create_vessel(test_client: TestClient, test_user_bearer: Coroutine[str, None, str]):

    bearer = await test_user_bearer

    vessel_name = 'Testing Vessel'

    create_response = test_client.post(f'/vessel/create_vessel/{vessel_name}', headers= get_auth_headers(bearer))

    assert create_response.status_code == 200

    vessel = create_response.json()

    assert vessel['name'] == vessel_name
    permissions = vessel['permissions']
    owners = [p[0] for p in permissions.items() if p[1] == 'owner']

    assert len(owners) == 1
    assert owners[0] == str(TEST_USER_UUID)

@pytest.mark.asyncio
async def test_create_vessel_auth_code(test_client: TestClient, test_user_bearer: Coroutine[str, None, str]):

    bearer = await test_user_bearer

    vessel_name = 'Testing Vessel'

    create_response = test_client.post(f'/vessel/create_vessel/{vessel_name}', headers=get_auth_headers(bearer))

    assert create_response.status_code == 200

    vessel = create_response.json()
    vessel_id = vessel['_id']
    valid_until = datetime.now(timezone.utc) + timedelta(1)

    auth_code_response = test_client.post(f'/vessel/create_auth_code/{vessel_id}/{valid_until.isoformat()}', headers=get_auth_headers(bearer))

    assert auth_code_response.status_code == 200

    auth_code_obj = auth_code_response.json()
    auth_code = auth_code_obj['_id']

    auth_code_response = test_client.post(f'/auth/authorization_code_flow', data=auth_code)

    assert auth_code_response.status_code == 200

