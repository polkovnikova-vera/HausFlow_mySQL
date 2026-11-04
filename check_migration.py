import sqlite3

conn = sqlite3.connect("data/hausflow.db")
conn.row_factory = sqlite3.Row

checks = [
    ("wohnungen", "gebaeude_id", "gebaeude"),
    ("meldungen", "gebaeude_id", "gebaeude"),
    ("meldungen", "wohnung_id", "wohnungen"),
    ("kontobewegungen", "gebaeude_id", "gebaeude"),
]

total = 0

for table, column, reference in checks:
    query = f"""
        SELECT t.id, t.{column}
        FROM {table} AS t
        LEFT JOIN {reference} AS r
            ON t.{column} = r.id
        WHERE t.{column} IS NOT NULL
          AND r.id IS NULL
    """

    rows = conn.execute(query).fetchall()

    print(f"\n{table}.{column} -> {reference}.id")
    print(f"Fehlende Referenzen: {len(rows)}")

    for row in rows:
        print(f"  Datensatz ID {row['id']} -> {column} {row[column]}")

    total += len(rows)

print(f"\nInsgesamt fehlende Referenzen: {total}")

conn.close()