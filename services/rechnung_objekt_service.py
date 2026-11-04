"""Connect analyzed invoice addresses to explicitly supplied buildings.

This adapter performs no OCR, AI calls, database access, or persistence. It
keeps the result contract of :func:`zuordnung_pruefen` and adds a safety check
for invoices that contain candidates for more than one building.
"""

from collections.abc import Mapping

from services.objektzuordnung_service import zuordnung_pruefen


def rechnung_objekt_zuordnen(rechnungsanalyse, gebaeude):
    """Match ``rechnung_analysieren`` output against a supplied building list.

    ``adressen`` from the analysis are passed through unchanged: their role and
    flat address component names match the matcher contract, while each
    ``load_gebaeude()`` row provides ``id`` and nested ``adresse`` components
    supported by that same matcher.

    The returned mapping uses the existing matcher keys: ``status``,
    ``vorschlag_gebaeude_id``, ``kandidaten``, and ``warnungen``. If an
    otherwise unique strong-role proposal coexists with candidate buildings
    from other invoice addresses, the invoice is treated as ambiguous and no
    single building is proposed.
    """
    if isinstance(rechnungsanalyse, Mapping):
        adressen = rechnungsanalyse.get("adressen", [])
        analysis_warnings = rechnungsanalyse.get("adressen_warnungen", [])
    else:
        adressen = []
        analysis_warnings = []

    result = zuordnung_pruefen(adressen, gebaeude)

    if (
        result["status"] == "eindeutig"
        and result["vorschlag_gebaeude_id"] is not None
        and len(result["kandidaten"]) > 1
    ):
        result["status"] = "mehrdeutig"
        result["vorschlag_gebaeude_id"] = None
        result["warnungen"].append(
            "Weitere Rechnungsadressen passen zu anderen Gebäuden; die Rechnung muss geprüft werden."
        )

    if isinstance(analysis_warnings, (list, tuple)):
        result["warnungen"] = sorted(set(result["warnungen"]) | {
            str(warning) for warning in analysis_warnings if warning
        })

    return result
