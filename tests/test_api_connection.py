import pytest


@pytest.mark.asyncio
async def test_test_controller(quart):

    client = quart.test_client()

    res = await client.get('/vessel/get_test_vessels')

    assert res.status_code == 200

