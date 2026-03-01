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
