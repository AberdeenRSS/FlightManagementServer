from uuid import UUID
from fastapi.testclient import TestClient
import jwt
import pytest
from app.models.vessel import Vessel
from app.services.data_access.mongodb.mongodb_connection import get_db
from tests.auth_helper import get_auth_headers
from app.models.flight import Flight
from datetime import datetime, timedelta
from datetime import timezone

@pytest.mark.asyncio
async def test_v1_delete_flight(test_client:TestClient,test_user_bearer):
    # Bearer token for test user
    bearer = await test_user_bearer
    flight_collection = get_db()["flights"]

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
    valid_until = datetime.now(timezone.utc) + timedelta(1)

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

    raw = await flight_collection.find({'_vessel_id': UUID(vessel["_id"]) }).to_list(10) 
    assert len(raw) == 1

    delete_response = test_client.delete(
        f"/v1/flights/{create_flight_data['_id']}",
        headers=get_auth_headers(bearer)
    )

    assert delete_response.status_code == 200

    raw = await flight_collection.find({'_vessel_id': UUID(vessel["_id"]) }).to_list(10) 
    assert len(raw) == 0

    # Check that the flight is deleted
    get_response = test_client.get(
        f"/v1/flights/{create_flight_data['_id']}",
        headers=get_auth_headers(bearer)
    )

    assert get_response.status_code == 404

    # Check that the vessel still exists
    get_vessel_response = test_client.get(
        f"/v1/vessels/{vessel['_id']}",
        headers=get_auth_headers(bearer)
    )
    assert get_vessel_response.status_code == 200