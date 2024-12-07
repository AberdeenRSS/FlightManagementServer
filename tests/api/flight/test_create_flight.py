from uuid import UUID
from fastapi.testclient import TestClient
import jwt
import pytest
from app.models.vessel import Vessel
from tests.auth_helper import get_auth_headers
from app.models.flight import Flight
from datetime import datetime, timedelta
from datetime import timezone

@pytest.mark.asyncio
async def test_create_flight(test_client:TestClient,test_user_bearer):
    # Bearer token for test user
    bearer = await test_user_bearer

    vessel_name = 'Testing Vessel'

    # Create a test vessel in the UI
    create_vessel_response = test_client.post(f'/vessel/create_vessel/{vessel_name}', 
                                            headers=get_auth_headers(bearer))
    assert create_vessel_response.status_code == 200
    vessel = create_vessel_response.json()
    
    # Get Auth code for the vessel hardware to register with
    valid_until = datetime.now(timezone.utc) + timedelta(minutes=1)
    auth_code_response = test_client.post(f"/vessel/create_auth_code/{vessel['_id']}/{valid_until}",headers=get_auth_headers(bearer))
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
        f"/vessel/register",
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

    create_flight_response = test_client.post('/flight/create', 
                                            json=first_flight, 
                                            headers=get_auth_headers(vessel_bearer_token))

    assert create_flight_response.status_code == 200
    create_flight_data = create_flight_response.json()
    assert '_id' in create_flight_data
    assert create_flight_data['_vessel_id'] == vessel['_id']