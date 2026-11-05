import pytest

from app.passwords import hash_password
from database.models import Gebaeude, User, UserBuilding


# ============================================================
# Testdaten vorbereiten
# ============================================================

@pytest.fixture
def report_data(db_session):
    # Benutzer erstellen
    anna = User(
        username="pytest_reports_anna",
        password_hash=hash_password("Test12345!"),
        role="tenant"
    )

    peter = User(
        username="pytest_reports_peter",
        password_hash=hash_password("Test12345!"),
        role="tenant"
    )

    michael = User(
        username="pytest_reports_michael",
        password_hash=hash_password("Test12345!"),
        role="staff"
    )

    admin = User(
        username="pytest_reports_admin",
        password_hash=hash_password("Test12345!"),
        role="admin"
    )

    db_session.add_all([anna, peter, michael, admin])
    db_session.flush()

    # Testgebäude erstellen
    building = Gebaeude(
        strasse="Teststrasse",
        hausnummer="10",
        stadt="Ansbach",
        plz="91522"
    )

    other_building = Gebaeude(
        strasse="Andere Strasse",
        hausnummer="20",
        stadt="Ansbach",
        plz="91522"
    )

    db_session.add_all([building, other_building])
    db_session.flush()

    # Benutzer den Gebäuden zuordnen
    db_session.add_all([
        UserBuilding(user_id=anna.id, building_id=building.id),
        UserBuilding(user_id=peter.id, building_id=building.id),
        UserBuilding(user_id=michael.id, building_id=building.id),
        UserBuilding(user_id=admin.id, building_id=building.id),
        UserBuilding(user_id=admin.id, building_id=other_building.id),
    ])

    db_session.flush()

    return {
        "anna": anna,
        "peter": peter,
        "michael": michael,
        "admin": admin,
        "building": building,
        "other_building": other_building,
    }


def login(client, username):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": username,
            "password": "Test12345!"
        }
    )

    assert response.status_code == 200

    token = response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}"
    }


def create_report(client, headers, building_id):
    return client.post(
        "/api/v1/reports",
        headers=headers,
        json={
            "gebaeude_id": building_id,
            "titel": "Heizung defekt",
            "beschreibung": "Die Heizung funktioniert nicht.",
            "kategorie": "Heizung"
        }
    )


# ============================================================
# TEST 1: Meldung erstellen
# ============================================================

def test_create_report(client, report_data):
    headers = login(client, "pytest_reports_anna")

    response = create_report(
        client,
        headers,
        report_data["building"].id
    )

    assert response.status_code == 201

    data = response.json()

    assert data["titel"] == "Heizung defekt"
    assert data["status"] == "open"
    assert data["author_id"] == report_data["anna"].id


# ============================================================
# TEST 2: Fremdes Gebäude
# ============================================================

def test_create_report_foreign_building(client, report_data):
    headers = login(client, "pytest_reports_anna")

    response = create_report(
        client,
        headers,
        report_data["other_building"].id
    )

    assert response.status_code == 403


# ============================================================
# TEST 3: Fremde Meldung nicht lesen
# ============================================================

def test_cannot_read_other_users_report(client, report_data):
    anna_headers = login(client, "pytest_reports_anna")
    peter_headers = login(client, "pytest_reports_peter")

    created = create_report(
        client,
        anna_headers,
        report_data["building"].id
    )

    assert created.status_code == 201

    report_id = created.json()["id"]

    response = client.get(
        f"/api/v1/reports/{report_id}",
        headers=peter_headers
    )

    assert response.status_code == 403


# ============================================================
# TEST 4: Eigene Meldung bearbeiten
# ============================================================

def test_update_own_report(client, report_data):
    headers = login(client, "pytest_reports_anna")

    created = create_report(
        client,
        headers,
        report_data["building"].id
    )

    assert created.status_code == 201

    report_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/reports/{report_id}",
        headers=headers,
        json={
            "beschreibung": "Die Heizung ist seit gestern defekt."
        }
    )

    assert response.status_code == 200
    assert (
        response.json()["beschreibung"]
        == "Die Heizung ist seit gestern defekt."
    )


# ============================================================
# TEST 5: Mitarbeiter übernimmt Meldung
# ============================================================

def test_claim_report(client, report_data):
    anna_headers = login(client, "pytest_reports_anna")
    michael_headers = login(client, "pytest_reports_michael")

    created = create_report(
        client,
        anna_headers,
        report_data["building"].id
    )

    assert created.status_code == 201

    report_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/reports/{report_id}/claim",
        headers=michael_headers
    )

    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"
    assert (
        response.json()["assigned_user_id"]
        == report_data["michael"].id
    )


# ============================================================
# TEST 6: Meldung abschließen
# ============================================================

def test_resolve_report(client, report_data):
    anna_headers = login(client, "pytest_reports_anna")
    michael_headers = login(client, "pytest_reports_michael")

    created = create_report(
        client,
        anna_headers,
        report_data["building"].id
    )

    assert created.status_code == 201

    report_id = created.json()["id"]

    claim = client.patch(
        f"/api/v1/reports/{report_id}/claim",
        headers=michael_headers
    )

    assert claim.status_code == 200

    response = client.patch(
        f"/api/v1/reports/{report_id}/resolve",
        headers=michael_headers
    )

    assert response.status_code == 200
    assert response.json()["status"] == "resolved"


# ============================================================
# TEST 7: Erneuter Abschluss verboten
# ============================================================

def test_resolve_twice_returns_409(client, report_data):
    anna_headers = login(client, "pytest_reports_anna")
    michael_headers = login(client, "pytest_reports_michael")

    created = create_report(
        client,
        anna_headers,
        report_data["building"].id
    )

    assert created.status_code == 201

    report_id = created.json()["id"]

    claim = client.patch(
        f"/api/v1/reports/{report_id}/claim",
        headers=michael_headers
    )

    assert claim.status_code == 200

    first = client.patch(
        f"/api/v1/reports/{report_id}/resolve",
        headers=michael_headers
    )

    assert first.status_code == 200

    second = client.patch(
        f"/api/v1/reports/{report_id}/resolve",
        headers=michael_headers
    )

    assert second.status_code == 409