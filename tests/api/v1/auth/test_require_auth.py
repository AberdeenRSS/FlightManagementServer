import pytest
from fastapi.testclient import TestClient

@pytest.mark.asyncio
async def test_require_auth(test_client: TestClient):

    authenticated_response = test_client.get('/auth/verify_authenticated')

    assert authenticated_response.status_code == 401