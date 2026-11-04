"""Pure validation helpers for invoice amounts and allocation metadata.

This module deliberately does not decide whether a cost is legally allocable.
It only normalizes supplied values and reports technical inconsistencies.
"""

from decimal import Decimal, InvalidOperation
import re
from typing import Any, Mapping, Optional


def geldbetrag_normalisieren(wert: Any) -> Optional[Decimal]:
    """Convert common German/European money strings to ``Decimal``.

    Examples accepted include ``"1.234,56 €"``, ``"1234,56"``,
    ``"1,234.56"`` and plain numeric values. Invalid or ambiguous strings
    return ``None`` rather than being guessed.
    """
    if isinstance(wert, bool) or wert is None:
        return None
    if isinstance(wert, Decimal):
        return wert if wert.is_finite() else None
    if isinstance(wert, int):
        return Decimal(wert)
    if isinstance(wert, float):
        if not (wert == wert and abs(wert) != float("inf")):
            return None
        # str avoids importing the binary float approximation into Decimal.
        wert = str(wert)
    if not isinstance(wert, str):
        return None

    text = wert.strip().replace("\u00a0", " ").replace("\u202f", " ")
    if not text:
        return None
    # Currency labels/symbols and whitespace are presentation, not value.
    text = re.sub(r"(?i)\b(?:EUR|EURO)\b|€", "", text).strip()
    text = re.sub(r"\s+", "", text)
    negative = text.startswith("-")
    if text.startswith(("+", "-")):
        text = text[1:]
    if not text or not re.fullmatch(r"\d[\d.,]*", text):
        return None

    if "," in text and "." in text:
        # The rightmost separator is the decimal mark; the other must form
        # valid groups of three. This handles both 1.234,56 and 1,234.56.
        decimal_mark = "," if text.rfind(",") > text.rfind(".") else "."
        grouping_mark = "." if decimal_mark == "," else ","
        integer_part, fraction = text.rsplit(decimal_mark, 1)
        groups = integer_part.split(grouping_mark)
        if not (1 <= len(fraction) <= 2 and groups[0].isdigit()
                and all(len(g) == 3 and g.isdigit() for g in groups[1:])):
            return None
        canonical = "".join(groups) + "." + fraction
    elif "," in text:
        left, right = text.rsplit(",", 1)
        if len(right) in (1, 2) and right.isdigit():
            if not left.isdigit():
                return None
            canonical = left + "." + right
        elif len(right) == 3 and left.isdigit() and 1 <= len(left) <= 3:
            # A lone comma with three trailing digits is ambiguous (decimal
            # thousands vs grouping); German convention is decimal, so reject.
            return None
        else:
            return None
    elif "." in text:
        left, right = text.rsplit(".", 1)
        if len(right) in (1, 2) and right.isdigit() and left.isdigit():
            canonical = left + "." + right
        elif len(right) == 3 and left.isdigit() and 1 <= len(left) <= 3:
            canonical = left + right
        else:
            groups = text.split(".")
            if not (groups[0].isdigit() and 1 <= len(groups[0]) <= 3
                    and all(len(g) == 3 and g.isdigit() for g in groups[1:])):
                return None
            canonical = "".join(groups)
    else:
        canonical = text

    try:
        amount = Decimal(canonical)
        return -amount if negative else amount
    except InvalidOperation:
        return None


def _amount_from(data: Mapping[str, Any], *keys: str) -> Optional[Decimal]:
    for key in keys:
        if key in data and data[key] is not None and data[key] != "":
            return geldbetrag_normalisieren(data[key])
    return None


