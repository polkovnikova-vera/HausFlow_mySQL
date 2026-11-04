# =========================
# WOHNUNGEN SERVICE (SQLITE)
# =========================

from services.db import get_connection


# Tabelle erstellen
def init_wohnungen_table():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS wohnungen (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        gebaeude_id INTEGER,
        nummer TEXT,
        flaeche REAL,
        mea REAL,
        eigentuemer_nachname TEXT,
        eigentuemer_vorname TEXT,
        eigentuemer_adresse TEXT,
        eigentuemer_telefon TEXT,
        eigentuemer_email TEXT,
        mieter_nachname TEXT,
        mieter_vorname TEXT,
        mieter_adresse TEXT,
        mieter_telefon TEXT,
        mieter_email TEXT,
        FOREIGN KEY (gebaeude_id) REFERENCES gebaeude(id)
    )
    """)

    conn.commit()
    conn.close()


# Wohnung hinzufügen
def add_wohnung(data):
    conn = get_connection()
    cursor = conn.cursor()

    eigentuemer = data["eigentuemer"]
    mieter = data["mieter"]

    cursor.execute("""
    INSERT INTO wohnungen (
        gebaeude_id,
        nummer,
        flaeche,
        mea,
        eigentuemer_nachname,
        eigentuemer_vorname,
        eigentuemer_adresse,
        eigentuemer_telefon,
        eigentuemer_email,
        mieter_nachname,
        mieter_vorname,
        mieter_adresse,
        mieter_telefon,
        mieter_email
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["gebaeude_id"],
        data["nummer"],
        data["flaeche"],
        data["miteigentumsanteile"],
        eigentuemer["nachname"],
        eigentuemer["vorname"],
        eigentuemer["adresse"],
        eigentuemer["telefonnummer"],
        eigentuemer["email"],
        mieter["nachname"],
        mieter["vorname"],
        mieter["adresse"],
        mieter["telefonnummer"],
        mieter["email"]
    ))

    conn.commit()

    new_id = cursor.lastrowid
    conn.close()

    data["id"] = new_id
    return data


# Wohnungen zu einem Gebäude laden
def get_wohnungen_by_gebaeude(gebaeude_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM wohnungen
    WHERE gebaeude_id = ?
    """, (gebaeude_id,))

    rows = cursor.fetchall()
    conn.close()

    result = []

    for row in rows:
        wohnung = {
            "id": row[0],
            "gebaeude_id": row[1],
            "nummer": row[2],
            "flaeche": row[3],
            "miteigentumsanteile": row[4],
            "eigentuemer": {
                "nachname": row[5],
                "vorname": row[6],
                "adresse": row[7],
                "telefonnummer": row[8],
                "email": row[9]
            },
            "mieter": {
                "nachname": row[10],
                "vorname": row[11],
                "adresse": row[12],
                "telefonnummer": row[13],
                "email": row[14]
            }
        }

        result.append(wohnung)

    return result