def test_dialects_list(client):
    response = client.get("/api/dialects")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
