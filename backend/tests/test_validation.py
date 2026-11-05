import pytest

from decimal import Decimal
from pydantic import ValidationError

from app.schemas import (
    LoginRequest,
    MeldungCreate,
    MeldungUpdate,
    RechnungCreate,
)


# ============================================================
# Login
# ============================================================

def test_login_empty_username():
    with pytest.raises(ValidationError):
        LoginRequest(
            username="",
            password="Test12345!"
        )


def test_login_empty_password():
    with pytest.raises(ValidationError):
        LoginRequest(
            username="anna",
            password=""
        )


# ============================================================
# Meldungen
# ============================================================

def test_meldung_empty_title():
    with pytest.raises(ValidationError):
        MeldungCreate(
            gebaeude_id=1,
            titel="",
            beschreibung="Heizung defekt"
        )


def test_meldung_title_too_long():
    with pytest.raises(ValidationError):
        MeldungCreate(
            gebaeude_id=1,
            titel="A" * 101,
            beschreibung="Heizung defekt"
        )


def test_meldung_invalid_building_id():
    with pytest.raises(ValidationError):
        MeldungCreate(
            gebaeude_id=0,
            titel="Heizung defekt",
            beschreibung="Keine Heizung"
        )


def test_meldung_empty_description():
    with pytest.raises(ValidationError):
        MeldungUpdate(
            beschreibung=""
        )


# ============================================================
# Rechnungen
# ============================================================

def valid_invoice_data():
    return {
        "gebaeude_id": 1,
        "rechnungsnummer": "RE-2026-001",
        "lieferant": "Testfirma GmbH",
        "rechnungsdatum": "2026-11-05",
        "betrag": "350.50",
        "meldung_ids": [1]
    }


def test_invoice_negative_amount():
    data = valid_invoice_data()
    data["betrag"] = "-100.00"

    with pytest.raises(ValidationError):
        RechnungCreate(**data)


def test_invoice_zero_amount():
    data = valid_invoice_data()
    data["betrag"] = "0.00"

    with pytest.raises(ValidationError):
        RechnungCreate(**data)


def test_invoice_too_many_decimals():
    data = valid_invoice_data()
    data["betrag"] = "100.123"

    with pytest.raises(ValidationError):
        RechnungCreate(**data)


def test_invoice_invalid_date():
    data = valid_invoice_data()
    data["rechnungsdatum"] = "keine-datum"

    with pytest.raises(ValidationError):
        RechnungCreate(**data)


def test_invoice_number_too_long():
    data = valid_invoice_data()
    data["rechnungsnummer"] = "R" * 51

    with pytest.raises(ValidationError):
        RechnungCreate(**data)


def test_invoice_missing_supplier():
    data = valid_invoice_data()
    del data["lieferant"]

    with pytest.raises(ValidationError):
        RechnungCreate(**data)


def test_invoice_valid_amount():
    data = valid_invoice_data()

    invoice = RechnungCreate(**data)

    assert invoice.betrag == Decimal("350.50")

# ============================================================
# TEST 14: Titel darf nicht nur Leerzeichen enthalten
# ============================================================

def test_meldung_title_only_spaces():
    with pytest.raises(ValidationError):
        MeldungCreate(
            gebaeude_id=1,
            titel="   ",
            beschreibung="Heizung funktioniert nicht"
        )

# ============================================================
# TEST 15: Ungueltige Meldungs-IDs
# ============================================================

@pytest.mark.parametrize(
    "meldung_id",
    [0, -1, -999]
)
def test_invoice_invalid_report_ids(meldung_id):
    data = valid_invoice_data()
    data["meldung_ids"] = [meldung_id]

    with pytest.raises(ValidationError):
        RechnungCreate(**data)