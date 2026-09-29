"""
Checkout: the transactional heart of the marketplace.

The interesting tests are the failure ones — each asserts that a failed
checkout leaves NO trace: stock untouched, cart intact, no order.
"""
import uuid as uuid_lib

import pytest
from sqlalchemy.exc import IntegrityError

from app.dependencies.payment import get_payment_provider
from app.main import app
from app.models.order import Order
from app.models.payment import Payment, PaymentStatus
from app.models.product import Inventory
from app.repositories import inventory_repository
from app.services import checkout_service
from app.services.payment_provider import MockPaymentProvider
from tests.helpers import (
    add_to_cart,
    cart_items,
    checkout,
    make_address,
    make_product,
    make_seller,
    register_and_login,
    stock_of,
)


def _shopper(client):
    headers = register_and_login(client)
    return headers, make_address(client, headers)


def test_successful_checkout_creates_order_and_updates_everything(client, db_session):
    seller = make_seller(client, db_session)
    product_id = make_product(client, db_session, seller_headers=seller, price="100.00", stock=5)
    customer, address_id = _shopper(client)
    add_to_cart(client, customer, product_id, 2)

    resp = checkout(client, customer, address_id)

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "placed"
    assert body["subtotal"] == "200.00"
    assert body["discount_total"] == "0.00"
    assert body["total_amount"] == "200.00"
    assert body["payment"]["status"] == "success"
    assert body["payment"]["amount"] == "200.00"
    assert body["shipping_address"]["city"] == "Pune"
    assert len(body["seller_orders"]) == 1
    item = body["seller_orders"][0]["items"][0]
    assert item["quantity"] == 2
    assert item["unit_price"] == "100.00"
    assert item["line_total"] == "200.00"
    # status history was started
    assert [h["status"] for h in body["seller_orders"][0]["history"]] == ["placed"]

    assert stock_of(client, product_id) == 3  # 5 - 2
    assert cart_items(client, customer) == []  # cart emptied


def test_checkout_requires_authentication(client):
    resp = client.post(
        "/api/checkout",
        json={"shipping_address_id": str(uuid_lib.uuid4()), "payment_method": "mock_success"},
    )
    assert resp.status_code == 401


def test_empty_cart_is_rejected(client):
    customer, address_id = _shopper(client)
    assert checkout(client, customer, address_id).status_code == 400


def test_someone_elses_address_is_rejected(client, db_session):
    product_id = make_product(client, db_session)
    customer, _ = _shopper(client)
    other, other_address = _shopper(client)
    add_to_cart(client, customer, product_id)

    resp = checkout(client, customer, other_address)  # not customer's address

    assert resp.status_code == 404
    assert len(cart_items(client, customer)) == 1  # nothing consumed


def test_unknown_address_is_rejected(client, db_session):
    product_id = make_product(client, db_session)
    customer, _ = _shopper(client)
    add_to_cart(client, customer, product_id)

    resp = checkout(client, customer, str(uuid_lib.uuid4()))

    assert resp.status_code == 404


def test_insufficient_stock_at_checkout_changes_nothing(client, db_session):
    seller = make_seller(client, db_session)
    product_id = make_product(client, db_session, seller_headers=seller, stock=5)
    customer, address_id = _shopper(client)
    add_to_cart(client, customer, product_id, 3)
    # stock drops after the item was carted
    client.patch(
        f"/api/products/{product_id}/stock", json={"available_stock": 1}, headers=seller
    )

    resp = checkout(client, customer, address_id)

    assert resp.status_code == 409
    assert stock_of(client, product_id) == 1
    assert len(cart_items(client, customer)) == 1
    assert client.get("/api/orders", headers=customer).json()["total"] == 0


def test_product_deactivated_after_carting_blocks_checkout(client, db_session):
    seller = make_seller(client, db_session)
    product_id = make_product(client, db_session, seller_headers=seller)
    customer, address_id = _shopper(client)
    add_to_cart(client, customer, product_id)
    client.post(f"/api/products/{product_id}/deactivate", headers=seller)

    assert checkout(client, customer, address_id).status_code == 409


def test_payment_failure_leaves_no_order_and_keeps_cart(client, db_session):
    product_id = make_product(client, db_session, stock=5)
    customer, address_id = _shopper(client)
    add_to_cart(client, customer, product_id, 2)

    resp = checkout(client, customer, address_id, "mock_fail")

    assert resp.status_code == 402
    assert stock_of(client, product_id) == 5  # stock returned by the rollback
    assert len(cart_items(client, customer)) == 1
    assert client.get("/api/orders", headers=customer).json()["total"] == 0
    # the attempt itself is still recorded, for audit
    payments = db_session.query(Payment).all()
    assert len(payments) == 1
    assert payments[0].status == PaymentStatus.FAILED
    assert payments[0].order_id is None


def test_cancelled_payment_is_recorded_as_cancelled(client, db_session):
    product_id = make_product(client, db_session)
    customer, address_id = _shopper(client)
    add_to_cart(client, customer, product_id)

    resp = checkout(client, customer, address_id, "mock_cancel")

    assert resp.status_code == 402
    assert db_session.query(Payment).one().status == PaymentStatus.CANCELLED
    assert db_session.query(Order).count() == 0


