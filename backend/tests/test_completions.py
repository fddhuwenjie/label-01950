def test_completions_list_and_create(client):
    response = client.get("/api/completions", params={"dialect": "sparksql"})
    assert response.status_code == 200
    base_count = len(response.json())

    response = client.post(
        "/api/completions",
        json={
            "category": "table",
            "value": "sample_table",
            "dialect": "sparksql",
            "workspace_id": None,
        },
    )
    assert response.status_code == 200

    response = client.get("/api/completions", params={"dialect": "sparksql"})
    assert response.status_code == 200
    assert len(response.json()) >= base_count + 1


def test_completions_validation_error(client):
    response = client.get("/api/completions")
    assert response.status_code == 422
    payload = response.json()
    assert payload["message"] == "validation_error"
    assert payload["details"]

    response = client.post("/api/completions", json={"category": "k", "value": "", "dialect": "h"})
    assert response.status_code == 422
    payload = response.json()
    assert payload["message"] == "validation_error"