def betragskandidaten_pruefen(
    nettobetrag: Any = None,
    umsatzsteuer: Any = None,
    bruttobetrag: Any = None,
    *,
    kandidater: Optional[Mapping[str, Any]] = None,
    toleranz: Any = Decimal("0.02"),
) -> dict:
    """Validate supplied net, VAT and gross amounts without choosing values.

    Values may be passed as arguments or via German/English keys in
    ``kandidater``. Multiple candidates for a field are reported as ambiguous.
    No missing amount is inferred from the other fields.
    """
    raw = {"nettobetrag": nettobetrag, "umsatzsteuer": umsatzsteuer,
           "bruttobetrag": bruttobetrag}
    aliases = {
        "nettobetrag": ("nettobetrag", "netto", "net_amount"),
        "umsatzsteuer": ("umsatzsteuer", "umsatzsteuer_betrag", "mwst", "vat"),
        "bruttobetrag": ("bruttobetrag", "brutto", "betrag", "gross_amount"),
    }
    if kandidater:
        for field, names in aliases.items():
            if raw[field] is None:
                for key in names:
                    if key in kandidater:
                        raw[field] = kandidater[key]
                        break

    amounts = {}
    ambiguous = []
    warnings = []
    for field, value in raw.items():
        if isinstance(value, (list, tuple, set)):
            parsed = [geldbetrag_normalisieren(v) for v in value]
            parsed = [v for v in parsed if v is not None]
            unique = list(dict.fromkeys(parsed))
            if len(unique) > 1:
                ambiguous.append(field)
                warnings.append(f"Mehrere unterschiedliche Kandidaten für {field}.")
                amounts[field] = None
            else:
                amounts[field] = unique[0] if unique else None
        else:
            amounts[field] = geldbetrag_normalisieren(value)
            if value not in (None, "") and amounts[field] is None:
                warnings.append(f"{field} konnte nicht eindeutig als Geldbetrag gelesen werden.")

    if ambiguous:
        status = "mehrdeutig"
    elif not any(v is not None for v in amounts.values()):
        status = "nicht_gefunden"
    else:
        status = "eindeutig"

    consistent = None
    net, vat, gross = amounts["nettobetrag"], amounts["umsatzsteuer"], amounts["bruttobetrag"]
    tol = geldbetrag_normalisieren(toleranz)
    if tol is None or tol < 0:
        tol = Decimal("0.02")
    if net is not None and vat is not None and gross is not None:
        consistent = abs((net + vat) - gross) <= tol
        if not consistent:
            warnings.append("Netto + Umsatzsteuer stimmt nicht mit Brutto überein.")
            status = "mehrdeutig"
    if status == "mehrdeutig" and not warnings:
        warnings.append("Betragsangaben sind nicht eindeutig.")

    return {
        "status": status,
        "arithmetisch_konsistent": consistent,
        "nettobetrag": net,
        "umsatzsteuer": vat,
        "bruttobetrag": gross,
        "mehrdeutige_felder": ambiguous,
        "warnungen": warnings,
    }


