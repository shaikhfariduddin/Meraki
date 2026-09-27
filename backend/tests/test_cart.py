"""
Cart: add/update/remove/clear, all re-validated server-side against
the live product (active status, stock), never trusting the client's
last-known price or subtotal.
"""
import uuid as uuid_lib

from app.models.user import User, UserRole
from app.repositories import user_repository
from app.utils.security import create_access_token, hash_password


def auth_headers(client, email, password="supersecret1", full_name="Customer"):
    client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    resp = client.post("/api/auth/login", data={"username": email, "password": password})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def admin_headers(db_session):
    admin = user_repository.get_by_email(db_session, "admin3@example.com")
    if admin is None:
        admin = User(
            email="admin3@example.com",
            password_hash=hash_password("adminpass1"),
            full_name="Admin",
            role=UserRole.ADMIN,
        )
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)
    token = create_access_token(subject=str(admin.id), role=admin.role.value)
    return {"Authorization": f"Bearer {token}"}


def make_approved_seller(client, db_session, email="seller@example.com"):
    headers = auth_headers(client, email=email)
    apply_resp = client.post(
        "/api/sellers/apply", json={"business_name": "Test Shop"}, headers=headers
    )
    admin_hdrs = admin_headers(db_session)
    client.post(
        f"/api/admin/sellers/{apply_resp.json()['id']}/approve", headers=admin_hdrs
    )
    return headers


def make_category(client, db_session, name="General", slug="general-cart"):
    admin_hdrs = admin_headers(db_session)
    resp = client.post(
        "/api/categories", json={"name": name, "slug": slug}, headers=admin_hdrs
    )
    return resp.json()["id"]


def make_product(client, db_session, price="20.00", stock=10):
    unique = uuid_lib.uuid4().hex[:8]
    seller_headers = make_approved_seller(
        client, db_session, email=f"cart-seller-{unique}@example.com"
    )
    category_id = make_category(client, db_session, name="General", slug=f"general-cart-{unique}")
    resp = client.post(
        "/api/products",
        json={
            "category_id": category_id,
            "name": "Cart Test Product",
            "price": price,
            "initial_stock": stock,
        },
        headers=seller_headers,
    )
    return resp.json()["id"]


def test_cart_requires_authentication(client):
    resp = client.get("/api/cart")
    assert resp.status_code == 401


def test_add_item_to_empty_cart(client, db_session):
    customer = auth_headers(client, email="cust1@example.com")
    product_id = make_product(client, db_session)

    resp = client.post(
        "/api/cart/items",
        json={"product_id": product_id, "quantity": 2},
        headers=customer,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 2
    assert body["subtotal"] == "40.00"
    assert body["item_count"] == 2


def test_adding_same_product_twice_accumulates_quantity(client, db_session):
    customer = auth_headers(client, email="cust2@example.com")
    product_id = make_product(client, db_session, stock=10)

    client.post(
        "/api/cart/items", json={"product_id": product_id, "quantity": 2}, headers=customer
    )
    resp = client.post(
        "/api/cart/items", json={"product_id": product_id, "quantity": 3}, headers=customer
    )
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 5


def test_cannot_add_more_than_available_stock(client, db_session):
    customer = auth_headers(client, email="cust3@example.com")
    product_id = make_product(client, db_session, stock=3)

    resp = client.post(
        "/api/cart/items", json={"product_id": product_id, "quantity": 5}, headers=customer
    )
    assert resp.status_code == 409


def test_cannot_add_inactive_product(client, db_session):
    seller_headers = make_approved_seller(client, db_session, email="deactivate-seller@example.com")
    category_id = make_category(client, db_session, name="Deactivated", slug="deactivated-cart")
    create_resp = client.post(
        "/api/products",
        json={"category_id": category_id, "name": "Soon Gone", "price": "10.00"},
        headers=seller_headers,
    )
    product_id = create_resp.json()["id"]
    client.post(f"/api/products/{product_id}/deactivate", headers=seller_headers)

    customer = auth_headers(client, email="cust4@example.com")
    resp = client.post(
        "/api/cart/items", json={"product_id": product_id, "quantity": 1}, headers=customer
    )
    assert resp.status_code == 409


def test_update_item_quantity(client, db_session):
    customer = auth_headers(client, email="cust5@example.com")
    product_id = make_product(client, db_session, price="15.00", stock=10)

    add_resp = client.post(
        "/api/cart/items", json={"product_id": product_id, "quantity": 1}, headers=customer
    )
    item_id = add_resp.json()["items"][0]["id"]

    resp = client.patch(
        f"/api/cart/items/{item_id}", json={"quantity": 4}, headers=customer
    )
    body = resp.json()
    assert body["items"][0]["quantity"] == 4
    assert body["subtotal"] == "60.00"


def test_update_item_quantity_beyond_stock_fails(client, db_session):
    customer = auth_headers(client, email="cust6@example.com")
    product_id = make_product(client, db_session, stock=3)

    add_resp = client.post(
        "/api/cart/items", json={"product_id": product_id, "quantity": 1}, headers=customer
    )
    item_id = add_resp.json()["items"][0]["id"]

    resp = client.patch(
        f"/api/cart/items/{item_id}", json={"quantity": 10}, headers=customer
    )
    assert resp.status_code == 409


def test_remove_item(client, db_session):
    customer = auth_headers(client, email="cust7@example.com")
    product_id = make_product(client, db_session)

    add_resp = client.post(
        "/api/cart/items", json={"product_id": product_id, "quantity": 1}, headers=customer
    )
    item_id = add_resp.json()["items"][0]["id"]

    resp = client.delete(f"/api/cart/items/{item_id}", headers=customer)
    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_clear_cart(client, db_session):
    customer = auth_headers(client, email="cust8@example.com")
    product_a = make_product(client, db_session)
    product_b = make_product(client, db_session)

    client.post(
        "/api/cart/items", json={"product_id": product_a, "quantity": 1}, headers=customer
    )
    client.post(
        "/api/cart/items", json={"product_id": product_b, "quantity": 1}, headers=customer
    )

    resp = client.delete("/api/cart", headers=customer)
    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_cannot_modify_another_users_cart_item(client, db_session):
    customer_a = auth_headers(client, email="cust9@example.com")
    customer_b = auth_headers(client, email="cust10@example.com")
    product_id = make_product(client, db_session)

    add_resp = client.post(
        "/api/cart/items", json={"product_id": product_id, "quantity": 1}, headers=customer_a
    )
    item_id = add_resp.json()["items"][0]["id"]

    resp = client.patch(
        f"/api/cart/items/{item_id}", json={"quantity": 2}, headers=customer_b
    )
    assert resp.status_code == 404


def test_empty_cart_returns_zero_subtotal(client, db_session):
    customer = auth_headers(client, email="cust11@example.com")
    resp = client.get("/api/cart", headers=customer)
    body = resp.json()
    assert body["items"] == []
    assert body["subtotal"] == "0"
    assert body["item_count"] == 0
