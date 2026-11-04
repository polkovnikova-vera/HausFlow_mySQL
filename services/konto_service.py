# =========================
# KONTO SERVICE (SQLITE)
# =========================

import json
from services.db import get_connection


# Tabelle erstellen
def init_konto_table():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS kontobewegungen (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        gebaeude_id INTEGER,
        datum TEXT,
        typ TEXT,
        kostenart TEXT,
        umlageschluessel TEXT,
        betrag REAL,
        beschreibung TEXT,
        beleg_pfad TEXT,
        betroffene_wohnungen TEXT
    )
    """)

    # Migration für bereits vorhandene Datenbanken
    cursor.execute("PRAGMA table_info(kontobewegungen)")
    columns = [row[1] for row in cursor.fetchall()]
    if "betroffene_wohnungen" not in columns:
        cursor.execute("ALTER TABLE kontobewegungen ADD COLUMN betroffene_wohnungen TEXT")

    conn.commit()
    conn.close()


# Kontobewegung hinzufügen
def add_kontobewegung(data):
    conn = get_connection()
    cursor = conn.cursor()

    betroffene = data.get("betroffene_wohnungen", [])
    betroffene_json = json.dumps(betroffene, ensure_ascii=False)

    cursor.execute("""
    INSERT INTO kontobewegungen (
        gebaeude_id,
        datum,
        typ,
        kostenart,
        umlageschluessel,
        betrag,
        beschreibung,
        beleg_pfad,
        betroffene_wohnungen
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["gebaeude_id"],
        data["datum"],
        data["typ"],
        data["kostenart"],
        data["umlageschluessel"],
        data["betrag"],
        data["beschreibung"],
        data["beleg_pfad"],
        betroffene_json
    ))

    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    data["id"] = new_id
    return data


# Kontobewegungen eines Gebäudes laden
def get_kontobewegungen_by_gebaeude(gebaeude_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM kontobewegungen
    WHERE gebaeude_id = ?
    """, (gebaeude_id,))

    rows = cursor.fetchall()
    column_names = [description[0] for description in cursor.description]
    conn.close()

    result = []

    for row in rows:
        db = dict(zip(column_names, row))
        raw_wohnungen = db.get("betroffene_wohnungen")

        try:
            betroffene = json.loads(raw_wohnungen) if raw_wohnungen else []
        except json.JSONDecodeError:
            betroffene = []

        eintrag = {
            "id": db.get("id"),
            "gebaeude_id": db.get("gebaeude_id"),
            "datum": db.get("datum"),
            "typ": db.get("typ"),
            "kostenart": db.get("kostenart"),
            "umlageschluessel": db.get("umlageschluessel"),
            "betrag": db.get("betrag"),
            "beschreibung": db.get("beschreibung"),
            "beleg_pfad": db.get("beleg_pfad"),
            "betroffene_wohnungen": betroffene
        }

        result.append(eintrag)

    return result
