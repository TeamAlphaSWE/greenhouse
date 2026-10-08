def create_plant(client, name="Basil"):
    return client.post("/api/v1/plants", json={"name": name}).get_json()


def test_create_plant(client):
    response = client.post("/api/v1/plants", json={"name": "Basil"})

    assert response.status_code == 201
    assert response.get_json()["name"] == "Basil"
    assert isinstance(response.get_json()["id"], str)


def test_create_plant_requires_name(client):
    response = client.post("/api/v1/plants", json={})

    assert response.status_code == 400


def test_list_plants(client):
    create_plant(client, "Basil")
    create_plant(client, "Tomato")

    response = client.get("/api/v1/plants")

    assert response.status_code == 200
    assert [p["name"] for p in response.get_json()] == ["Basil", "Tomato"]


def test_get_plant(client):
    plant = create_plant(client)

    response = client.get(f"/api/v1/plants/{plant['id']}")

    assert response.status_code == 200
    assert response.get_json() == plant


def test_get_unknown_plant_returns_404(client):
    assert client.get("/api/v1/plants/not-an-id").status_code == 404
    assert client.get("/api/v1/plants/000000000000000000000000").status_code == 404


def test_update_plant(client):
    plant = create_plant(client)

    response = client.patch(f"/api/v1/plants/{plant['id']}", json={"name": "Thai Basil"})

    assert response.status_code == 200
    assert response.get_json() == {"id": plant["id"], "name": "Thai Basil"}


def test_update_unknown_plant_returns_404(client):
    response = client.patch("/api/v1/plants/not-an-id", json={"name": "x"})

    assert response.status_code == 404


def test_delete_plant(client):
    plant = create_plant(client)

    assert client.delete(f"/api/v1/plants/{plant['id']}").status_code == 204
    assert client.get(f"/api/v1/plants/{plant['id']}").status_code == 404
    assert client.delete(f"/api/v1/plants/{plant['id']}").status_code == 404
