from uuid import uuid4
from fastapi.testclient import TestClient
import pytest

@pytest.mark.asyncio
async def test_auth_token(test_client:TestClient,test_user_auth_code):
    auth_code = await test_user_auth_code
    
    token_response = test_client.post('/auth/authorization_code_flow', json={'token': auth_code})

    assert token_response.status_code == 200

    res_payload = token_response.json()

    assert 'token' in res_payload
    assert 'refresh_token' in res_payload

    token = res_payload['token']

    authenticated_response = test_client.get('/auth/verify_authenticated', headers={'Authorization': f'Bearer {token}'})

    assert authenticated_response.status_code == 200