# =========================
# GEBÄUDE SERVICE (SQLITE)
# =========================

from services.db import get_connection


# Tabelle erstellen
def init_gebaeude_table():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS gebaeude (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plz TEXT,
        stadt TEXT,
        strasse TEXT,
        hausnummer TEXT,
        flaeche REAL,
        mea REAL,
        energieausweis_bis TEXT,
        legionellenpruefung_bis TEXT
    )
    """)

    conn.commit()
    conn.close()


# Gebäude hinzufügen
def add_gebaeude(data):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO gebaeude (
        plz, stadt, strasse, hausnummer,
        flaeche, mea,
        energieausweis_bis,
        legionellenpruefung_bis
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["plz"],
        data["stadt"],
        data["strasse"],
        data["hausnummer"],
        data["flaeche"],
        data["mea"],
        data["energieausweis_bis"],
        data["legionellenpruefung_bis"]
    ))

    conn.commit()

    # 👉 ВАЖНО
    new_id = cursor.lastrowid

    conn.close()

    # 👉 возвращаем объект
    data["id"] = new_id
    return data
    conn.commit()
    conn.close()


# Alle Gebäude laden
def load_gebaeude():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM gebaeude")
    rows = cursor.fetchall()

    conn.close()

    result = []

    for row in rows:
        g = {
            "id": row[0],
            "adresse": {
                "plz": row[1],
                "stadt": row[2],
                "strasse": row[3],
                "hausnummer": row[4]
            },
            "flaeche": row[5],
            "miteigentumsanteile": row[6],
            "energieausweis_bis": row[7],
            "legionellenpruefung_bis": row[8]
        }
        result.append(g)

    return result

#LÖSCHEN
def delete_gebaeude(gebaeude_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM wohnungen WHERE gebaeude_id = ?", (gebaeude_id,))
    cursor.execute("DELETE FROM meldungen WHERE gebaeude_id = ?", (gebaeude_id,))
    cursor.execute("DELETE FROM kontobewegungen WHERE gebaeude_id = ?", (gebaeude_id,))

    cursor.execute("DELETE FROM gebaeude WHERE id = ?", (gebaeude_id,))

    conn.commit()
    conn.close()

#Ändern
def update_gebaeude(gebaeude_id, data):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE gebaeude
        SET plz = ?,
            stadt = ?,
            strasse = ?,
            hausnummer = ?,
            flaeche = ?,
            mea = ?,
            energieausweis_bis = ?,
            legionellenpruefung_bis = ?
        WHERE id = ?
    """, (
        data["plz"],
        data["stadt"],
        data["strasse"],
        data["hausnummer"],
        data["flaeche"],
        data["mea"],
        data["energieausweis_bis"],
        data["legionellenpruefung_bis"],
        gebaeude_id
    ))

    conn.commit()
    conn.close()