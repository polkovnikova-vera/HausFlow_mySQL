# ============================================================
# HausFlow - API Sicherheitstests
# ============================================================


# TEST 1: Zugriff ohne Anmeldung
def test_reports_without_token(client):
    response = client.get("/api/v1/reports")

    assert response.status_code == 401


# TEST 2: Ungueltige Meldungs-ID
def test_invalid_report_id(client):
    response = client.get("/api/v1/reports/abc")

    assert response.status_code == 401


# TEST 3: Zugriff auf Rechnungen ohne Anmeldung
def test_invoices_without_token(client):
    response = client.get("/api/v1/invoices")

    assert response.status_code == 401


# ============================================================
# TEST 4: Nicht vorhandene Meldung
# ============================================================

def test_report_not_found(client, test_user):
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
        "/api/v1/reports/999999",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    assert response.status_code == 404


# ============================================================
# TEST 5: Ungueltige Meldungs-ID
# ============================================================

def test_report_invalid_id(client, test_user):
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
        "/api/v1/reports/abc",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    assert response.status_code == 422


# ============================================================
# TEST 6: Nicht vorhandene Rechnung
# ============================================================

def test_invoice_not_found(client, test_user):
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
        "/api/v1/invoices/999999",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    assert response.status_code == 403

# ============================================================
# TEST 7: Nicht vorhandene Rechnung - Staff
# ============================================================

def test_invoice_not_found_for_staff(client, db_session):
    from app.passwords import hash_password
    from database.models import User

    user = User(
        username="pytest_staff_404",
        password_hash=hash_password("Test12345!"),
        role="staff"
    )

    db_session.add(user)
    db_session.flush()

    login = client.post(
        "/api/v1/auth/login",
        json={
            "username": "pytest_staff_404",
            "password": "Test12345!"
        }
    )

    assert login.status_code == 200

    token = login.json()["access_token"]

    response = client.get(
        "/api/v1/invoices/999999",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    assert response.status_code == 404


# ============================================================
# TEST 8: Ungueltige Rechnungs-ID - HTTP 422
# ============================================================

def test_invoice_invalid_id(client, db_session):
    from app.passwords import hash_password
    from database.models import User

    user = User(
        username="pytest_staff_422",
        password_hash=hash_password("Test12345!"),
        role="staff"
    )

    db_session.add(user)
    db_session.flush()

    login = client.post(
        "/api/v1/auth/login",
        json={
            "username": "pytest_staff_422",
            "password": "Test12345!"
        }
    )

    assert login.status_code == 200

    token = login.json()["access_token"]

    response = client.get(
        "/api/v1/invoices/abc",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    assert response.status_code == 422