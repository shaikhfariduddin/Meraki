"""
Seller onboarding: apply -> admin approve/reject/suspend.

Covers the state machine's valid transitions and a couple of the
invalid ones (double-apply, non-admin trying to review).
"""
from app.models.user import User, UserRole
from app.utils.security import create_access_token, hash_password


def auth_headers(client, email="alice@example.com", password="supersecret1", full_name="Alice"):
    client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    resp = client.post("/api/auth/login", data={"username": email, "password": password})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def admin_headers(db_session):
    admin = User(
        email="admin@example.com",
        password_hash=hash_password("adminpass1"),
        full_name="Admin",
        role=UserRole.ADMIN,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    token = create_access_token(subject=str(admin.id), role=admin.role.value)
    return {"Authorization": f"Bearer {token}"}


def test_customer_can_apply_for_seller(client):
    headers = auth_headers(client)
    resp = client.post(
        "/api/sellers/apply", json={"business_name": "Alice's Shop"}, headers=headers
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "pending"


def test_cannot_apply_twice_while_pending(client):
    headers = auth_headers(client)
    client.post("/api/sellers/apply", json={"business_name": "Alice's Shop"}, headers=headers)
    resp = client.post(
        "/api/sellers/apply", json={"business_name": "Alice's Shop 2"}, headers=headers
    )
    assert resp.status_code == 409


def test_non_admin_cannot_list_applications(client):
    headers = auth_headers(client)
    resp = client.get("/api/admin/sellers", headers=headers)
    assert resp.status_code == 403


def test_unauthenticated_cannot_apply(client):
    resp = client.post("/api/sellers/apply", json={"business_name": "No Auth Shop"})
    assert resp.status_code == 401


def test_admin_can_approve_seller_and_role_updates(client, db_session):
    seller_headers = auth_headers(client)
    apply_resp = client.post(
        "/api/sellers/apply", json={"business_name": "Alice's Shop"}, headers=seller_headers
    )
    seller_id = apply_resp.json()["id"]

    admin_hdrs = admin_headers(db_session)
    resp = client.post(f"/api/admin/sellers/{seller_id}/approve", headers=admin_hdrs)
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    me = client.get("/api/auth/me", headers=seller_headers)
    assert me.json()["role"] == "seller"


def test_cannot_approve_twice(client, db_session):
    seller_headers = auth_headers(client)
    apply_resp = client.post(
        "/api/sellers/apply", json={"business_name": "Alice's Shop"}, headers=seller_headers
    )
    seller_id = apply_resp.json()["id"]

    admin_hdrs = admin_headers(db_session)
    client.post(f"/api/admin/sellers/{seller_id}/approve", headers=admin_hdrs)
    second = client.post(f"/api/admin/sellers/{seller_id}/approve", headers=admin_hdrs)
    assert second.status_code == 409


def test_admin_can_reject_seller(client, db_session):
    seller_headers = auth_headers(client)
    apply_resp = client.post(
        "/api/sellers/apply", json={"business_name": "Alice's Shop"}, headers=seller_headers
    )
    seller_id = apply_resp.json()["id"]

    admin_hdrs = admin_headers(db_session)
    resp = client.post(
        f"/api/admin/sellers/{seller_id}/reject",
        json={"reason": "Incomplete business details"},
        headers=admin_hdrs,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


def test_rejected_seller_can_reapply(client, db_session):
    seller_headers = auth_headers(client)
    apply_resp = client.post(
        "/api/sellers/apply", json={"business_name": "Alice's Shop"}, headers=seller_headers
    )
    seller_id = apply_resp.json()["id"]

    admin_hdrs = admin_headers(db_session)
    client.post(f"/api/admin/sellers/{seller_id}/reject", headers=admin_hdrs)

    reapply = client.post(
        "/api/sellers/apply", json={"business_name": "Alice's Shop v2"}, headers=seller_headers
    )
    assert reapply.status_code == 201
    assert reapply.json()["status"] == "pending"


def test_admin_can_suspend_approved_seller(client, db_session):
    seller_headers = auth_headers(client)
    apply_resp = client.post(
        "/api/sellers/apply", json={"business_name": "Alice's Shop"}, headers=seller_headers
    )
    seller_id = apply_resp.json()["id"]

    admin_hdrs = admin_headers(db_session)
    client.post(f"/api/admin/sellers/{seller_id}/approve", headers=admin_hdrs)

    suspend_resp = client.post(
        f"/api/admin/sellers/{seller_id}/suspend",
        json={"reason": "Policy violation"},
        headers=admin_hdrs,
    )
    assert suspend_resp.status_code == 200
    assert suspend_resp.json()["status"] == "suspended"


def test_cannot_suspend_a_pending_seller(client, db_session):
    seller_headers = auth_headers(client)
    apply_resp = client.post(
        "/api/sellers/apply", json={"business_name": "Alice's Shop"}, headers=seller_headers
    )
    seller_id = apply_resp.json()["id"]

    admin_hdrs = admin_headers(db_session)
    resp = client.post(f"/api/admin/sellers/{seller_id}/suspend", headers=admin_hdrs)
    assert resp.status_code == 409
