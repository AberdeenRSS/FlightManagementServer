from fastapi.testclient import TestClient
from uuid import UUID, uuid4
from tests.auth_helper import get_auth_headers
from tests.conftest import TEST_USER_UUID
from typing import Any
import pytest
from app.models.vessel import Vessel
from tests.auth_helper import create_api_user, get_bearer_for_user, get_auth_headers
from datetime import datetime, timedelta
from datetime import timezone
import jwt
from app.models.vessel_part import VesselPart

from app.services.data_access.mongodb.mongodb_connection import get_db
import copy


@pytest.mark.asyncio
async def test_v1_delete_vessel(test_client: TestClient, test_user_bearer):
    bearer = await test_user_bearer
    uuid_1 = UUID('a6c9efe6-bf2a-47bc-aecd-f911ed3d30d1')
    flight_collection = get_db()['flights']
    
    vessel = test_client.post(
        f'/v1/vessels/',
        headers=get_auth_headers(bearer),
        json={'name': 'Original Vessel'}
    ).json()

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

    registered_vessel = register_vessel_response.json()
    assert register_vessel_response.status_code == 200

    assert registered_vessel['name'] == 'Original Vessel'
    assert registered_vessel['_version'] == 1

    vessel_version_1 = copy.deepcopy(registered_vessel)

    vessel_part = VesselPart(
        name='Test Part',
        part_type='Test Type',
        virtual=True,
        _id = uuid_1
    )

    # Add a part to the vessel
    new_hardware_vessel = {
        'parts': [vessel_part.model_dump(mode='json')],
        'no_auth_permission':None,
        '_id':token_id,
    }

    # Register the vessel again, this will make a new version of vessel
    register_vessel_response = test_client.post(
        f"/v1/vessels/register",
        json=new_hardware_vessel,
        headers=get_auth_headers(vessel_bearer_token)
    )

    registered_vessel = register_vessel_response.json()

    assert register_vessel_response.status_code == 200
    assert registered_vessel['name'] == 'Original Vessel'
    assert registered_vessel['_version'] == 2

    vessel_version_2 = copy.deepcopy(registered_vessel)

    get_response = test_client.get(
        f"/v1/vessels/{vessel['_id']}/versions/1",
        headers=get_auth_headers(bearer)
    )

    assert get_response.status_code == 200

    # Version 2 should still exist
    get_response = test_client.get(
        f"/v1/vessels/{vessel['_id']}/versions/2",
        headers=get_auth_headers(bearer)
    )

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
    print(create_flight_data)
    assert get_response.status_code == 200

    flight_response = test_client.get(f"/v1/vessels/{vessel['_id']}/flights", 
       headers=get_auth_headers(bearer)
    )

    assert flight_response.status_code == 200
    flight_data = flight_response.json()
    print(vessel["_id"])
    print(flight_data)
    assert len(flight_data) == 1

    raw = await flight_collection.find({'_vessel_id': UUID(vessel["_id"]) }).to_list(1000) 

    assert len(raw) == 1

    # Delete the original
    delete_response = test_client.delete(
        f"/v1/vessels/{vessel['_id']}",
        headers=get_auth_headers(bearer)
    )

    assert delete_response.status_code == 200
    assert delete_response.json() == 'success'

    # Check original doesnt exist
    get_response = test_client.get(
        f"/v1/vessels/{vessel['_id']}/versions/1",
        headers=get_auth_headers(bearer)
    )
    assert get_response.status_code == 404

    get_response = test_client.get(
        f"/v1/vessels/{vessel['_id']}/versions/2",
        headers=get_auth_headers(bearer)
    )
    assert get_response.status_code == 404

    flight_response = test_client.get(f"/v1/vessels/{vessel['_id']}/flights", 
       headers=get_auth_headers(bearer)
    )

    # Vessel shouldn't exist
    assert flight_response.status_code == 400

    # The flight should be deleted from the DB
    raw = await flight_collection.find({'_vessel_id': UUID(vessel["_id"]) }).to_list(1000) 
    assert len(raw) == 0



    