def test_order_keeps_purchase_time_price_after_price_change(client, db_session):
    seller = make_seller(client, db_session)
    product_id = make_product(client, db_session, seller_headers=seller, price="100.00")
    customer, address_id = _shopper(client)
    add_to_cart(client, customer, product_id)
    order_id = checkout(client, customer, address_id).json()["id"]

    client.patch(f"/api/products/{product_id}", json={"price": "999.00"}, headers=seller)

    order = client.get(f"/api/orders/{order_id}", headers=customer).json()
    assert order["seller_orders"][0]["items"][0]["unit_price"] == "100.00"
    assert order["total_amount"] == "100.00"


def test_discount_price_is_applied_and_reported(client, db_session):
    product_id = make_product(client, db_session, price="100.00", discount_price="80.00")
    customer, address_id = _shopper(client)
    add_to_cart(client, customer, product_id, 2)

    body = checkout(client, customer, address_id).json()

    assert body["subtotal"] == "200.00"
    assert body["total_amount"] == "160.00"
    assert body["discount_total"] == "40.00"
    item = body["seller_orders"][0]["items"][0]
    assert item["list_price"] == "100.00"
    assert item["unit_price"] == "80.00"


def test_multi_seller_checkout_creates_one_order_with_two_seller_orders(client, db_session):
    product_a = make_product(client, db_session, price="10.00", name="From seller A")
    product_b = make_product(client, db_session, price="30.00", name="From seller B")
    customer, address_id = _shopper(client)
    add_to_cart(client, customer, product_a, 1)
    add_to_cart(client, customer, product_b, 2)

    body = checkout(client, customer, address_id).json()

    assert body["total_amount"] == "70.00"
    assert body["payment"]["amount"] == "70.00"  # one payment for the whole checkout
    sub_orders = body["seller_orders"]
    assert len(sub_orders) == 2
    assert len({so["seller_id"] for so in sub_orders}) == 2
    assert all(len(so["items"]) == 1 for so in sub_orders)
    assert sorted(so["total_amount"] for so in sub_orders) == ["10.00", "60.00"]


def test_failure_on_a_later_line_rolls_back_stock_taken_for_earlier_lines(
    client, db_session, monkeypatch
):
    product_a = make_product(client, db_session, stock=5)
    product_b = make_product(client, db_session, stock=5)
    customer, address_id = _shopper(client)
    add_to_cart(client, customer, product_a)
    add_to_cart(client, customer, product_b)

    real_decrement = inventory_repository.decrement_stock
    calls = {"n": 0}

    def flaky(db, product_id, quantity):
        calls["n"] += 1
        if calls["n"] == 2:  # simulate losing a race on the second line
            return 0
        return real_decrement(db, product_id, quantity)

    monkeypatch.setattr(inventory_repository, "decrement_stock", flaky)

    resp = checkout(client, customer, address_id)

    assert resp.status_code == 409
    assert calls["n"] == 2  # first line really did take stock before the failure
    assert stock_of(client, product_a) == 5  # ...and got it back
    assert stock_of(client, product_b) == 5
    assert db_session.query(Order).count() == 0
    assert len(cart_items(client, customer)) == 2


class _SpyProvider(MockPaymentProvider):
    def __init__(self):
        self.refunds = []

    def refund(self, transaction_reference):
        self.refunds.append(transaction_reference)
        return True


def test_customer_is_refunded_if_order_cannot_be_saved_after_charge(
    client, db_session, monkeypatch
):
    product_id = make_product(client, db_session, stock=5)
    customer, address_id = _shopper(client)
    add_to_cart(client, customer, product_id, 2)

    spy = _SpyProvider()
    app.dependency_overrides[get_payment_provider] = lambda: spy

    def boom(*args, **kwargs):
        raise RuntimeError("simulated database failure after the charge succeeded")

    monkeypatch.setattr(checkout_service, "_finalize_success", boom)

    with pytest.raises(RuntimeError):
        checkout(client, customer, address_id)

    assert len(spy.refunds) == 1  # compensating refund was issued
    assert stock_of(client, product_id) == 5  # nothing kept
    assert db_session.query(Order).count() == 0
    assert len(cart_items(client, customer)) == 1
    audit = db_session.query(Payment).one()
    assert audit.status == PaymentStatus.CANCELLED  # never left looking like a live payment
    assert audit.order_id is None
    assert audit.transaction_reference == spy.refunds[0]


def test_last_unit_cannot_be_sold_twice(client, db_session):
    seller = make_seller(client, db_session)
    product_id = make_product(client, db_session, seller_headers=seller, stock=2)
    alice, alice_address = _shopper(client)
    bob, bob_address = _shopper(client)
    add_to_cart(client, alice, product_id, 2)  # both valid while stock is 2
    add_to_cart(client, bob, product_id, 2)

    assert checkout(client, alice, alice_address).status_code == 201
    assert checkout(client, bob, bob_address).status_code == 409

    assert stock_of(client, product_id) == 0  # never negative
    assert db_session.query(Order).count() == 1


def test_decrement_stock_is_a_conditional_atomic_update(client, db_session):
    product_id = uuid_lib.UUID(make_product(client, db_session, stock=2))

    assert inventory_repository.decrement_stock(db_session, product_id, 2) == 1
    assert inventory_repository.decrement_stock(db_session, product_id, 1) == 0  # empty now
    db_session.commit()

    assert stock_of(client, str(product_id)) == 0


def test_database_itself_refuses_negative_stock(client, db_session):
    product_id = uuid_lib.UUID(make_product(client, db_session, stock=1))
    inventory = db_session.query(Inventory).filter(Inventory.product_id == product_id).one()

    inventory.available_stock = -1
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
