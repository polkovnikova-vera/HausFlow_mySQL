import pytest

from decimal import Decimal
from datetime import date
from sqlalchemy import select

from app.passwords import hash_password

from database.models import (
    Gebaeude,
    Meldung,
    MeldungRechnung,
    Rechnung,
    User,
    UserBuilding,
)


# ============================================================
# Testdaten vorbereiten
# ============================================================

@pytest.fixture
def invoice_data(db_session):

    password = hash_password("Test12345!")

    # Benutzer erstellen
    anna = User(
        username="pytest_invoice_anna",
        password_hash=password,
        role="tenant"
    )

    michael = User(
        username="pytest_invoice_michael",
        password_hash=password,
        role="staff"
    )

    thomas = User(
        username="pytest_invoice_thomas",
        password_hash=password,
        role="staff"
    )

    admin = User(
        username="pytest_invoice_admin",
        password_hash=password,
        role="admin"
    )

    db_session.add_all([anna, michael, thomas, admin])
    db_session.flush()

    # Gebaeude erstellen
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

    # Benutzer-Gebaeude-Zuordnungen
    db_session.add_all([
        UserBuilding(
            user_id=anna.id,
            building_id=building.id
        ),
        UserBuilding(
            user_id=michael.id,
            building_id=building.id
        ),
        UserBuilding(
            user_id=thomas.id,
            building_id=other_building.id
        ),
        UserBuilding(
            user_id=admin.id,
            building_id=building.id
        ),
        UserBuilding(
            user_id=admin.id,
            building_id=other_building.id
        ),
    ])

    db_session.flush()

    # Testmeldung erstellen
    meldung = Meldung(
        gebaeude_id=building.id,
        author_id=anna.id,
        titel="Heizung defekt",
        beschreibung="Die Heizung funktioniert nicht.",
        kategorie="Heizung",
        prioritaet="medium",
        status="open"
    )

    db_session.add(meldung)
    db_session.flush()

    return {
        "anna": anna,
        "michael": michael,
        "thomas": thomas,
        "admin": admin,
        "building": building,
        "other_building": other_building,
        "meldung": meldung,
    }


# ============================================================
# Hilfsfunktionen
# ============================================================

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


def create_invoice(client, headers, building_id, meldung_ids):
    return client.post(
        "/api/v1/invoices",
        headers=headers,
        json={
            "gebaeude_id": building_id,
            "rechnungsnummer": "RE-PYTEST-001",
            "lieferant": "Testfirma GmbH",
            "rechnungsdatum": "2026-11-05",
            "betrag": "350.50",
            "meldung_ids": meldung_ids
        }
    )


# ============================================================
# TEST 1: Rechnung erstellen
# ============================================================

def test_create_invoice(client, invoice_data):
    headers = login(client, "pytest_invoice_michael")

    response = create_invoice(
        client,
        headers,
        invoice_data["building"].id,
        [invoice_data["meldung"].id]
    )

    assert response.status_code == 201

    data = response.json()

    assert data["status"] == "open"
    assert Decimal(data["betrag"]) == Decimal("350.50")
    assert data["erstellt_von"] == invoice_data["michael"].id


# ============================================================
# TEST 2: Tenant darf keine Rechnung erstellen
# ============================================================

def test_tenant_cannot_create_invoice(client, invoice_data):
    headers = login(client, "pytest_invoice_anna")

    response = create_invoice(
        client,
        headers,
        invoice_data["building"].id,
        [invoice_data["meldung"].id]
    )

    assert response.status_code == 403


# ============================================================
# TEST 3: Fremdes Gebaeude
# ============================================================

def test_staff_cannot_create_foreign_invoice(client, invoice_data):
    headers = login(client, "pytest_invoice_thomas")

    response = create_invoice(
        client,
        headers,
        invoice_data["building"].id,
        [invoice_data["meldung"].id]
    )

    assert response.status_code == 403


# ============================================================
# TEST 4: M:N-Verknuepfung
# ============================================================

def test_invoice_report_relation(client, db_session, invoice_data):
    headers = login(client, "pytest_invoice_michael")

    response = create_invoice(
        client,
        headers,
        invoice_data["building"].id,
        [invoice_data["meldung"].id]
    )

    assert response.status_code == 201

    invoice_id = response.json()["id"]

    relation = db_session.scalar(
        select(MeldungRechnung).where(
            MeldungRechnung.rechnung_id == invoice_id,
            MeldungRechnung.meldung_id == invoice_data["meldung"].id
        )
    )

    assert relation is not None


