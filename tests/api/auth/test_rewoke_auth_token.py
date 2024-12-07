import pytest
from fastapi.testclient import TestClient

@pytest.mark.asyncio
async def test_rewoke_auth_token(test_client: TestClient, test_user_auth_code):
    auth_code = await test_user_auth_code
    initial_response = test_client.post('/auth/authorization_code_flow', json={'token': auth_code})

    assert initial_response.status_code == 200

    rewoke_response = test_client.post('/auth/auth_code/rewoke', data=auth_code)

    assert rewoke_response.status_code == 200

    token_response = test_client.post('/auth/authorization_code_flow', json={'token': auth_code})

    assert token_response.status_code == 401