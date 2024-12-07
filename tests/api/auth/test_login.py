from uuid import uuid4
from fastapi.testclient import TestClient

def test_login(test_client:TestClient):
    unique_name = f'{uuid4()}@whatever.com'
    pw = str(uuid4())

    res = test_client.post('/auth/register', json= { 'name': 'some_name', 'unique_name': unique_name, 'pw': pw})

    assert res.status_code == 200

    login_res = test_client.post('auth/login', json={ 'unique_name': unique_name, 'pw': pw })

    assert login_res.status_code == 200

    res_payload = login_res.json()

    assert 'token' in res_payload
    assert 'refresh_token' in res_payload

    token = res_payload['token']

    authenticated_response = test_client.get('/auth/verify_authenticated', headers={'Authorization': f'Bearer {token}'})

    assert authenticated_response.status_code == 200