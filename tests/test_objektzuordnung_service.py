from copy import deepcopy

import pytest

from services.objektzuordnung_service import zuordnung_pruefen


def objekt(objekt_id=1, *, plz="91522", stadt="Ansbach", strasse="Hauptstraße", hausnummer="12", **extra):
    return {
        "id": objekt_id,
        "adresse": {
            "plz": plz,
            "stadt": stadt,
            "strasse": strasse,
            "hausnummer": hausnummer,
        },
        **extra,
    }


def adresse(*, rolle="leistungsort", plz="91522", stadt="Ansbach", strasse="Hauptstraße", hausnummer="12"):
    return {
        "rolle": rolle,
        "plz": plz,
        "stadt": stadt,
        "strasse": strasse,
        "hausnummer": hausnummer,
    }


def test_complete_exact_match_proposes_unique_building():
    result = zuordnung_pruefen([adresse()], [objekt(42)])
    assert result["status"] == "eindeutig"
    assert result["vorschlag_gebaeude_id"] == 42
    assert [c["gebaeude_id"] for c in result["kandidaten"]] == [42]
    assert result["kandidaten"][0]["score"] == 100.0
    assert result["kandidaten"][0]["erklaerungen"]


@pytest.mark.parametrize("building_street,invoice_street", [
    ("Hauptstraße", "Hauptstrasse"),
    ("Hauptstr.", "Hauptstraße"),
    ("  HAUPTSTRASSE  ", "haupt straße"),
])
def test_street_spelling_case_and_whitespace_variants_match(building_street, invoice_street):
    result = zuordnung_pruefen(
        [adresse(strasse=invoice_street)],
        [objekt(strasse=building_street)],
    )
    assert result["status"] == "eindeutig"
    assert result["vorschlag_gebaeude_id"] == 1


def test_minor_ocr_street_error_is_review_candidate_not_auto_assignment():
    result = zuordnung_pruefen(
        [adresse(strasse="Hauptstrasße")],
        [objekt()],
    )
    assert result["status"] == "pruefen"
    assert result["vorschlag_gebaeude_id"] is None
    assert result["kandidaten"]
    assert result["kandidaten"][0]["adress_matches"][0]["ungefaehre_treffer"]["strasse"]


def test_duplicate_complete_addresses_return_all_ids_without_arbitrary_choice():
    result = zuordnung_pruefen(
        [adresse()],
        [objekt(9), objekt(3)],
    )
    assert result["status"] == "mehrdeutig"
    assert result["vorschlag_gebaeude_id"] is None
    assert {c["gebaeude_id"] for c in result["kandidaten"]} == {3, 9}


@pytest.mark.parametrize("house_number", ["12a", "12/1", "13"])
def test_different_house_numbers_do_not_match_as_same_address(house_number):
    result = zuordnung_pruefen(
        [adresse(hausnummer="12")],
        [objekt(hausnummer=house_number)],
    )
    assert result["status"] == "pruefen"
    assert result["vorschlag_gebaeude_id"] is None
    # Shared street/city/PLZ can still be useful for a manual review, but a
    # different house number must remain explicitly unmatched.
    assert result["kandidaten"][0]["adress_matches"][0]["komponententreffer"]["hausnummer"] is False
    assert result["kandidaten"][0]["adress_matches"][0]["exakt_vollstaendig"] is False


def test_different_postal_code_is_not_fuzzy_matched():
    result = zuordnung_pruefen(
        [adresse(plz="91521")],
        [objekt(plz="91522")],
    )
    assert result["status"] == "pruefen"
    assert result["vorschlag_gebaeude_id"] is None
    assert result["kandidaten"]
    assert result["kandidaten"][0]["adress_matches"][0]["komponententreffer"]["plz"] is False


def test_supplier_address_is_never_used_as_standalone_evidence():
    result = zuordnung_pruefen(
        [adresse(rolle="lieferantenadresse")],
        [objekt()],
    )
    assert result["status"] == "pruefen"
    assert result["vorschlag_gebaeude_id"] is None
    assert result["kandidaten"] == []
    assert any("Lieferantenadresse" in warning for warning in result["warnungen"])


def test_invoice_address_is_auxiliary_and_does_not_auto_assign():
    result = zuordnung_pruefen(
        [adresse(rolle="rechnungsadresse")],
        [objekt()],
    )
    assert result["status"] == "pruefen"
    assert result["vorschlag_gebaeude_id"] is None
    assert result["kandidaten"][0]["gebaeude_id"] == 1
    assert any("Hilfsmerkmal" in w for w in result["kandidaten"][0]["warnungen"])


def test_missing_components_are_not_filled_in_or_treated_as_exact():
    partial = {"rolle": "objektadresse", "plz": "91522", "stadt": "Ansbach", "strasse": "Hauptstraße"}
    result = zuordnung_pruefen([partial], [objekt()])
    assert result["status"] == "pruefen"
    assert result["vorschlag_gebaeude_id"] is None
    match = result["kandidaten"][0]["adress_matches"][0]
    assert match["komponententreffer"]["hausnummer"] is False
    assert match["exakt_vollstaendig"] is False


def test_no_matching_objects_returns_no_match():
    result = zuordnung_pruefen(
        [adresse()],
        [objekt(plz="10115", stadt="Berlin", strasse="Andere Straße", hausnummer="99")],
    )
    assert result["status"] == "kein_treffer"
    assert result["vorschlag_gebaeude_id"] is None
    assert result["kandidaten"] == []


def test_multiple_addresses_can_support_one_building():
    result = zuordnung_pruefen(
        [
            adresse(rolle="leistungsort"),
            adresse(rolle="objektadresse"),
            adresse(rolle="lieferantenadresse", plz="80331", stadt="München", strasse="Lieferweg", hausnummer="4"),
        ],
        [objekt(17)],
    )
    assert result["status"] == "eindeutig"
    assert result["vorschlag_gebaeude_id"] == 17
    assert len(result["kandidaten"][0]["adress_matches"]) == 2


def test_conflicting_full_addresses_require_review_and_no_proposal():
    result = zuordnung_pruefen(
        [
            adresse(rolle="leistungsort"),
            adresse(rolle="objektadresse", plz="80331", stadt="München", strasse="Isartorstraße", hausnummer="5"),
        ],
        [
            objekt(1),
            objekt(2, plz="80331", stadt="München", strasse="Isartorstraße", hausnummer="5"),
        ],
    )
    assert result["status"] == "mehrdeutig"
    assert result["vorschlag_gebaeude_id"] is None
    assert {c["gebaeude_id"] for c in result["kandidaten"]} == {1, 2}
    assert any("verschiedene Gebäude" in warning for warning in result["warnungen"])


def test_input_objects_are_not_modified():
    addresses = [adresse(strasse=" HAUPTSTR. ")]
    buildings = [objekt(2)]
    before = deepcopy((addresses, buildings))
    zuordnung_pruefen(addresses, buildings)
    assert (addresses, buildings) == before


def test_candidate_sorting_is_deterministic_for_ties():
    buildings = [objekt(10), objekt(2), objekt(7)]
    first = zuordnung_pruefen([adresse(rolle="rechnungsadresse")], buildings)
    second = zuordnung_pruefen([adresse(rolle="rechnungsadresse")], list(reversed(buildings)))
    assert [c["gebaeude_id"] for c in first["kandidaten"]] == [2, 7, 10]
    assert first == second
