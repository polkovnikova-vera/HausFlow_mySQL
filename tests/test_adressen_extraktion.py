"""Tests for isolated OCR address extraction in invoice analysis."""

from copy import deepcopy
from unittest.mock import patch

from services import ai_rechnung_service as service
from services.objektzuordnung_service import zuordnung_pruefen


OCR_TEXT = (
    "Leistungsort: Musterstr. 2, 91522 Ansbach\n"
    "Rechnungsadresse: Marktweg 7, 90402 Nürnberg\n"
    "Hauptstraße 10, 90402 Nürnberg"
)

MAIN_RESULT = {
    "firma": "Testanbieter",
    "datum": "2026-03-12",
    "betrag": 119.0,
    "kostenart": "Hausmeister",
    "umlagefaehig": None,
    "umlageschluessel": None,
    "verteilung": None,
    "betroffene_wohnung_ids": [],
    "beschreibung": "Testleistung",
    "confidence": 0.8,
    "begruendung": "Test",
}


def run_analysis(address_response=None, *, address_error=None):
    with (
        patch.object(service, "_ollama_chat", return_value=deepcopy(MAIN_RESULT)) as main_call,
        patch.object(
            service,
            "_adressen_ollama_chat",
            side_effect=address_error if address_error else None,
            return_value=deepcopy(
                {"adressen": []} if address_response is None else address_response
            ),
        ) as address_call,
        patch.object(service, "ml_beschreibung_vorhersagen", return_value=None),
        patch.object(service, "ml_kostenart_vorhersagen", return_value=None),
        patch.object(service, "ml_datum_vorhersagen", return_value=None),
        patch.object(service, "ml_status", return_value={"aktiv": False}),
        patch.object(service, "ml_debug_vorhersage", return_value={}),
    ):
        result = service.rechnung_analysieren(OCR_TEXT, [])
    main_call.assert_called_once()
    address_call.assert_called_once_with(OCR_TEXT, model=service.OLLAMA_MODEL)
    return result


def test_multiple_roles_and_multiple_performance_locations_are_preserved():
    response = {
        "adressen": [
            {
                "rolle": "leistungsort",
                "strasse": "Musterstraße",
                "hausnummer": "2",
                "plz": "91522",
                "stadt": "Ansbach",
                "originaltext": "Leistungsort: Musterstr. 2, 91522 Ansbach",
            },
            {
                "rolle": "leistungsort",
                "strasse": "Hauptstraße",
                "hausnummer": "10",
                "plz": "90402",
                "stadt": "Nürnberg",
                "originaltext": "Hauptstraße 10, 90402 Nürnberg",
            },
            {
                "rolle": "rechnungsadresse",
                "strasse": "Marktweg",
                "hausnummer": "7",
                "plz": "90402",
                "stadt": "Nürnberg",
                "originaltext": "Rechnungsadresse: Marktweg 7, 90402 Nürnberg",
            },
        ]
    }
    result = run_analysis(response)

    assert [address["rolle"] for address in result["adressen"]] == [
        "leistungsort", "leistungsort", "rechnungsadresse"
    ]
    assert all(
        set(address) == {"rolle", "strasse", "hausnummer", "plz", "stadt", "originaltext"}
        for address in result["adressen"]
    )
    assert result["adressen"][0]["strasse"] == "Musterstraße"
    # The shape is directly consumable by the independent matching service.
    matched = zuordnung_pruefen(result["adressen"], [
        {"id": 1, "plz": "91522", "stadt": "Ansbach", "strasse": "Musterstraße", "hausnummer": "2"},
    ])
    assert matched["vorschlag_gebaeude_id"] == 1


def test_missing_components_remain_none_and_unproven_components_are_removed():
    result = run_analysis({
        "adressen": [{
            "rolle": "objektadresse",
            "strasse": "Musterstraße",
            "hausnummer": "2",
            "plz": "99999",  # Not present in the cited OCR fragment.
            "stadt": None,
            "originaltext": "Leistungsort: Musterstr. 2, 91522 Ansbach",
        }]
    })
    address = result["adressen"][0]
    assert address["plz"] is None
    assert address["stadt"] is None
    assert address["hausnummer"] == "2"
    assert any("plz" in warning for warning in result["adressen_warnungen"])


def test_hallucinated_originaltext_rejects_address():
    result = run_analysis({
        "adressen": [{
            "rolle": "objektadresse",
            "strasse": "Erfundene Straße",
            "hausnummer": "99",
            "plz": "12345",
            "stadt": "Berlin",
            "originaltext": "Erfundene Straße 99, 12345 Berlin",
        }]
    })
    assert result["adressen"] == []
    assert any("nicht exakt belegt" in warning for warning in result["adressen_warnungen"])


def test_ollama_or_invalid_json_failure_does_not_break_main_analysis():
    result = run_analysis(address_error=RuntimeError("Ollama returned invalid JSON"))
    assert result["adressen"] == []
    assert result["firma"] == MAIN_RESULT["firma"]
    assert result["datum"] == MAIN_RESULT["datum"]
    assert result["betrag"] == MAIN_RESULT["betrag"]
    assert result["kostenart"] == MAIN_RESULT["kostenart"]
    assert result["beschreibung"] == MAIN_RESULT["beschreibung"]
    assert result["adressen_warnungen"]
    assert result["adressen_warnungen"][0].startswith("Adress-Erkennung fehlgeschlagen")
    assert result["adressen_warnungen"][0] in result["warnungen"]


def test_missing_or_invalid_address_list_returns_empty_with_warning():
    missing = run_analysis({})
    invalid = run_analysis({"adressen": {"rolle": "unbekannt"}})
    assert missing["adressen"] == []
    assert invalid["adressen"] == []
    assert missing["adressen_warnungen"]
    assert invalid["adressen_warnungen"]


def test_unknown_role_is_retained_as_unbekannt():
    result = run_analysis({
        "adressen": [{
            "rolle": "service_location",
            "strasse": "Musterstraße",
            "hausnummer": "2",
            "plz": "91522",
            "stadt": "Ansbach",
            "originaltext": "Leistungsort: Musterstr. 2, 91522 Ansbach",
        }]
    })
    assert result["adressen"][0]["rolle"] == "unbekannt"
    assert result["adressen_warnungen"]


def test_existing_analysis_fields_are_preserved():
    result = run_analysis({"adressen": []})
    for key, value in MAIN_RESULT.items():
        if key == "umlageschluessel":
            # The legacy analyzer deliberately publishes this as a proposal.
            assert result["umlageschluessel"] is None
        else:
            assert result[key] == value
    assert "adressen" in result
