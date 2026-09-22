"""
Auth endpoint tests.

Covers: registration, duplicate email, login (success + failure), and
that a protected endpoint actually enforces the JWT.
"""


def register(client, email="alice@example.com", password="supersecret1", full_name="Alice"):
    return client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )


def test_register_creates_user(client):
    resp = register(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "alice@example.com"
    assert body["role"] == "customer"
    assert "password" not in body
    assert "password_hash" not in body


def test_register_duplicate_email_rejected(client):
    register(client)
    resp = register(client)
    assert resp.status_code == 409


def test_login_success_returns_token(client):
    register(client)
    resp = client.post(
        "/api/auth/login",
        data={"username": "alice@example.com", "password": "supersecret1"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password_rejected(client):
    register(client)
    resp = client.post(
        "/api/auth/login",
        data={"username": "alice@example.com", "password": "wrong-password"},
    )
    assert resp.status_code == 401


def test_me_requires_authentication(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_returns_current_user_with_valid_token(client):
    register(client)
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "alice@example.com", "password": "supersecret1"},
    )
    token = login_resp.json()["access_token"]
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "alice@example.com"
