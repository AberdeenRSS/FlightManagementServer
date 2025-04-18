import pytest
from fastapi.testclient import TestClient
from tests.auth_helper import get_auth_headers
from tests.conftest import TEST_USER_UUID
from uuid import uuid4

@pytest.mark.asyncio
async def test_create_vessel(test_client: TestClient, test_user_bearer):

    bearer = await test_user_bearer

    vessel_name = 'Testing Vessel'

    create_response = test_client.post(f'/vessel/create_vessel/{vessel_name}', headers=get_auth_headers(bearer))

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
