from conftest import auth_headers


def test_register_creates_user(client):
    r = client.post("/auth/register", json={
        "email": "nuevo@example.com",
        "password": "pass123",
        "name": "Nuevo",
    })
    assert r.status_code == 201
    assert "creado con éxito" in r.json()["message"]


def test_register_duplicate_email_rejected(client):
    payload = {"email": "dupe@example.com", "password": "pass123", "name": "Dupe"}
    assert client.post("/auth/register", json=payload).status_code == 201
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 400
    assert "ya está registrado" in r.json()["detail"]


def test_login_success_returns_token(client, user_factory):
    user_factory(email="login@example.com", password="correcta")
    r = client.post("/auth/login", json={"email": "login@example.com", "password": "correcta"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "login@example.com"


def test_login_wrong_password(client, user_factory):
    user_factory(email="login@example.com", password="correcta")
    r = client.post("/auth/login", json={"email": "login@example.com", "password": "incorrecta"})
    assert r.status_code == 401


def test_login_inactive_user(client, user_factory):
    user_factory(email="inactivo@example.com", password="pass123", active=False)
    r = client.post("/auth/login", json={"email": "inactivo@example.com", "password": "pass123"})
    assert r.status_code == 401


def test_forgot_password_returns_token(client, user_factory):
    user_factory(email="reset@example.com")
    r = client.post("/auth/forgot-password", json={"email": "reset@example.com"})
    assert r.status_code == 200
    assert r.json()["reset_token"]
    assert r.json()["expires_in_minutes"] == 30


def test_forgot_password_unknown_email_no_token(client):
    r = client.post("/auth/forgot-password", json={"email": "noexiste@example.com"})
    assert r.status_code == 200
    assert r.json()["reset_token"] is None


def test_reset_password_full_flow(client, user_factory):
    user_factory(email="reset@example.com", password="vieja")
    token = client.post(
        "/auth/forgot-password", json={"email": "reset@example.com"}
    ).json()["reset_token"]

    r = client.post("/auth/reset-password", json={"token": token, "new_password": "nueva-pass"})
    assert r.status_code == 200

    assert client.post(
        "/auth/login", json={"email": "reset@example.com", "password": "vieja"}
    ).status_code == 401
    assert client.post(
        "/auth/login", json={"email": "reset@example.com", "password": "nueva-pass"}
    ).status_code == 200


def test_reset_password_invalid_token(client):
    r = client.post("/auth/reset-password", json={"token": "token-falso", "new_password": "x"})
    assert r.status_code == 400


def test_reset_token_cannot_be_used_as_access_token(client, user_factory):
    user_factory(email="reset@example.com")
    reset_token = client.post(
        "/auth/forgot-password", json={"email": "reset@example.com"}
    ).json()["reset_token"]

    r = client.get("/incidents/", headers=auth_headers(reset_token))
    assert r.status_code == 401
