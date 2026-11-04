# =========================
# MELDUNGEN SERVICE (SQLITE)
# =========================

from services.db import get_connection


# Tabelle erstellen
def init_meldungen_table():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS meldungen (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        gebaeude_id INTEGER,
        wohnung_id INTEGER,
        kategorie TEXT,
        beschreibung TEXT,
        prioritaet TEXT,
        status TEXT,
        erstellt_am TEXT
    )
    """)

    conn.commit()
    conn.close()


# Meldung hinzufügen
def add_meldung(data):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO meldungen (
        gebaeude_id,
        wohnung_id,
        kategorie,
        beschreibung,
        prioritaet,
        status,
        erstellt_am
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data["gebaeude_id"],
        data["wohnung_id"],
        data["kategorie"],
        data["beschreibung"],
        data["prioritaet"],
        data["status"],
        data["erstellt_am"]
    ))

    conn.commit()

    new_id = cursor.lastrowid
    conn.close()

    data["id"] = new_id
    return data


# Meldungen laden
def get_meldungen_by_gebaeude(gebaeude_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM meldungen
    WHERE gebaeude_id = ?
    """, (gebaeude_id,))

    rows = cursor.fetchall()
    conn.close()

    result = []

    for row in rows:
        meldung = {
            "id": row[0],
            "gebaeude_id": row[1],
            "wohnung_id": row[2],
            "kategorie": row[3],
            "beschreibung": row[4],
            "prioritaet": row[5],
            "status": row[6],
            "erstellt_am": row[7]
        }

        result.append(meldung)

    return result