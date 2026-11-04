import unittest
from decimal import Decimal

from services.rechnung_validation import (
    betragskandidaten_pruefen,
    geldbetrag_normalisieren,
    kostenartwechsel_pruefen,
    umlage_konsistenz_pruefen,
)


class GeldbetragNormalisierenTests(unittest.TestCase):
    def test_deutsche_formate(self):
        self.assertEqual(geldbetrag_normalisieren("1.234,56 €"), Decimal("1234.56"))
        self.assertEqual(geldbetrag_normalisieren("1234,5 EUR"), Decimal("1234.5"))
        self.assertEqual(geldbetrag_normalisieren("-99,99"), Decimal("-99.99"))

    def test_international_format_and_plain_values(self):
        self.assertEqual(geldbetrag_normalisieren("1,234.56"), Decimal("1234.56"))
        self.assertEqual(geldbetrag_normalisieren(12), Decimal("12"))
        self.assertEqual(geldbetrag_normalisieren(1.25), Decimal("1.25"))

    def test_invalid_or_ambiguous_values_are_not_guessed(self):
        for value in (None, True, "", "1,234", "12,34,56", "abc", "1.23.45"):
            with self.subTest(value=value):
                self.assertIsNone(geldbetrag_normalisieren(value))


class BetragskandidatenPruefenTests(unittest.TestCase):
    def test_consistent_net_vat_gross(self):
        result = betragskandidaten_pruefen("100,00", "19,00", "119,00")
        self.assertEqual(result["status"], "eindeutig")
        self.assertIs(result["arithmetisch_konsistent"], True)
        self.assertEqual(result["bruttobetrag"], Decimal("119.00"))

    def test_arithmetic_mismatch_requires_review(self):
        result = betragskandidaten_pruefen("100,00", "19,00", "120,00")
        self.assertEqual(result["status"], "mehrdeutig")
        self.assertIs(result["arithmetisch_konsistent"], False)
        self.assertTrue(result["warnungen"])

    def test_multiple_candidates_are_not_selected(self):
        result = betragskandidaten_pruefen(bruttobetrag=["119,00", "120,00"])
        self.assertEqual(result["status"], "mehrdeutig")
        self.assertIsNone(result["bruttobetrag"])
        self.assertIn("bruttobetrag", result["mehrdeutige_felder"])

    def test_missing_values_are_not_inferred(self):
        result = betragskandidaten_pruefen(nettobetrag="100,00", umsatzsteuer="19,00")
        self.assertIsNone(result["bruttobetrag"])
        self.assertIsNone(result["arithmetisch_konsistent"])


class UmlageKonsistenzTests(unittest.TestCase):
    def test_unknown_eligibility_requires_review(self):
        result = umlage_konsistenz_pruefen(
            umlagefaehig=None, umlageschluessel=None, verteilung=None,
            modus="Betriebskostenabrechnung",
        )
        self.assertEqual(result["status"], "pruefen")
        self.assertFalse(result["rechtliche_umlagefaehigkeit_bewertet"])

    def test_distribution_selection_mismatch(self):
        result = umlage_konsistenz_pruefen(
            True, "Wohnfläche", "AUSWAHL", [], modus="WEG-Abrechnung"
        )
        self.assertEqual(result["status"], "pruefen")
        self.assertTrue(any("AUSWAHL" in warning for warning in result["warnungen"]))

    def test_configured_category_key_pair(self):
        rules = {"kostenart_schluessel": {"Heizung": ["Verbrauch"]}}
        valid = umlage_konsistenz_pruefen(
            True, "Verbrauch", "ALLE", [], kostenart="Heizung",
            modus="WEG-Abrechnung", objektregeln=rules,
        )
        invalid = umlage_konsistenz_pruefen(
            True, "Wohnfläche", "ALLE", [], kostenart="Heizung",
            modus="WEG-Abrechnung", objektregeln=rules,
        )
        self.assertEqual(valid["status"], "technisch_konsistent")
        self.assertEqual(invalid["status"], "pruefen")
        self.assertFalse(valid["rechtliche_umlagefaehigkeit_bewertet"])

    def test_inconsistent_not_allocable_fields(self):
        result = umlage_konsistenz_pruefen(
            False, "Wohnfläche", "ALLE", ["wohnung-1"],
            modus="WEG-Abrechnung",
        )
        self.assertEqual(result["status"], "pruefen")
        self.assertGreaterEqual(len(result["warnungen"]), 2)


class KostenartwechselTests(unittest.TestCase):
    def test_change_requires_recheck_of_dependent_fields(self):
        result = kostenartwechsel_pruefen(
            "Heizung", "Reparatur", "Verbrauch", "Heizkosten laut Abrechnung"
        )
        self.assertTrue(result["erneut_pruefen"])
        self.assertEqual(set(result["prueffelder"]), {"umlageschluessel", "begruendung"})

    def test_unchanged_category_does_not_trigger_recheck(self):
        result = kostenartwechsel_pruefen("Heizung", "Heizung", "Verbrauch", "Begründung")
        self.assertFalse(result["erneut_pruefen"])
        self.assertEqual(result["warnungen"], [])


if __name__ == "__main__":
    unittest.main()
