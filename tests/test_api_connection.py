from fastapi.testclient import TestClient


def test_test_controller(test_client: TestClient):

    res = test_client.get('/vessel/get_test_vessels')

    assert res.status_code == 200
