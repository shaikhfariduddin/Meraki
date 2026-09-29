"""Seller-side order fulfillment: viewing and progressing orders through
the status state machine, with ownership and valid-transition checks."""
from tests.helpers import (
    add_to_cart,
    checkout,
    make_address,
    make_product,
    make_seller,
    register_and_login,
    stock_of,
)


def _placed_seller_order(client, db_session, *, stock=5, quantity=2):
    seller = make_seller(client, db_session)
    product_id = make_product(client, db_session, seller_headers=seller, stock=stock)
    customer = register_and_login(client)
    address_id = make_address(client, customer)
    add_to_cart(client, customer, product_id, quantity)
    order = checkout(client, customer, address_id).json()
    seller_order_id = order["seller_orders"][0]["id"]
    return seller, product_id, seller_order_id


def test_seller_orders_require_authentication(client):
    assert client.get("/api/sellers/orders").status_code == 401


def test_customer_cannot_access_seller_orders(client, db_session):
    customer = register_and_login(client)
    resp = client.get("/api/sellers/orders", headers=customer)
    assert resp.status_code == 403


def test_seller_sees_order_after_checkout(client, db_session):
    seller, _, seller_order_id = _placed_seller_order(client, db_session)

    resp = client.get("/api/sellers/orders", headers=seller)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == seller_order_id
    assert body["items"][0]["status"] == "placed"


def test_seller_order_detail_includes_shipping_address(client, db_session):
    seller, _, seller_order_id = _placed_seller_order(client, db_session)

    resp = client.get(f"/api/sellers/orders/{seller_order_id}", headers=seller)
    assert resp.status_code == 200
    assert resp.json()["shipping_address"]["city"] == "Pune"


def test_valid_status_progression(client, db_session):
    seller, _, seller_order_id = _placed_seller_order(client, db_session)

    for target in ("confirmed", "processing", "shipped", "delivered"):
        resp = client.patch(
            f"/api/sellers/orders/{seller_order_id}/status",
            json={"status": target},
            headers=seller,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == target

    history = client.get(
        f"/api/sellers/orders/{seller_order_id}", headers=seller
    ).json()["history"]
    assert [h["status"] for h in history] == [
        "placed",
        "confirmed",
        "processing",
        "shipped",
        "delivered",
    ]


def test_cannot_skip_a_status(client, db_session):
    seller, _, seller_order_id = _placed_seller_order(client, db_session)

    resp = client.patch(
        f"/api/sellers/orders/{seller_order_id}/status",
        json={"status": "shipped"},
        headers=seller,
    )
    assert resp.status_code == 409


def test_cannot_cancel_after_shipped(client, db_session):
    seller, _, seller_order_id = _placed_seller_order(client, db_session)
    for target in ("confirmed", "processing", "shipped"):
        client.patch(
            f"/api/sellers/orders/{seller_order_id}/status",
            json={"status": target},
            headers=seller,
        )

    resp = client.patch(
        f"/api/sellers/orders/{seller_order_id}/status",
        json={"status": "cancelled"},
        headers=seller,
    )
    assert resp.status_code == 409


def test_cancelling_returns_stock(client, db_session):
    seller, product_id, seller_order_id = _placed_seller_order(
        client, db_session, stock=5, quantity=2
    )
    assert stock_of(client, product_id) == 3

    resp = client.patch(
        f"/api/sellers/orders/{seller_order_id}/status",
        json={"status": "cancelled"},
        headers=seller,
    )
    assert resp.status_code == 200
    assert stock_of(client, product_id) == 5


def test_other_seller_cannot_see_or_update_order(client, db_session):
    _, _, seller_order_id = _placed_seller_order(client, db_session)
    other_seller = make_seller(client, db_session)

    assert (
        client.get(f"/api/sellers/orders/{seller_order_id}", headers=other_seller).status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/sellers/orders/{seller_order_id}/status",
            json={"status": "confirmed"},
            headers=other_seller,
        ).status_code
        == 404
    )
