import json
import os


def load_json(path):
    # Wenn Datei nicht existiert → leere Liste zurückgeben
    if not os.path.exists(path):
        return []

    try:
        # JSON-Datei lesen
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    except (json.JSONDecodeError, FileNotFoundError):
        # Falls Datei leer/kaputt ist → leere Liste zurückgeben
        return []


def save_json(path, data):
    # Daten als JSON speichern
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)
        