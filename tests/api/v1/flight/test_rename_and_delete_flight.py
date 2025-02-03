from uuid import UUID
from fastapi.testclient import TestClient
import jwt
import pytest
from app.models.vessel import Vessel
from tests.auth_helper import get_auth_headers
from app.models.flight import Flight
from datetime import datetime, timedelta
from datetime import timezone
from tests.auth_helper import create_api_user, get_bearer_for_user
from uuid import uuid4

@pytest.mark.asyncio
async def test_v1_create_flight(test_client:TestClient,test_user_bearer):
    # Bearer token for test user
    bearer = await test_user_bearer

    second_user = await create_api_user(uuid4())
    second_user_bearer = await get_bearer_for_user(second_user, test_client)

    assert bearer is not second_user_bearer

    vessel_name = 'Testing Vessel'
    
    request_body = {
        'name': vessel_name,
    }

    # Create a test vessel in the UI
    create_vessel_response = test_client.post(
        f'/v1/vessels/', 
        headers=get_auth_headers(bearer),
        json=request_body
    )

    assert create_vessel_response.status_code == 200
    vessel = create_vessel_response.json()
    
    # Get Auth code for the vessel hardware to register with
    valid_until = datetime.now(timezone.utc) + timedelta(minutes=1)

    auth_code_data = {
        'valid_until': valid_until.isoformat()
    }

    auth_code_response = test_client.post(
        f"/v1/vessels/{vessel['_id']}/auth_codes",
        headers=get_auth_headers(bearer),
        json=auth_code_data
    )

    assert auth_code_response.status_code == 200
    auth_code = auth_code_response.json()['_id']

    vessel_bearer_response = test_client.post(f"/auth/authorization_code_flow",json={'token':auth_code})
    assert vessel_bearer_response.status_code == 200
    vessel_bearer_token = vessel_bearer_response.json()['token']

    decoded_token = jwt.decode(vessel_bearer_token, options={"verify_signature": False})
    token_id = decoded_token['uid']

    # Register the vessel hardware
    hardware_vessel = {
        'parts': [],
        'no_auth_permission':None,
        '_id':token_id,
    }

    register_vessel_response = test_client.post(
        f"/v1/vessels/register",
        json=hardware_vessel,
        headers=get_auth_headers(vessel_bearer_token)
    )

    assert register_vessel_response.status_code == 200

    # Create a test flight for this vessel
    now = datetime.now(timezone.utc)
    first_flight = {
        "start":now.isoformat(),
        "_vessel_id":vessel['_id'],
        "_vessel_version":vessel['_version'],
        "name":'Test Flight',
        "measured_parts": {},
        "measured_part_ids":[],
        "available_commands":{}
    }

    create_flight_response = test_client.post('/v1/flights/', 
                                            json=first_flight, 
                                            headers=get_auth_headers(vessel_bearer_token))

    assert create_flight_response.status_code == 200
    create_flight_data = create_flight_response.json()
    assert '_id' in create_flight_data
    assert create_flight_data['_vessel_id'] == vessel['_id']

    assert create_flight_data['name'] == 'Test Flight'

    get_flight_response = test_client.get(
        f"/v1/flights/{create_flight_data['_id']}",
        headers=get_auth_headers(bearer))
    
    assert get_flight_response.status_code == 200
    get_flight_data = get_flight_response.json()
    assert get_flight_data['_id'] == create_flight_data['_id']
    assert get_flight_data['name'] == 'Test Flight'

    unauthorised_rename_flight_response = test_client.put(
        f"/v1/flights/{create_flight_data['_id']}",
        json={'name':'I shouldnt do this'},
        headers=get_auth_headers(second_user_bearer))
    
    assert unauthorised_rename_flight_response.status_code == 403

    get_flight_response = test_client.get(
        f"/v1/flights/{create_flight_data['_id']}",
        headers=get_auth_headers(bearer)
    )

    assert get_flight_response.status_code == 200
    get_flight_data = get_flight_response.json()
    assert get_flight_data['_id'] == create_flight_data['_id']
    assert get_flight_data['name'] == 'Test Flight'
    

    rename_flight_response = test_client.put(
        f"/v1/flights/{create_flight_data['_id']}",
        json={'name':'Renamed Flight'},
        headers=get_auth_headers(bearer)
    )

    assert rename_flight_response.status_code == 200
    renamed_flight = rename_flight_response.json()
    print(renamed_flight)
    assert renamed_flight['name'] == 'Renamed Flight'
    assert renamed_flight['_vessel_id'] == vessel['_id']
    
    get_flight_response = test_client.get(
        f"/v1/flights/{create_flight_data['_id']}",
        headers=get_auth_headers(bearer))
    
    assert get_flight_response.status_code == 200
    get_flight_data = get_flight_response.json()
    assert get_flight_data['_id'] == create_flight_data['_id']
    assert get_flight_data['name'] == 'Renamed Flight'

    unauthorised_delete_flight_response = test_client.delete(
        f"/v1/flights/{create_flight_data['_id']}",
        headers=get_auth_headers(second_user_bearer))
    
    assert unauthorised_delete_flight_response.status_code == 403

    delete_flight_response = test_client.delete(
        f"/v1/flights/{create_flight_data['_id']}",
        headers=get_auth_headers(bearer)
    )

    assert delete_flight_response.status_code == 200

    get_flight_response = test_client.get(
        f"/v1/flights/{create_flight_data['_id']}",
        headers=get_auth_headers(bearer))
    
    assert get_flight_response.status_code == 404