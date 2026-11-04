"""Service-level tests connecting invoice analysis and building matching."""

from copy import deepcopy

from services.rechnung_objekt_service import rechnung_objekt_zuordnen


def address(role="leistungsort", *, plz="91522", city="Ansbach", street="Musterstraße", number="2"):
    return {
        "rolle": role,
        "strasse": street,
        "hausnummer": number,
        "plz": plz,
        "stadt": city,
        "originaltext": f"{street} {number}, {plz} {city}",
    }


def building(building_id, *, plz="91522", city="Ansbach", street="Musterstraße", number="2"):
    return {
        "id": building_id,
        "adresse": {
            "plz": plz,
            "stadt": city,
            "strasse": street,
            "hausnummer": number,
        },
        "flaeche": 100,
        "miteigentumsanteile": 1000,
    }


def analysis(*addresses, **extra):
    return {"adressen": list(addresses), **extra}


def test_full_contract_maps_analysis_to_load_gebaeude_shape():
    result = rechnung_objekt_zuordnen(analysis(address()), [building(41)])
    assert result["status"] == "eindeutig"
    assert result["vorschlag_gebaeude_id"] == 41
    assert [candidate["gebaeude_id"] for candidate in result["kandidaten"]] == [41]
    assert set(result) == {"status", "vorschlag_gebaeude_id", "kandidaten", "warnungen"}


def test_multiple_performance_addresses_matching_different_buildings_are_ambiguous():
    second_address = address(
        "leistungsort", plz="90402", city="Nürnberg", street="Hauptstraße", number="10"
    )
    result = rechnung_objekt_zuordnen(
        analysis(address(), second_address),
        [building(1), building(2, plz="90402", city="Nürnberg", street="Hauptstraße", number="10")],
    )
    assert result["status"] == "mehrdeutig"
    assert result["vorschlag_gebaeude_id"] is None
    assert {candidate["gebaeude_id"] for candidate in result["kandidaten"]} == {1, 2}
    assert sum(len(candidate["adress_matches"]) for candidate in result["kandidaten"]) == 2


def test_multiple_addresses_for_same_building_keep_single_proposal():
    result = rechnung_objekt_zuordnen(
        analysis(address("leistungsort"), address("objektadresse")),
        [building(5)],
    )
    assert result["status"] == "eindeutig"
    assert result["vorschlag_gebaeude_id"] == 5
    assert len(result["kandidaten"]) == 1
    assert len(result["kandidaten"][0]["adress_matches"]) == 2


def test_duplicate_building_addresses_preserve_all_ids_and_require_review():
    result = rechnung_objekt_zuordnen(analysis(address()), [building(8), building(3)])
    assert result["status"] == "mehrdeutig"
    assert result["vorschlag_gebaeude_id"] is None
    assert {candidate["gebaeude_id"] for candidate in result["kandidaten"]} == {3, 8}


def test_unknown_role_can_only_create_review_candidate():
    result = rechnung_objekt_zuordnen(analysis(address("unbekannt")), [building(5)])
    assert result["status"] == "pruefen"
    assert result["vorschlag_gebaeude_id"] is None
    assert result["kandidaten"][0]["gebaeude_id"] == 5


def test_supplier_only_does_not_propose_building():
    result = rechnung_objekt_zuordnen(analysis(address("lieferantenadresse")), [building(5)])
    assert result["status"] == "pruefen"
    assert result["vorschlag_gebaeude_id"] is None
    assert result["kandidaten"] == []


def test_invoice_address_only_does_not_propose_building():
    result = rechnung_objekt_zuordnen(analysis(address("rechnungsadresse")), [building(5)])
    assert result["status"] == "pruefen"
    assert result["vorschlag_gebaeude_id"] is None


def test_strong_match_plus_candidate_from_another_address_is_not_single_building_choice():
    weak_other = address(
        "unbekannt", plz=None, city=None, street="Musterstraße", number="20"
    )
    result = rechnung_objekt_zuordnen(
        analysis(address(), weak_other),
        [building(1), building(2, number="20")],
    )
    assert result["status"] == "mehrdeutig"
    assert result["vorschlag_gebaeude_id"] is None
    assert {candidate["gebaeude_id"] for candidate in result["kandidaten"]} == {1, 2}
    assert any("anderen Gebäuden" in warning for warning in result["warnungen"])


def test_analysis_warnings_are_preserved_in_existing_warning_field():
    warning = "Adress-Erkennung fehlgeschlagen."
    result = rechnung_objekt_zuordnen(analysis(address(), adressen_warnungen=[warning]), [building(5)])
    assert warning in result["warnungen"]


def test_missing_or_invalid_address_list_returns_matcher_review_status():
    missing = rechnung_objekt_zuordnen({}, [building(5)])
    invalid = rechnung_objekt_zuordnen({"adressen": None}, [building(5)])
    assert missing["status"] == "pruefen"
    assert invalid["status"] == "pruefen"
    assert missing["vorschlag_gebaeude_id"] is None
    assert invalid["vorschlag_gebaeude_id"] is None


def test_analysis_and_building_inputs_are_not_mutated():
    source = analysis(address(), adressen_warnungen=["review"])
    buildings = [building(5)]
    before = deepcopy((source, buildings))
    rechnung_objekt_zuordnen(source, buildings)
    assert (source, buildings) == before
