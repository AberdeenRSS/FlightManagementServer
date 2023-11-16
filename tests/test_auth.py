from typing import Coroutine
from uuid import uuid4
import pytest
from quart import Quart


@pytest.mark.asyncio
async def test_register(quart: Quart):

    client = quart.test_client()

    unique_name = f'{uuid4()}@whatever.com'
    pw = str(uuid4())

    res = await client.post('/auth/register', json= { 'name': 'some_name', 'unique_name': unique_name, 'pw': pw})

    assert res.status_code == 200

    res_payload = await res.get_json()

    assert 'token' in res_payload
    assert 'refresh_token' in res_payload

    token = res_payload['token']

    authenticated_response = await client.get('/auth/verify_authenticated', headers={'Authorization': f'Bearer {token}'})

    assert authenticated_response.status_code == 200

@pytest.mark.asyncio
async def test_login(quart: Quart):

    client = quart.test_client()

    unique_name = f'{uuid4()}@whatever.com'
    pw = str(uuid4())

    res = await client.post('/auth/register', json= { 'name': 'some_name', 'unique_name': unique_name, 'pw': pw})

    assert res.status_code == 200

    login_res = await client.post('auth/login', json={ 'unique_name': unique_name, 'pw': pw })

    assert login_res.status_code == 200

    res_payload = await login_res.json

    assert 'token' in res_payload
    assert 'refresh_token' in res_payload

    token = res_payload['token']

    authenticated_response = await client.get('/auth/verify_authenticated', headers={'Authorization': f'Bearer {token}'})

    assert authenticated_response.status_code == 200

@pytest.mark.asyncio
async def test_refresh_token(quart: Quart):

    client = quart.test_client()

    unique_name = f'{uuid4()}@whatever.com'
    pw = str(uuid4())

    res = await client.post('/auth/register', json= { 'name': 'some_name', 'unique_name': unique_name, 'pw': pw})

    res_content = await res.json

    assert res.status_code == 200

    refresh_response = await client.post('/auth/authorization_code_flow', data=res_content['refresh_token'])

    assert refresh_response.status_code == 200

    res_payload = await refresh_response.json

    assert 'token' in res_payload
    assert 'refresh_token' in res_payload

    token = res_payload['token']

    authenticated_response = await client.get('/auth/verify_authenticated', headers={'Authorization': f'Bearer {token}'})

    assert authenticated_response.status_code == 200

@pytest.mark.asyncio
async def test_auth_token(quart: Quart, test_user_auth_code: Coroutine[str, None, str]):
 
    auth_code = await test_user_auth_code
    
    client = quart.test_client()

    token_response = await client.post('/auth/authorization_code_flow', data=auth_code)

    assert token_response.status_code == 200

    res_payload = await token_response.json

    assert 'token' in res_payload
    assert 'refresh_token' in res_payload

    token = res_payload['token']

    authenticated_response = await client.get('/auth/verify_authenticated', headers={'Authorization': f'Bearer {token}'})

    assert authenticated_response.status_code == 200

@pytest.mark.asyncio
async def test_rewoke_auth_token(quart:Quart, test_user_auth_code: Coroutine[str, None, str]):

    auth_code = await test_user_auth_code

    client = quart.test_client()

    rewoke_response = await client.post('/auth/auth_code/rewoke', data=auth_code)

    assert rewoke_response.status_code == 200

    token_response = await client.post('/auth/authorization_code_flow', data=auth_code)

    assert token_response.status_code == 401


@pytest.mark.asyncio
async def test_require_auth(quart: Quart):

    client = quart.test_client()

    authenticated_response = await client.get('/auth/verify_authenticated')

    assert authenticated_response.status_code == 401
