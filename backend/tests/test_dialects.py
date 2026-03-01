def test_dialects_list(client):
    response = client.get("/api/dialects")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data:
        assert "code" in data[0]
        assert "label" in data[0]