def umlage_konsistenz_pruefen(
    umlagefaehig: Any = None,
    umlageschluessel: Any = None,
    verteilung: Any = None,
    ausgewaehlte_wohnungen: Any = None,
    *,
    kostenart: Any = None,
    modus: Any = None,
    objektregeln: Optional[Mapping[str, Any]] = None,
) -> dict:
    """Check technical consistency only; never determine legal allocability.

    ``objektregeln`` may optionally contain ``kostenart_schluessel`` mapping
    a cost category to an iterable of configured keys for the given object
    and mode. Without such explicit configuration, compatibility is unknown.
    """
    warnings = []
    needs_review = False
    valid_distribution = {"ALLE", "AUSWAHL", "NICHT_UMLAGEFAEHIG"}
    known_keys = {"Wohnfläche", "Miteigentumsanteile", "Personenanzahl",
                  "Verbrauch", "Wohneinheiten", "Nicht umlagefähig"}
    selected = list(ausgewaehlte_wohnungen or [])

    if umlagefaehig not in (True, False, None):
        warnings.append("Umlagefähigkeit hat keinen gültigen Wahrheitswert.")
        needs_review = True
    if umlagefaehig is None:
        warnings.append("Umlagefähigkeit ist nicht bestimmt und muss geprüft werden.")
        needs_review = True
    if umlageschluessel is not None and umlageschluessel not in known_keys:
        warnings.append("Unbekannter Umlageschlüssel.")
        needs_review = True
    if verteilung is not None and verteilung not in valid_distribution:
        warnings.append("Unbekannter Verteilungstyp.")
        needs_review = True

    if umlagefaehig is False:
        if umlageschluessel not in (None, "Nicht umlagefähig"):
            warnings.append("Bei nicht umlagefähigem Eintrag ist ein Verteilungsschlüssel gesetzt.")
            needs_review = True
        if verteilung not in (None, "NICHT_UMLAGEFAEHIG"):
            warnings.append("Verteilungstyp widerspricht der Kennzeichnung als nicht umlagefähig.")
            needs_review = True
        if selected:
            warnings.append("Für nicht umlagefähigen Eintrag sind Wohnungen ausgewählt.")
            needs_review = True
    elif umlagefaehig is True:
        if umlageschluessel in (None, "Nicht umlagefähig"):
            warnings.append("Für umlagefähigen Eintrag fehlt ein passender Umlageschlüssel.")
            needs_review = True
        if verteilung == "NICHT_UMLAGEFAEHIG":
            warnings.append("Verteilungstyp widerspricht der Umlagefähigkeit.")
            needs_review = True
        if verteilung == "AUSWAHL" and not selected:
            warnings.append("Verteilung AUSWAHL erfordert mindestens eine ausgewählte Wohnung.")
            needs_review = True
        if verteilung == "ALLE" and selected:
            warnings.append("Bei Verteilung ALLE sind zusätzlich einzelne Wohnungen ausgewählt.")
            needs_review = True

    if kostenart is not None and umlageschluessel is not None:
        configured = (objektregeln or {}).get("kostenart_schluessel", {}).get(kostenart)
        if configured is None:
            warnings.append("Kompatibilität von Kostenart und Umlageschlüssel ist ohne Objektregel unbekannt.")
            needs_review = True
        elif umlageschluessel not in configured:
            warnings.append("Umlageschlüssel passt nicht zur konfigurierten Objektregel für diese Kostenart.")
            needs_review = True

    if modus not in (None, "WEG-Abrechnung", "Betriebskostenabrechnung"):
        warnings.append("Abrechnungsmodus fehlt oder ist unbekannt; rechtliche Umlagefähigkeit nicht bewertet.")
        needs_review = True
    elif modus is None:
        warnings.append("Abrechnungsmodus nicht angegeben; rechtliche Umlagefähigkeit nicht bewertet.")
        needs_review = True

    return {
        "status": "pruefen" if needs_review else "technisch_konsistent",
        "technisch_konsistent": not needs_review,
        "rechtliche_umlagefaehigkeit_bewertet": False,
        "warnungen": warnings,
    }


def kostenartwechsel_pruefen(
    alte_kostenart: Any,
    neue_kostenart: Any,
    umlageschluessel: Any = None,
    begruendung: Any = None,
    *,
    objektregeln: Optional[Mapping[str, Any]] = None,
) -> dict:
    """Report whether changing cost category requires rechecking derived fields."""
    changed = alte_kostenart != neue_kostenart
    warnings = []
    fields = []
    if changed:
        if umlageschluessel is not None:
            fields.append("umlageschluessel")
        if begruendung:
            fields.append("begruendung")
        warnings.append("Kostenart wurde geändert; abhängige Umlage-Angaben erneut prüfen.")
        configured = (objektregeln or {}).get("kostenart_schluessel", {}).get(neue_kostenart)
        if umlageschluessel is not None and configured is not None and umlageschluessel not in configured:
            warnings.append("Der bestehende Umlageschlüssel widerspricht der Objektregel für die neue Kostenart.")
        elif umlageschluessel is not None and configured is None:
            warnings.append("Kompatibilität des bestehenden Umlageschlüssels ist nicht konfiguriert.")
        if begruendung:
            warnings.append("Begründung könnte sich auf die vorherige Kostenart beziehen.")
    return {
        "geaendert": changed,
        "erneut_pruefen": changed,
        "prueffelder": fields,
        "warnungen": warnings,
    }
