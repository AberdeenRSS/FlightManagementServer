from uuid import uuid4
from fastapi.testclient import TestClient

def test_refresh_token(test_client:TestClient):
    unique_name = f'{uuid4()}@whatever.com'
    pw = str(uuid4())
    data = {
        "name": "some_name",
        "unique_name": unique_name,
        "pw": pw
    }
    res = test_client.post('/auth/register', json=data)

    res_content = res.json()

    assert res.status_code == 200
    res_payload = res.json()
    assert 'token' in res_payload
    assert 'refresh_token' in res_payload

    refresh_token = res_payload['refresh_token']

    refresh_response = test_client.post('/auth/authorization_code_flow', json={'token': refresh_token})

    assert refresh_response.status_code == 200

    res_payload = refresh_response.json()

    assert 'token' in res_payload
    assert 'refresh_token' in res_payload

    token = res_payload['token']

    authenticated_response = test_client.get('/auth/verify_authenticated', headers={'Authorization': f'Bearer {token}'})

    assert authenticated_response.status_code == 200