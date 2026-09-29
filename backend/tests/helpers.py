"""Shared test helpers. Every helper generates unique emails/slugs, so calling
one several times inside a single test can never collide."""
import uuid as uuid_lib

from app.models.user import User, UserRole
from app.repositories import user_repository
from app.utils.security import create_access_token, hash_password


def unique() -> str:
    return uuid_lib.uuid4().hex[:8]


def register_and_login(client, *, email=None, password="supersecret1", full_name="Test User"):
    email = email or f"user-{unique()}@example.com"
    client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    resp = client.post("/api/auth/login", data={"username": email, "password": password})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def admin_headers(db_session):
    email = "helpers-admin@example.com"
    admin = user_repository.get_by_email(db_session, email)
    if admin is None:
        admin = User(
            email=email,
            password_hash=hash_password("adminpass1"),
            full_name="Admin",
            role=UserRole.ADMIN,
        )
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)
    token = create_access_token(subject=str(admin.id), role=admin.role.value)
    return {"Authorization": f"Bearer {token}"}


def make_seller(client, db_session):
    headers = register_and_login(client, full_name="Seller")
    applied = client.post(
        "/api/sellers/apply", json={"business_name": f"Shop {unique()}"}, headers=headers
    )
    client.post(
        f"/api/admin/sellers/{applied.json()['id']}/approve",
        headers=admin_headers(db_session),
    )
    return headers


def make_category(client, db_session):
    u = unique()
    resp = client.post(
        "/api/categories",
        json={"name": f"Category {u}", "slug": f"category-{u}"},
        headers=admin_headers(db_session),
    )
    return resp.json()["id"]


def make_product(
    client,
    db_session,
    *,
    seller_headers=None,
    category_id=None,
    price="20.00",
    discount_price=None,
    stock=10,
    name="Test Product",
):
    seller_headers = seller_headers or make_seller(client, db_session)
    category_id = category_id or make_category(client, db_session)
    body = {"category_id": category_id, "name": name, "price": price, "initial_stock": stock}
    if discount_price is not None:
        body["discount_price"] = discount_price
    resp = client.post("/api/products", json=body, headers=seller_headers)
    return resp.json()["id"]


def make_address(client, headers, **overrides):
    body = {
        "full_name": "Asha Rao",
        "phone": "+91 98765 43210",
        "address_line": "12 MG Road",
        "city": "Pune",
        "state": "Maharashtra",
        "postal_code": "411001",
        "country": "India",
    }
    body.update(overrides)
    return client.post("/api/addresses", json=body, headers=headers).json()["id"]


def add_to_cart(client, headers, product_id, quantity=1):
    return client.post(
        "/api/cart/items",
        json={"product_id": product_id, "quantity": quantity},
        headers=headers,
    )


def checkout(client, headers, address_id, payment_method="mock_success"):
    return client.post(
        "/api/checkout",
        json={"shipping_address_id": address_id, "payment_method": payment_method},
        headers=headers,
    )


def stock_of(client, product_id) -> int:
    return client.get(f"/api/products/{product_id}").json()["available_stock"]


def cart_items(client, headers) -> list:
    return client.get("/api/cart", headers=headers).json()["items"]
