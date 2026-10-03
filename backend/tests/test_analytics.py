from tests.helpers import (
    add_to_cart,
    admin_headers,
    checkout,
    make_address,
    make_category,
    make_product,
    make_seller,
    register_and_login,
)


def test_admin_analytics_requires_admin(client):
    headers = register_and_login(client)
    resp = client.get("/api/admin/analytics", headers=headers)
    assert resp.status_code == 403


def test_seller_analytics_requires_approved_seller(client):
    headers = register_and_login(client)
    resp = client.get("/api/sellers/analytics", headers=headers)
    assert resp.status_code == 403


def test_admin_analytics_reflects_platform_state(client, db_session):
    seller_headers = make_seller(client, db_session)
    category_id = make_category(client, db_session)
    product_id = make_product(
        client,
        db_session,
        seller_headers=seller_headers,
        category_id=category_id,
        price="25.00",
        stock=2,
    )

    customer_headers = register_and_login(client)
    add_to_cart(client, customer_headers, product_id, quantity=1)
    address_id = make_address(client, customer_headers)
    checkout(client, customer_headers, address_id)

    resp = client.get("/api/admin/analytics", headers=admin_headers(db_session))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_sellers"] >= 1
    assert body["total_products"] >= 1
    assert body["total_orders"] >= 1
    assert float(body["total_revenue"]) >= 25.00
    assert body["pending_orders"] >= 1
    assert body["low_stock_products"] >= 1


def test_seller_analytics_scoped_to_own_products(client, db_session):
    seller_headers = make_seller(client, db_session)
    category_id = make_category(client, db_session)
    make_product(
        client,
        db_session,
        seller_headers=seller_headers,
        category_id=category_id,
        price="10.00",
        stock=50,
    )
    make_product(
        client,
        db_session,
        seller_headers=seller_headers,
        category_id=category_id,
        price="15.00",
        stock=1,
    )

    other_seller_headers = make_seller(client, db_session)
    make_product(client, db_session, seller_headers=other_seller_headers, category_id=category_id)

    resp = client.get("/api/sellers/analytics", headers=seller_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_products"] == 2
    assert body["low_stock_products"] == 1
