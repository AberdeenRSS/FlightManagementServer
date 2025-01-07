import json
from typing import Coroutine
from uuid import uuid4
import pytest
from app.models.user import User
from fastapi.testclient import TestClient


from app.services.data_access.user import create_or_update_user

@pytest.mark.asyncio
async def test_get_user_names(test_client:TestClient):

    unique_name_1 = f'{uuid4()}@whatever.com'
    pw_1 = str(uuid4())

    unique_name_2 = f'{uuid4()}@whatever.com'
    pw_2 = str(uuid4())

    user1 = User(
        _id=uuid4(), 
        pw=pw_1, 
        unique_name=unique_name_1, 
        name='TEST_USER_1', 
        roles=list())
    user2 = User(
        _id=uuid4(), 
        pw=pw_2, 
        unique_name=unique_name_2, 
        name='TEST_USER_2', 
        roles=list())

    await create_or_update_user(user1)
    await create_or_update_user(user2)

    user_names_response = test_client.post('/user/get_names', json=[str(user1.id), str(user2.id)])

    assert user_names_response.status_code == 200

    user_names = user_names_response.json()

    assert str(user1.id) in user_names
    assert str(user2.id) in user_names

    assert user_names[str(user1.id)] == 'TEST_USER_1'
    assert user_names[str(user2.id)] == 'TEST_USER_2'
