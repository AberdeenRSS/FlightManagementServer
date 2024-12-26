import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from pytz import UTC
from tests.auth_helper import get_auth_headers, create_api_user, get_bearer_for_user
from uuid import uuid4



@pytest.mark.asyncio
async def test_v1_create_vessel_auth_code(test_client: TestClient, test_user_bearer): 
    bearer = await test_user_bearer

    # Create a Vessel for first user
    vessel_name = 'Testing Vessel'

    vessel_data = {
        'name': vessel_name,
    }

    create_response = test_client.post(
        f"/v1/vessels/",
        headers=get_auth_headers(bearer),
        json=vessel_data
    )

    assert create_response.status_code == 200
    assert create_response.json()['_version'] == 1

    vessel = create_response.json()
    vessel_id = vessel['_id']
    valid_until = datetime.now(UTC) + timedelta(1)
    assert vessel['no_auth_permission'] is None

    # Create an auth code for the vessel by the first user
    auth_code_data = {
        'valid_until': valid_until.isoformat(),
    }

    auth_code_response = test_client.post(
        f'/v1/vessels/{vessel_id}/auth_codes', 
        headers=get_auth_headers(bearer),
        json=auth_code_data
    )
    
    assert auth_code_response.status_code == 200

    auth_code_obj = auth_code_response.json()
    auth_code = auth_code_obj['_id']

    # Check that the auth code works
    auth_code_response = test_client.post(f'/auth/authorization_code_flow', json={'token':auth_code})

    assert auth_code_response.status_code == 200

    get_vessel_response = test_client.get(
        f'/v1/vessels/{vessel_id}/versions/1',
        headers=get_auth_headers(bearer)
    )
    assert get_vessel_response.status_code == 200

    get_vessel_response = test_client.get(
        f'/v1/vessels/{vessel_id}',
        headers=get_auth_headers(bearer)
    )

    assert get_vessel_response.status_code == 200

    # Create second user who shouldnt have permissions for this vessel
    second_user = await create_api_user(uuid4())
    second_user_bearer = await get_bearer_for_user(second_user, test_client)

    # Try to get the vessel should return 403
    get_vessel_response = test_client.get(
        f'/v1/vessels/{vessel_id}/versions/1',
        headers=get_auth_headers(second_user_bearer)
    )
    assert get_vessel_response.status_code == 403

    get_vessel_response = test_client.get(
        f'/v1/vessels/{vessel_id}',
        headers=get_auth_headers(second_user_bearer)
    )

    assert get_vessel_response.status_code == 403

    # try to create an auth code should return 403
    second_auth_code_data = {
        'valid_until': valid_until.isoformat(),
    }
    disallowed_auth_code_response = test_client.post(
        f"/v1/vessels/{vessel_id}/auth_codes",
        headers=get_auth_headers(second_user_bearer),
        json=second_auth_code_data
    )

    assert disallowed_auth_code_response.status_code == 403
    assert 'token' not in disallowed_auth_code_response.json() 