# ============================================================
# TEST 5: Rechnungen anzeigen
# ============================================================

def test_get_invoices(client, invoice_data):
    headers = login(client, "pytest_invoice_michael")

    created = create_invoice(
        client,
        headers,
        invoice_data["building"].id,
        [invoice_data["meldung"].id]
    )

    assert created.status_code == 201

    response = client.get(
        "/api/v1/invoices",
        headers=headers
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


# ============================================================
# TEST 6: Rechnung bezahlen
# ============================================================

def test_pay_invoice(client, invoice_data):
    headers = login(client, "pytest_invoice_michael")

    created = create_invoice(
        client,
        headers,
        invoice_data["building"].id,
        [invoice_data["meldung"].id]
    )

    assert created.status_code == 201

    invoice_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/invoices/{invoice_id}",
        headers=headers
    )

    assert response.status_code == 200
    assert response.json()["status"] == "paid"
    assert response.json()["bezahlt_am"] == date.today().isoformat()


# ============================================================
# TEST 7: Erneute Bezahlung verboten
# ============================================================

def test_pay_invoice_twice(client, invoice_data):
    headers = login(client, "pytest_invoice_michael")

    created = create_invoice(
        client,
        headers,
        invoice_data["building"].id,
        [invoice_data["meldung"].id]
    )

    assert created.status_code == 201

    invoice_id = created.json()["id"]

    first = client.patch(
        f"/api/v1/invoices/{invoice_id}",
        headers=headers
    )

    assert first.status_code == 200

    second = client.patch(
        f"/api/v1/invoices/{invoice_id}",
        headers=headers
    )

    assert second.status_code == 409


# ============================================================
# TEST 8: Fremde Meldung und Rollback
# ============================================================

def test_invoice_foreign_report(client, db_session, invoice_data):
    headers = login(client, "pytest_invoice_admin")

    response = create_invoice(
        client,
        headers,
        invoice_data["other_building"].id,
        [invoice_data["meldung"].id]
    )

    # API muss die Verknuepfung ablehnen
    assert response.status_code == 409

    # Es darf keine Rechnung gespeichert werden
    invoice = db_session.scalar(
        select(Rechnung).where(
            Rechnung.rechnungsnummer == "RE-PYTEST-001"
        )
    )

    assert invoice is None

# ============================================================
# TEST 9: Rollback bei Datenbankfehler
# ============================================================

def test_invoice_rollback_on_database_error(db_session):
    from sqlalchemy.exc import IntegrityError

    # Testdaten verwenden
    user = User(
        username="pytest_rollback_user",
        password_hash=hash_password("Test12345!"),
        role="staff"
    )

    building = Gebaeude(
        strasse="Rollbackstrasse",
        hausnummer="99",
        stadt="Ansbach",
        plz="91522"
    )

    db_session.add_all([user, building])
    db_session.flush()

    # Eigenen SAVEPOINT fuer den Fehlertest erstellen
    savepoint = db_session.begin_nested()

    invoice_id = None

    try:
        # Rechnung erstellen
        invoice = Rechnung(
            gebaeude_id=building.id,
            erstellt_von=user.id,
            rechnungsnummer="RE-ROLLBACK-TEST",
            lieferant="Testfirma",
            rechnungsdatum=date(2026, 11, 5),
            betrag=Decimal("100.00"),
            status="open",
            bezahlt_am=None
        )

        db_session.add(invoice)
        db_session.flush()

        invoice_id = invoice.id

        # Fehlerhafte M:N-Verknuepfung
        relation = MeldungRechnung(
            meldung_id=999999999,
            rechnung_id=invoice_id
        )

        db_session.add(relation)

        # MySQL muss Foreign-Key-Fehler ausloesen
        with pytest.raises(IntegrityError):
            db_session.flush()

    finally:
        # Fehlerhafte Transaktion zurueckrollen
        savepoint.rollback()

    # Rechnung darf nach Rollback nicht existieren
    invoice = db_session.scalar(
        select(Rechnung).where(
            Rechnung.rechnungsnummer == "RE-ROLLBACK-TEST"
        )
    )

    assert invoice is None