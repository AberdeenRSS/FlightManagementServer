from typing import Coroutine
from uuid import uuid4
from fastapi.testclient import TestClient
import pytest


@pytest.mark.asyncio
async def test_register(test_client: TestClient):

    unique_name = f'{uuid4()}@whatever.com'
    pw = str(uuid4())

    res = test_client.post('/auth/register', json= { 'name': 'some_name', 'unique_name': unique_name, 'pw': pw})

    assert res.status_code == 200

    res_payload = res.json()

    assert 'token' in res_payload
    assert 'refresh_token' in res_payload

    token = res_payload['token']

    authenticated_response = test_client.get('/auth/verify_authenticated', headers={'Authorization': f'Bearer {token}'})

    assert authenticated_response.status_code == 200

@pytest.mark.asyncio
async def test_login(test_client: TestClient):


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

@pytest.mark.asyncio
async def test_refresh_token(test_client: TestClient):

    unique_name = f'{uuid4()}@whatever.com'
    pw = str(uuid4())

    res = test_client.post('/auth/register', json= { 'name': 'some_name', 'unique_name': unique_name, 'pw': pw})

    res_content = res.json()

    assert res.status_code == 200

    refresh_response = test_client.post('/auth/authorization_code_flow', data=res_content['refresh_token'])

    assert refresh_response.status_code == 200

    res_payload = refresh_response.json()

    assert 'token' in res_payload
    assert 'refresh_token' in res_payload

    token = res_payload['token']

    authenticated_response = test_client.get('/auth/verify_authenticated', headers={'Authorization': f'Bearer {token}'})

    assert authenticated_response.status_code == 200

@pytest.mark.asyncio
async def test_auth_token(test_client: TestClient, test_user_auth_code: Coroutine[str, None, str]):
 
    auth_code = await test_user_auth_code
    
    token_response = test_client.post('/auth/authorization_code_flow', data=auth_code)

    assert token_response.status_code == 200

    res_payload = token_response.json()

    assert 'token' in res_payload
    assert 'refresh_token' in res_payload

    token = res_payload['token']

    authenticated_response = test_client.get('/auth/verify_authenticated', headers={'Authorization': f'Bearer {token}'})

    assert authenticated_response.status_code == 200

@pytest.mark.asyncio
async def test_rewoke_auth_token(test_client: TestClient, test_user_auth_code: Coroutine[str, None, str]):

    auth_code = await test_user_auth_code

    rewoke_response = test_client.post('/auth/auth_code/rewoke', data=auth_code)

    assert rewoke_response.status_code == 200

    token_response = test_client.post('/auth/authorization_code_flow', data=auth_code)

    assert token_response.status_code == 401


@pytest.mark.asyncio
async def test_require_auth(test_client: TestClient):

    authenticated_response = test_client.get('/auth/verify_authenticated')

    assert authenticated_response.status_code == 401
