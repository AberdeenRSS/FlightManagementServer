from fastapi.testclient import TestClient

def test_read_docs(test_client:TestClient):
    response = test_client.get("/docs")
    assert response.status_code == 200
