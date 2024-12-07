import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from tests.auth_helper import create_api_user, get_bearer_for_user, get_auth_headers

@pytest.mark.asyncio
async def test_vessel_view_privileges(test_client: TestClient, test_user_bearer):    
    '''Tests that the vehicles can only be seen if the user has "view" permissions'''

    bearer = await test_user_bearer

    vessel_name = 'Testing Vessel'

    create_response = test_client.post(f'/vessel/create_vessel/{vessel_name}', headers=get_auth_headers(bearer))

    assert create_response.status_code == 200

    vessel = create_response.json()
    vessel_id = vessel['_id']

    second_user = await create_api_user(uuid4())
    second_user_bearer = await get_bearer_for_user(second_user, test_client)

    # Expect the first request to fail as the second user has no permission yet
    get_all_response_1 = test_client.get(f'/vessel/get_all', headers=get_auth_headers(second_user_bearer))

    assert get_all_response_1.status_code == 200
    get_all_json_1 = get_all_response_1.json()

    assert len(get_all_json_1) == 0
    
    # Assign the second user as an owner
    assign_permission_response = test_client.post(f'/vessel/set_permission/{vessel_id}/{second_user.unique_name}/owner', headers=get_auth_headers(bearer))

    assert assign_permission_response.status_code == 200

    # Now the vessel should be visible
    get_all_response_2 = test_client.get(f'/vessel/get_all', headers=get_auth_headers(second_user_bearer))

    assert get_all_response_2.status_code == 200
    get_all_json_2 = get_all_response_2.json()

    assert len(get_all_json_2) == 1