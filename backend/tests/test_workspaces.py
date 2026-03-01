def test_workspace_crud(client):
    response = client.post("/api/workspaces", json={"name": "default", "dialect": "sparksql"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "default"
    workspace_id = data["id"]

    response = client.get("/api/workspaces")
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.put(f"/api/workspaces/{workspace_id}", json={"name": "main", "dialect": "hive"})
    assert response.status_code == 200
    assert response.json()["dialect"] == "hive"

    response = client.delete(f"/api/workspaces/{workspace_id}")
    assert response.status_code == 200


def test_workspace_validation_error(client):
    response = client.post("/api/workspaces", json={"name": "a", "dialect": "hive"})
    assert response.status_code == 422
    payload = response.json()
    assert payload["message"] == "validation_error"
    assert payload["details"]


def test_workspace_not_found(client):
    response = client.put("/api/workspaces/9999", json={"name": "main", "dialect": "hive"})
    assert response.status_code == 404
    assert response.json()["message"] == "workspace_not_found"

    response = client.delete("/api/workspaces/9999")
    assert response.status_code == 404
    assert response.json()["message"] == "workspace_not_found"
