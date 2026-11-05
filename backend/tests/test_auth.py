import pytest

from sqlalchemy import select
from app.passwords import hash_password
from database.models import User



# ============================================================
# TEST 1: Login erfolgreich
# ============================================================

def test_login_success(client, test_user):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "pytest_anna",
            "password": "Test12345!"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"


# ============================================================
# TEST 2: Falsches Passwort
# ============================================================

def test_login_wrong_password(client, test_user):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "pytest_anna",
            "password": "FalschesPasswort"
        }
    )

    assert response.status_code == 401


# ============================================================
# TEST 3: Unbekannter Benutzer
# ============================================================

def test_login_unknown_user(client):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "unbekannter_pytest_user",
            "password": "Test12345!"
        }
    )

    assert response.status_code == 401


# ============================================================
# TEST 4: Zugriff ohne Token
# ============================================================

def test_me_without_token(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


# ============================================================
# TEST 5: Login und Zugriff auf /me
# ============================================================

def test_me_with_token(client, test_user):
    login = client.post(
        "/api/v1/auth/login",
        json={
            "username": "pytest_anna",
            "password": "Test12345!"
        }
    )

    assert login.status_code == 200

    token = login.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    assert response.status_code == 200
    assert response.json()["username"] == "pytest_anna"
    assert response.json()["role"] == "tenant"


# ============================================================
# TEST 6: Logout macht Token ungueltig
# ============================================================

def test_logout_invalidates_token(client, test_user):
    login = client.post(
        "/api/v1/auth/login",
        json={
            "username": "pytest_anna",
            "password": "Test12345!"
        }
    )

    assert login.status_code == 200

    token = login.json()["access_token"]

    headers = {
        "Authorization": f"Bearer {token}"
    }

    logout = client.post(
        "/api/v1/auth/logout",
        headers=headers
    )

    assert logout.status_code == 204

    response = client.get(
        "/api/v1/auth/me",
        headers=headers
    )

    assert response.status_code == 401

# ============================================================
# TEST 7: Benutzer erfolgreich registrieren
# ============================================================

def test_register_success(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "pytest_new_user",
            "password": "Test12345!"
        }
    )

    assert response.status_code == 201

    data = response.json()

    assert data["username"] == "pytest_new_user"
    assert data["role"] == "tenant"
    assert "id" in data

    # Passwort darf nicht zurueckgegeben werden
    assert "password" not in data
    assert "password_hash" not in data
# ============================================================
# TEST 8: Doppelte Registrierung - HTTP 409
# ============================================================

def test_register_duplicate_username(client):
    data = {
        "username": "pytest_duplicate_user",
        "password": "Test12345!"
    }

    first = client.post(
        "/api/v1/auth/register",
        json=data
    )

    assert first.status_code == 201

    second = client.post(
        "/api/v1/auth/register",
        json=data
    )

    assert second.status_code == 409
    assert second.json()["detail"] == "Benutzername bereits vergeben"

# ============================================================
# TEST 9: Ungueltige Registrierung - HTTP 422
# ============================================================

import pytest

@pytest.mark.parametrize(
    "username,password",
    [
        ("ab", "Test12345!"),
        ("test user", "Test12345!"),
        ("pytest_short", "123"),
        ("", "Test12345!"),
    ]
)
def test_register_invalid_data(client, username, password):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "password": password
        }
    )

    assert response.status_code == 422
