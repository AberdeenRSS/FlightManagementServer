from datetime import datetime, timedelta
from typing import Coroutine
from uuid import uuid4
import pytest
from quart import Quart

from tests.auth_helper import create_api_user, get_auth_headers, get_bearer_for_user


@pytest.mark.asyncio
async def test_create_vehicle_auth_code(quart: Quart, test_user_bearer: Coroutine[str, None, str]):    
    '''Tests that vehicle auth codes can only be created by the vessel owners'''

    bearer = await test_user_bearer

    vessel_name = 'Testing Vessel'

    client = quart.test_client()

    create_response = await client.post(f'/vessel/create_vessel/{vessel_name}', headers=get_auth_headers(bearer))

    assert create_response.status_code == 200

    vessel = await create_response.json
    vessel_id = vessel['_id']

    second_user = await create_api_user(uuid4())
    second_user_bearer = await get_bearer_for_user(second_user, client)

    valid_until = datetime.utcnow() + timedelta(1)

    # Expect the first request to fail as the second user has no permission yet
    create_auth_code_response_1 = await client.post(f'/vessel/create_auth_code/{vessel_id}/{valid_until.isoformat()}', headers=get_auth_headers(second_user_bearer))

    assert create_auth_code_response_1.status_code == 403

    # Assign the second user as an owner
    assign_permission_response = await client.post(f'/vessel/set_permission/{vessel_id}/{second_user.unique_name}/owner', headers=get_auth_headers(bearer))

    assert assign_permission_response.status_code == 200

    # Now creating the code should work
    create_auth_code_response_2 = await client.post(f'/vessel/create_auth_code/{vessel_id}/{valid_until.isoformat()}', headers=get_auth_headers(second_user_bearer))

    assert create_auth_code_response_2.status_code == 200

@pytest.mark.asyncio
async def test_vessel_view_privileges(quart: Quart, test_user_bearer: Coroutine[str, None, str]):    
    '''Tests that the vehicles can only be seen if the user has "view" permissions'''

    bearer = await test_user_bearer

    vessel_name = 'Testing Vessel'

    client = quart.test_client()

    create_response = await client.post(f'/vessel/create_vessel/{vessel_name}', headers=get_auth_headers(bearer))

    assert create_response.status_code == 200

    vessel = await create_response.json
    vessel_id = vessel['_id']

    second_user = await create_api_user(uuid4())
    second_user_bearer = await get_bearer_for_user(second_user, client)


    # Expect the first request to fail as the second user has no permission yet
    get_all_response_1 = await client.get(f'/vessel/get_all', headers=get_auth_headers(second_user_bearer))

    assert get_all_response_1.status_code == 200
    get_all_json_1 = await get_all_response_1.json

    assert len(get_all_json_1) == 0
    
    # Assign the second user as an owner
    assign_permission_response = await client.post(f'/vessel/set_permission/{vessel_id}/{second_user.unique_name}/owner', headers=get_auth_headers(bearer))

    assert assign_permission_response.status_code == 200

    # Now the vessel should be visible
    get_all_response_2 = await client.get(f'/vessel/get_all', headers=get_auth_headers(second_user_bearer))

    assert get_all_response_2.status_code == 200
    get_all_json_2 = await get_all_response_2.json

    assert len(get_all_json_2) == 1
