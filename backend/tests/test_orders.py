"""Customer-facing order history: strictly owner-only."""
import uuid as uuid_lib

from tests.helpers import (
    add_to_cart,
    checkout,
    make_address,
    make_product,
    register_and_login,
)


def _place_order(client, db_session, *, customer=None, quantity=1):
    customer = customer or register_and_login(client)
    address_id = make_address(client, customer)
    product_id = make_product(client, db_session, price="25.00")
    add_to_cart(client, customer, product_id, quantity)
    order = checkout(client, customer, address_id).json()
    return customer, order


def test_orders_require_authentication(client):
    assert client.get("/api/orders").status_code == 401
    assert client.get(f"/api/orders/{uuid_lib.uuid4()}").status_code == 401


def test_order_list_is_paginated_and_summarised(client, db_session):
    customer, first = _place_order(client, db_session, quantity=2)
    _place_order(client, db_session, customer=customer)

    body = client.get("/api/orders", headers=customer).json()
    assert body["total"] == 2
    assert body["page"] == 1
    assert len(body["items"]) == 2
    summary = next(o for o in body["items"] if o["id"] == first["id"])
    assert summary["status"] == "placed"
    assert summary["item_count"] == 2
    assert summary["total_amount"] == "50.00"

    page_two = client.get("/api/orders", params={"page": 2, "page_size": 1}, headers=customer)
    assert page_two.json()["total"] == 2
    assert len(page_two.json()["items"]) == 1


def test_customer_only_sees_their_own_orders(client, db_session):
    alice, alice_order = _place_order(client, db_session)
    bob = register_and_login(client)

    assert client.get("/api/orders", headers=bob).json()["total"] == 0
    assert client.get("/api/orders", headers=alice).json()["total"] == 1


def test_order_detail_for_owner(client, db_session):
    customer, order = _place_order(client, db_session)

    resp = client.get(f"/api/orders/{order['id']}", headers=customer)

    assert resp.status_code == 200
    assert resp.json()["id"] == order["id"]
    assert resp.json()["payment"]["status"] == "success"


def test_cannot_read_another_customers_order(client, db_session):
    _, alice_order = _place_order(client, db_session)
    bob = register_and_login(client)

    resp = client.get(f"/api/orders/{alice_order['id']}", headers=bob)

    assert resp.status_code == 404  # same answer as "doesn't exist"


def test_unknown_order_is_404(client):
    customer = register_and_login(client)
    assert client.get(f"/api/orders/{uuid_lib.uuid4()}", headers=customer).status_code == 404
