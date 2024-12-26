from typing import Any
import pytest
from fastapi.testclient import TestClient
from app.models.vessel import Vessel
from tests.auth_helper import get_auth_headers
from tests.conftest import TEST_USER_UUID
from uuid import uuid4
from tests.auth_helper import create_api_user, get_bearer_for_user, get_auth_headers

@pytest.mark.asyncio
async def test_v1_rename_vessel(test_client: TestClient, test_user_bearer: Any):

    bearer = await test_user_bearer

    vessel_name = 'Testing Vessel'

    request_body = {
        'name': vessel_name,
    }

    # Create a vessel
    create_response = test_client.post(
        f'/v1/vessels/',
        headers=get_auth_headers(bearer),
        json=request_body
    )

    assert create_response.status_code == 200

    vessel = create_response.json()

    assert vessel['name'] == vessel_name
    permissions = vessel['permissions']
    owners = [p[0] for p in permissions.items() if p[1] == 'owner']

    # The vessel should be created with only the user as the owner
    assert len(permissions) == 1
    assert len(owners) == 1
    assert owners[0] == str(TEST_USER_UUID)
    # other users should not be able to access the vessel without permissions
    assert vessel['no_auth_permission'] is None

    # Rename the vessel
    new_vessel_name = 'New Vessel Name'


    rename_data = {
        'name': new_vessel_name
    }

    rename_response = test_client.put(
        f"/v1/vessels/{vessel['_id']}",
        headers=get_auth_headers(bearer),
        json=rename_data
    )

    assert rename_response.status_code == 200

    renamed_vessel = rename_response.json()

    assert renamed_vessel['name'] == new_vessel_name

    # Check that vessel has been updated on new request
    get_response = test_client.get(
        f"/v1/vessels/{vessel['_id']}",
        headers=get_auth_headers(bearer)
    )

    assert get_response.status_code == 200

    updated_vessel = get_response.json()

    assert updated_vessel['name'] == new_vessel_name

@pytest.mark.asyncio
async def test_v1_rename_vessel_unauthorized(test_client: TestClient, test_user_bearer):
    """Test that users without owner permission cannot rename vessels"""
    # Create vessel with first user
    bearer = await test_user_bearer
    second_user = await create_api_user(uuid4())
    second_user_bearer = await get_bearer_for_user(second_user, test_client)

    
    vessel = test_client.post(
        f'/v1/vessels/',
        headers=get_auth_headers(bearer),
        json={'name': 'Original Name'}
    ).json()

    rename_response = test_client.put(
        f"/v1/vessels/{vessel['_id']}",
        headers=get_auth_headers(second_user_bearer),
        json={'name': 'Unauthorized Change'}
    )

    assert rename_response.status_code == 403

@pytest.mark.asyncio
async def test_v1_rename_vessel_invalid_data(test_client: TestClient, test_user_bearer: Any):
    """Test renaming with invalid data"""
    bearer = await test_user_bearer
    
    # Create a vessel
    vessel = test_client.post(
        f'/v1/vessels/',
        headers=get_auth_headers(bearer),
        json={'name': 'Test Vessel'}
    ).json()

    # Empty string name
    rename_response = test_client.put(
        f"/v1/vessels/{vessel['_id']}",
        headers=get_auth_headers(bearer),
        json={'name': ''}
    )
    assert rename_response.status_code == 422

    # No name in request
    rename_response = test_client.put(
        f"/v1/vessels/{vessel['_id']}",
        headers=get_auth_headers(bearer),
        json={}
    )
    assert rename_response.status_code == 422


