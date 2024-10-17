'''import json
from typing import Coroutine
from uuid import uuid4
import pytest
from models.user import User

from services.data_access.user import create_or_update_user

@pytest.mark.asyncio
async def test_get_user_names(quart:Quart):

    client = TestClient(app)

    unique_name_1 = f'{uuid4()}@whatever.com'
    pw_1 = str(uuid4())

    unique_name_2 = f'{uuid4()}@whatever.com'
    pw_2 = str(uuid4())

    user1 = User(uuid4(), pw_1, unique_name_1, 'TEST_USER_1', list())
    user2 = User(uuid4(), pw_2, unique_name_2, 'TEST_USER_2', list())

    await create_or_update_user(user1)
    await create_or_update_user(user2)

    user_names_response = await client.get('/user/get_names', json=[str(user1._id), str(user2._id)])

    assert user_names_response.status_code == 200

    user_names = await  user_names_response.json

    assert str(user1._id) in user_names
    assert str(user2._id) in user_names

    assert user_names[str(user1._id)] == 'TEST_USER_1'
    assert user_names[str(user2._id)] == 'TEST_USER_2'
'''