"""Integration contract tests for rechnung_analysieren without Ollama or ML."""

from copy import deepcopy
from unittest.mock import patch

import pytest

from services import ai_rechnung_service as service


TEXT = "TESTRECHNUNG ohne personenbezogene Daten. Betrag 119,00 EUR."
WOHNUNGEN = [
    {"id": 1, "nummer": "TEST-1", "flaeche": 50, "miteigentumsanteile": 500},
    {"id": 2, "nummer": "TEST-2", "flaeche": 70, "miteigentumsanteile": 700},
]


def antwort(**overrides):
    result = {
        "firma": "Testanbieter",
        "datum": "2026-01-15",
        "betrag": 119.0,
        "kostenart": "Heizung & Warmwasser",
        "umlagefaehig": True,
        "umlageschluessel": "Verbrauch",
        "verteilung": "ALLE",
        "betroffene_wohnung_ids": [],
        "beschreibung": "Wartung Heizung",
        "confidence": 0.9,
        "begruendung": "Testbegründung",
    }
    result.update(overrides)
    return result


def analysieren(ollama_antwort, *, ml_kostenart=None):
    """Run service with all network/model-dependent functions isolated."""
    with (
        patch.object(service, "_ollama_chat", return_value=deepcopy(ollama_antwort)) as ollama,
        patch.object(service, "_adressen_ollama_chat", return_value={"adressen": []}) as address_ollama,
        patch.object(service, "ml_beschreibung_vorhersagen", return_value=None),
        patch.object(service, "ml_kostenart_vorhersagen", return_value=ml_kostenart),
        patch.object(service, "ml_datum_vorhersagen", return_value=None),
        patch.object(service, "ml_status", return_value={"aktiv": False}),
        patch.object(service, "ml_debug_vorhersage", return_value={"debug": True}),
    ):
        result = service.rechnung_analysieren(TEXT, WOHNUNGEN)
    ollama.assert_called_once()
    address_ollama.assert_called_once()
    return result


class TestCurrentBehavior:
    """Document the existing result contract and currently observable fallbacks."""

    def test_result_keeps_legacy_contract_keys(self):
        result = analysieren(antwort())
        assert result["firma"] == "Testanbieter"
        assert result["datum"] == "2026-01-15"
        assert result["betrag"] == 119.0
        assert result["kostenart"] == "Heizung & Warmwasser"
        assert result["umlageschluessel"] is None
        assert result["umlageschluessel_vorschlag"] == "Verbrauch"
        assert result["umlagefaehig"] is True
        assert result["umlage_status"] == "pruefen"
        assert "nicht fachlich bestätigt" in result["umlagefaehig_quelle"]
        assert result["verteilung"] == "ALLE"
        assert result["betroffene_wohnung_ids"] == []
        assert "ml_status" in result
        assert "ml_debug" in result

    def test_missing_amount_remains_missing_in_service_result(self):
        result = analysieren(antwort(betrag=None))
        assert result["betrag"] is None

    def test_missing_allocation_key_is_left_unknown(self):
        result = analysieren(antwort(umlageschluessel=None))
        assert result["umlageschluessel"] is None
        assert result["umlageschluessel_vorschlag"] is None
        assert result["umlagespruefung"]["status"] == "pruefen"
        assert result["warnungen"]

    def test_unknown_cost_category_becomes_sonstiges(self):
        result = analysieren(antwort(kostenart="Unbekannte Kategorie"))
        assert result["kostenart"] == "Sonstiges"

    def test_high_confidence_ml_cost_category_replaces_ollama_category(self):
        result = analysieren(
            antwort(kostenart="Gartenpflege", umlageschluessel="Wohnfläche"),
            ml_kostenart={"kostenart": "Heizung & Warmwasser", "confidence": 0.95},
        )
        assert result["kostenart"] == "Heizung & Warmwasser"
        # Without object rules the key remains only a proposal, not a selection.
        assert result["umlageschluessel"] is None
        assert result["umlageschluessel_vorschlag"] == "Wohnfläche"

    def test_ollama_false_is_preserved_as_unconfirmed_proposal(self):
        result = analysieren(antwort(umlagefaehig=False))
        assert result["umlagefaehig"] is False
        assert "nicht fachlich bestätigt" in result["umlagefaehig_quelle"]
        assert result["umlagespruefung"]["status"] == "pruefen"

    def test_invalid_distribution_is_cleared_and_marked_for_review(self):
        result = analysieren(antwort(
            verteilung="UNSICHER",
            betroffene_wohnung_ids=["UNKNOWN-ID"],
        ))
        assert result["verteilung"] is None
        assert result["betroffene_wohnung_ids"] == []
        assert result["umlagespruefung"]["status"] == "pruefen"


class TestDesiredSafeBehavior:
    """Expected safety properties not implemented by the current service yet."""

    @pytest.mark.xfail(strict=True, reason="Проверка суммы не входит в этот этап интеграции.")
    def test_missing_amount_must_require_user_review(self):
        result = analysieren(antwort(betrag=None))
        assert result.get("betrag_status") == "nicht_gefunden"
        assert result.get("warnungen")

    def test_missing_allocation_key_must_not_be_inferred(self):
        result = analysieren(antwort(umlageschluessel=None))
        assert result["umlageschluessel"] is None
        assert result.get("umlagespruefung", {}).get("status") == "pruefen"

    @pytest.mark.xfail(strict=True, reason="Kostenartwechsel markiert abhängige Umlagefelder derzeit nicht zur Prüfung.")
    def test_cost_category_change_must_flag_allocation_fields(self):
        result = analysieren(
            antwort(kostenart="Gartenpflege", umlageschluessel="Wohnfläche"),
            ml_kostenart={"kostenart": "Heizung & Warmwasser", "confidence": 0.95},
        )
        assert result.get("kostenartwechsel_pruefung", {}).get("erneut_pruefen") is True

    def test_ollama_false_must_not_be_overwritten(self):
        result = analysieren(antwort(umlagefaehig=False))
        assert result["umlagefaehig"] is False

    def test_ambiguous_distribution_must_require_review(self):
        result = analysieren(antwort(verteilung="UNSICHER"))
        assert result["verteilung"] is None
        assert result.get("umlagespruefung", {}).get("status") == "pruefen"

    def test_missing_eligibility_is_none_and_requires_review(self):
        ollama_result = antwort()
        ollama_result.pop("umlagefaehig")
        result = analysieren(ollama_result)
        assert result["umlagefaehig"] is None
        assert result["umlagespruefung"]["status"] == "pruefen"
        assert result["warnungen"]

