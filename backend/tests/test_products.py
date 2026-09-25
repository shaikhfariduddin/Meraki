"""
Product management: creation gated on approved-seller status,
ownership enforced on updates/deactivation/stock, and only active
products show up in the public listing.
"""
from app.models.user import User, UserRole
from app.repositories import user_repository
from app.utils.security import create_access_token, hash_password


def auth_headers(client, email, password="supersecret1", full_name="Seller"):
    client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    resp = client.post("/api/auth/login", data={"username": email, "password": password})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def admin_headers(db_session):
    # Reused across helpers within the same test — must be idempotent,
    # or the second call hits a duplicate-email constraint.
    admin = user_repository.get_by_email(db_session, "admin2@example.com")
    if admin is None:
        admin = User(
            email="admin2@example.com",
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


def make_category(client, db_session, name="Shoes", slug="shoes"):
    admin_hdrs = admin_headers(db_session)
    resp = client.post(
        "/api/categories", json={"name": name, "slug": slug}, headers=admin_hdrs
    )
    return resp.json()["id"]


def test_customer_cannot_create_product(client, db_session):
    headers = auth_headers(client, email="cust@example.com")
    category_id = make_category(client, db_session)
    resp = client.post(
        "/api/products",
        json={"category_id": category_id, "name": "Shoe", "price": "10.00"},
        headers=headers,
    )
    assert resp.status_code == 403


def test_pending_seller_cannot_create_product(client, db_session):
    headers = auth_headers(client, email="pending@example.com")
    client.post("/api/sellers/apply", json={"business_name": "Pending Shop"}, headers=headers)
    category_id = make_category(client, db_session)
    resp = client.post(
        "/api/products",
        json={"category_id": category_id, "name": "Shoe", "price": "10.00"},
        headers=headers,
    )
    assert resp.status_code == 403


def test_approved_seller_can_create_product(client, db_session):
    headers = make_approved_seller(client, db_session)
    category_id = make_category(client, db_session)
    resp = client.post(
        "/api/products",
        json={
            "category_id": category_id,
            "name": "Running Shoe",
            "description": "Comfy daily trainer",
            "price": "2999.00",
            "initial_stock": 10,
            "image_urls": ["https://example.com/shoe.jpg"],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["available_stock"] == 10
    assert len(body["images"]) == 1
    assert body["is_active"] is True


def test_create_product_with_unknown_category_fails(client, db_session):
    headers = make_approved_seller(client, db_session)
    resp = client.post(
        "/api/products",
        json={
            "category_id": "00000000-0000-0000-0000-000000000000",
            "name": "X",
            "price": "1.00",
        },
        headers=headers,
    )
    assert resp.status_code == 400


def test_discount_price_must_be_below_price(client, db_session):
    headers = make_approved_seller(client, db_session)
    category_id = make_category(client, db_session)
    resp = client.post(
        "/api/products",
        json={
            "category_id": category_id,
            "name": "Shoe",
            "price": "10.00",
            "discount_price": "15.00",
        },
        headers=headers,
    )
    assert resp.status_code == 422


def test_seller_cannot_modify_other_sellers_product(client, db_session):
    seller_a = make_approved_seller(client, db_session, email="seller-a@example.com")
    seller_b = make_approved_seller(client, db_session, email="seller-b@example.com")
    category_id = make_category(client, db_session)

    create_resp = client.post(
        "/api/products",
        json={"category_id": category_id, "name": "A's Product", "price": "5.00"},
        headers=seller_a,
    )
    product_id = create_resp.json()["id"]

    resp = client.patch(
        f"/api/products/{product_id}", json={"name": "Hijacked"}, headers=seller_b
    )
    assert resp.status_code == 403


def test_owner_can_update_and_deactivate_product(client, db_session):
    headers = make_approved_seller(client, db_session)
    category_id = make_category(client, db_session)
    create_resp = client.post(
        "/api/products",
        json={"category_id": category_id, "name": "Shoe", "price": "10.00"},
        headers=headers,
    )
    product_id = create_resp.json()["id"]

    update_resp = client.patch(
        f"/api/products/{product_id}", json={"price": "12.50"}, headers=headers
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["price"] == "12.50"

    deactivate_resp = client.post(f"/api/products/{product_id}/deactivate", headers=headers)
    assert deactivate_resp.status_code == 200
    assert deactivate_resp.json()["is_active"] is False


def test_inactive_products_excluded_from_public_listing(client, db_session):
    headers = make_approved_seller(client, db_session)
    category_id = make_category(client, db_session)
    create_resp = client.post(
        "/api/products",
        json={"category_id": category_id, "name": "Shoe", "price": "10.00"},
        headers=headers,
    )
    product_id = create_resp.json()["id"]
    client.post(f"/api/products/{product_id}/deactivate", headers=headers)

    listing = client.get("/api/products")
    ids = [p["id"] for p in listing.json()]
    assert product_id not in ids


def test_seller_can_update_own_stock(client, db_session):
    headers = make_approved_seller(client, db_session)
    category_id = make_category(client, db_session)
    create_resp = client.post(
        "/api/products",
        json={
            "category_id": category_id,
            "name": "Shoe",
            "price": "10.00",
            "initial_stock": 5,
        },
        headers=headers,
    )
    product_id = create_resp.json()["id"]

    resp = client.patch(
        f"/api/products/{product_id}/stock", json={"available_stock": 50}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["available_stock"] == 50


def test_non_admin_cannot_create_category(client):
    headers = auth_headers(client, email="notadmin@example.com")
    resp = client.post(
        "/api/categories", json={"name": "Shoes", "slug": "shoes-2"}, headers=headers
    )
    assert resp.status_code == 403
