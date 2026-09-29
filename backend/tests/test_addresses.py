from tests.helpers import make_address, register_and_login


def test_addresses_require_authentication(client):
    assert client.get("/api/addresses").status_code == 401


def test_create_and_list_addresses(client):
    headers = register_and_login(client)
    make_address(client, headers, city="Pune")
    make_address(client, headers, city="Mumbai")

    resp = client.get("/api/addresses", headers=headers)
    assert resp.status_code == 200
    assert {a["city"] for a in resp.json()} == {"Pune", "Mumbai"}


def test_invalid_phone_is_rejected(client):
    headers = register_and_login(client)
    resp = client.post(
        "/api/addresses",
        json={
            "full_name": "A",
            "phone": "not-a-phone!",
            "address_line": "x",
            "city": "x",
            "state": "x",
            "postal_code": "1",
            "country": "India",
        },
        headers=headers,
    )
    assert resp.status_code == 422


def test_update_address_changes_only_sent_fields(client):
    headers = register_and_login(client)
    address_id = make_address(client, headers)

    resp = client.patch(f"/api/addresses/{address_id}", json={"city": "Nagpur"}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["city"] == "Nagpur"
    assert body["state"] == "Maharashtra"  # untouched


def test_delete_address(client):
    headers = register_and_login(client)
    address_id = make_address(client, headers)

    assert client.delete(f"/api/addresses/{address_id}", headers=headers).status_code == 204
    assert client.get("/api/addresses", headers=headers).json() == []


def test_cannot_touch_another_users_address(client):
    owner = register_and_login(client)
    intruder = register_and_login(client)
    address_id = make_address(client, owner)

    assert (
        client.patch(
            f"/api/addresses/{address_id}", json={"city": "Hacked"}, headers=intruder
        ).status_code
        == 404
    )
    assert client.delete(f"/api/addresses/{address_id}", headers=intruder).status_code == 404
    # ...and it is still intact for the owner
    assert client.get("/api/addresses", headers=owner).json()[0]["city"] == "Pune"
    # ...and invisible in the intruder's own list
    assert client.get("/api/addresses", headers=intruder).json() == []
