"""
Wishlist: add/remove/view. A duplicate add is rejected rather than
silently accepted (enforced at the DB level with a unique constraint,
not just in application code), and a wishlist is scoped per user.
"""
from tests.helpers import make_product, register_and_login


def test_wishlist_requires_authentication(client):
    resp = client.get("/api/wishlist")
    assert resp.status_code == 401


def test_add_and_view_wishlist_item(client, db_session):
    headers = register_and_login(client)
    product_id = make_product(client, db_session)

    resp = client.post(
        "/api/wishlist/items", json={"product_id": product_id}, headers=headers
    )
    assert resp.status_code == 201
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["product_id"] == product_id


def test_cannot_add_same_product_twice(client, db_session):
    headers = register_and_login(client)
    product_id = make_product(client, db_session)

    client.post("/api/wishlist/items", json={"product_id": product_id}, headers=headers)
    resp = client.post(
        "/api/wishlist/items", json={"product_id": product_id}, headers=headers
    )
    assert resp.status_code == 409


def test_add_unknown_product_fails(client):
    headers = register_and_login(client)
    resp = client.post(
        "/api/wishlist/items",
        json={"product_id": "00000000-0000-0000-0000-000000000000"},
        headers=headers,
    )
    assert resp.status_code == 404


def test_remove_wishlist_item(client, db_session):
    headers = register_and_login(client)
    product_id = make_product(client, db_session)

    add_resp = client.post(
        "/api/wishlist/items", json={"product_id": product_id}, headers=headers
    )
    item_id = add_resp.json()["items"][0]["id"]

    resp = client.delete(f"/api/wishlist/items/{item_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_wishlist_is_per_user(client, db_session):
    headers_a = register_and_login(client)
    headers_b = register_and_login(client)
    product_id = make_product(client, db_session)

    client.post("/api/wishlist/items", json={"product_id": product_id}, headers=headers_a)

    resp_b = client.get("/api/wishlist", headers=headers_b)
    assert resp_b.json()["items"] == []
