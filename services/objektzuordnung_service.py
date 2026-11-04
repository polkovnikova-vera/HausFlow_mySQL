"""Pure address-to-building matching helpers.

The module has no database, filesystem, Tkinter, or AI dependencies. Scores are
ranking points, not calibrated probabilities or proof that an invoice belongs
to a building. A proposal is made only for one complete, exact, strong-role
address that resolves to exactly one building ID without conflicting evidence.
"""

from difflib import SequenceMatcher
import re
import unicodedata
from typing import Any, Mapping


_ROLE_WEIGHTS = {
    "leistungsort": 1.0,
    "objektadresse": 1.0,
    "rechnungsadresse": 0.45,
    "unbekannt": 0.60,
}
_COMPONENT_POINTS = {
    "plz": 30.0,
    "stadt": 15.0,
    "strasse": 35.0,
    "hausnummer": 20.0,
}
_STRONG_ROLES = {"leistungsort", "objektadresse"}
_ADDRESS_FIELDS = ("plz", "stadt", "strasse", "hausnummer")


def _fold_text(value: Any) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value)).casefold()
    text = text.replace("ß", "ss")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalize_street(value: Any) -> str:
    text = _fold_text(value)
    if not text:
        return ""
    # Treat a standalone German street abbreviation as Straße. Do not rewrite
    # substrings inside names (e.g. "Stralau").
    text = re.sub(r"(?<!\w)str\.(?=\s|$)", "strasse", text)
    text = re.sub(r"(?<!\w)str(?=\s|$)", "strasse", text)
    text = re.sub(r"str\.$", "strasse", text)
    # German address spelling often separates the street name and suffix
    # ("Haupt Straße"). Canonicalize that boundary without altering other
    # words that merely contain the letters "str".
    text = re.sub(r"(?<=\w)\s+strasse\b", "strasse", text)
    text = re.sub(r"[^\w]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def _normalize_component(field: str, value: Any) -> str:
    if field == "strasse":
        return _normalize_street(value)
    text = _fold_text(value)
    if field == "plz":
        # Keep leading zeroes and require exact postal-code equality.
        return re.sub(r"\s+", "", text)
    if field == "hausnummer":
        # Whitespace is formatting; letters, slashes and hyphens remain
        # significant so 12, 12a and 12/1 stay distinct.
        return re.sub(r"\s+", "", text)
    text = re.sub(r"[^\w]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def _components(record: Mapping[str, Any]) -> dict[str, Any]:
    nested = record.get("adresse")
    nested = nested if isinstance(nested, Mapping) else {}
    aliases = {
        "plz": ("plz", "postleitzahl"),
        "stadt": ("stadt", "ort", "city"),
        "strasse": ("strasse", "straße", "street"),
        "hausnummer": ("hausnummer", "hausnr", "house_number"),
    }
    result = {}
    for field, keys in aliases.items():
        value = None
        for source in (record, nested):
            for key in keys:
                if key in source and source[key] not in (None, ""):
                    value = source[key]
                    break
            if value is not None:
                break
        result[field] = value
    return result


def _role(address: Mapping[str, Any]) -> str:
    raw = address.get("rolle", address.get("role", "unbekannt"))
    role = _fold_text(raw).replace("-", "_").replace(" ", "_")
    aliases = {
        "leistungsort": "leistungsort",
        "objektadresse": "objektadresse",
        "rechnungsadresse": "rechnungsadresse",
        "lieferantenadresse": "lieferantenadresse",
        "unbekannt": "unbekannt",
    }
    return aliases.get(role, "unbekannt")


def _street_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right, autojunk=False).ratio()


def _compare_address(address: Mapping[str, Any], obj: Mapping[str, Any]) -> dict:
    source = _components(address)
    target = _components(obj)
    matched = {field: False for field in _ADDRESS_FIELDS}
    fuzzy = {field: False for field in _ADDRESS_FIELDS}
    explanations = []
    points = 0.0
    compared = 0

    for field, weight in _COMPONENT_POINTS.items():
        left = _normalize_component(field, source[field])
        right = _normalize_component(field, target[field])
        if not left or not right:
            continue
        compared += 1
        if left == right:
            matched[field] = True
            points += weight
            explanations.append(f"{field}: совпадает точно")
        elif field == "strasse":
            similarity = _street_similarity(left, right)
            if similarity >= 0.82:
                matched[field] = True
                fuzzy[field] = True
                points += weight * similarity
                explanations.append(
                    f"strasse: приблизительное совпадение (сходство {similarity:.2f})"
                )
            else:
                explanations.append("strasse: существенное расхождение")
        else:
            explanations.append(f"{field}: не совпадает")

    matches = sum(matched.values())
    # PLZ/city alone is too broad to count as a building candidate. Require
    # at least two matching components, including street or house number.
    is_candidate = matches >= 2 and (matched["strasse"] or matched["hausnummer"])
    return {
        "score": points,
        "matched": matched,
        "fuzzy": fuzzy,
        "matches": matches,
        "compared": compared,
        "candidate": is_candidate,
        "exact_complete": (
            all(matched.values()) and not any(fuzzy.values())
        ),
        "explanations": explanations,
    }


def _id_sort_key(value: Any) -> tuple:
    """Stable ordering, numeric for numeric IDs and lexical for other IDs."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return (0, value)
    return (1, type(value).__name__, str(value))


def zuordnung_pruefen(adressen, objekte) -> dict:
    """Rank building candidates for recognized invoice addresses.

    Address mappings may provide ``rolle`` (or ``role``), address components
    at top level, or components nested under ``adresse``. Objects require a
    unique ``id`` and support the same component locations. Street OCR
    similarity is used only to produce a review candidate; fuzzy matches are
    never auto-proposed. Supplier addresses are excluded as matching evidence.
    """
    warnings = []
    candidates_by_id = {}
    strong_exact_targets = set()
    other_exact_targets = set()
    usable_address_count = 0

    if not isinstance(adressen, (list, tuple)):
        adressen = []
        warnings.append("Adressen müssen als Liste übergeben werden.")
    if not isinstance(objekte, (list, tuple)):
        objekte = []
        warnings.append("Objekte müssen als Liste übergeben werden.")

    valid_objects = []
    seen_ids = set()
    for index, obj in enumerate(objekte):
        if not isinstance(obj, Mapping):
            warnings.append(f"Objekt an Position {index} ist kein Mapping und wurde ignoriert.")
            continue
        if "id" not in obj or obj["id"] is None:
            warnings.append(f"Objekt an Position {index} hat keine ID und wurde ignoriert.")
            continue
        obj_id = obj["id"]
        try:
            duplicate = obj_id in seen_ids
            seen_ids.add(obj_id)
        except TypeError:
            warnings.append(f"Objekt an Position {index} hat eine nicht skalare ID und wurde ignoriert.")
            continue
        if duplicate:
            warnings.append(f"Doppelte Objekt-ID {obj_id!r}; mehrfacher Eintrag ignoriert.")
            continue
        valid_objects.append(obj)

    for address_index, address in enumerate(adressen):
        if not isinstance(address, Mapping):
            warnings.append(f"Adresse an Position {address_index} ist kein Mapping und wurde ignoriert.")
            continue
        role = _role(address)
        parts = _components(address)
        if role == "lieferantenadresse":
            warnings.append(
                f"Adresse {address_index + 1}: Lieferantenadresse wird nicht zur Objektzuordnung verwendet."
            )
            continue
        if not any(_normalize_component(field, parts[field]) for field in _ADDRESS_FIELDS):
            warnings.append(f"Adresse {address_index + 1}: keine nutzbaren Adresskomponenten.")
            continue
        usable_address_count += 1

        for obj in valid_objects:
            comparison = _compare_address(address, obj)
            if not comparison["candidate"]:
                continue
            obj_id = obj["id"]
            role_weight = _ROLE_WEIGHTS[role]
            weighted_score = comparison["score"] * role_weight
            item = candidates_by_id.setdefault(obj_id, {
                "gebaeude_id": obj_id,
                "score": 0.0,
                "adress_matches": [],
                "erklaerungen": [],
                "warnungen": [],
            })
            item["score"] = max(item["score"], weighted_score)
            item["adress_matches"].append({
                "adresse_index": address_index,
                "rolle": role,
                "komponententreffer": dict(comparison["matched"]),
                "ungefaehre_treffer": dict(comparison["fuzzy"]),
                "exakt_vollstaendig": comparison["exact_complete"],
                "roh_score": round(comparison["score"], 2),
            })
            explanations = [
                f"Rolle {role}: {entry}" for entry in comparison["explanations"]
            ]
            for explanation in explanations:
                if explanation not in item["erklaerungen"]:
                    item["erklaerungen"].append(explanation)
            if role == "rechnungsadresse":
                item["warnungen"].append(
                    "Rechnungsadresse ist nur ein Hilfsmerkmal und reicht allein nicht zur Zuordnung."
                )
            elif role == "unbekannt":
                item["warnungen"].append(
                    "Adressrolle unbekannt; Treffer muss vom Benutzer geprüft werden."
                )

            if comparison["exact_complete"]:
                other_exact_targets.add(obj_id)
                if role in _STRONG_ROLES:
                    strong_exact_targets.add(obj_id)

    candidates = list(candidates_by_id.values())
    for item in candidates:
        item["score"] = round(item["score"], 2)
        item["adress_matches"].sort(
            key=lambda match: (match["adresse_index"], match["rolle"])
        )
        item["erklaerungen"].sort()
        item["warnungen"] = sorted(set(item["warnungen"]))
    candidates.sort(key=lambda item: (-item["score"], _id_sort_key(item["gebaeude_id"])))

    proposal = None
    if len(strong_exact_targets) > 1:
        status = "mehrdeutig"
        warnings.append(
            "Mehrere vollständige Leistungsort-/Objektadresse-Treffer zeigen auf verschiedene Gebäude."
        )
    elif len(other_exact_targets) > 1:
        status = "mehrdeutig"
        warnings.append(
            "Vollständige Adressen zeigen auf verschiedene Gebäude; Zuordnung ist widersprüchlich."
        )
    elif len(strong_exact_targets) == 1:
        proposal = next(iter(strong_exact_targets))
        status = "eindeutig"
    elif candidates:
        status = "pruefen"
        if not usable_address_count:
            warnings.append("Keine geeignete Adresse zur Objektzuordnung vorhanden.")
        else:
            warnings.append(
                "Es gibt Kandidaten, aber keine eindeutige vollständige exakte Adresse mit starker Rolle."
            )
    elif usable_address_count == 0:
        status = "pruefen"
        warnings.append("Keine für die Zuordnung geeignete Adresse erkannt.")
    else:
        status = "kein_treffer"
        warnings.append("Kein passendes Gebäude gefunden.")

    # A strong exact address must still identify exactly one ID. The set above
    # naturally contains all IDs for duplicate-address buildings.
    if proposal is not None and sum(
        1 for item in candidates if item["gebaeude_id"] == proposal
    ) != 1:
        proposal = None
        status = "mehrdeutig"

    return {
        "status": status,
        "vorschlag_gebaeude_id": proposal,
        "kandidaten": candidates,
        "warnungen": sorted(set(warnings)),
    }
