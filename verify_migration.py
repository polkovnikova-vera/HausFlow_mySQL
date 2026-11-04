import sqlite3
from decimal import Decimal

from sqlalchemy import text
from database.connection import engine

tables = [
    "gebaeude",
    "wohnungen",
    "meldungen",
    "kontobewegungen",
]

sqlite = sqlite3.connect("data/hausflow_backup.db")
sqlite.row_factory = sqlite3.Row

errors = []

with engine.connect() as mysql:
    for table in tables:
        rows = sqlite.execute(
            f"SELECT * FROM {table}"
        ).fetchall()

        if table != "gebaeude":
            rows = [
                row for row in rows
                if row["gebaeude_id"] != 1
            ]

        mysql_rows = mysql.execute(
            text(f"SELECT * FROM {table}")
        ).mappings().all()

        old = {row["id"]: dict(row) for row in rows}
        new = {row["id"]: dict(row) for row in mysql_rows}

        for record_id in old.keys() | new.keys():
            if record_id not in old or record_id not in new:
                errors.append(f"{table}: ID {record_id} fehlt")
                continue

            for column, old_value in old[record_id].items():
                new_value = new[record_id][column]

                if old_value is None or new_value is None:
                    equal = old_value is None and new_value is None
                elif column in ("betrag", "flaeche", "mea"):
                    equal = Decimal(str(old_value)) == Decimal(str(new_value))
                else:
                    equal = str(old_value) == str(new_value)
                if not equal:
                    errors.append(
                        f"{table}, ID {record_id}, Feld {column}: "
                        f"{old_value!r} != {new_value!r}"
                    )

        print(f"{table}: SQLite {len(old)}, MySQL {len(new)}")

sqlite.close()

print(f"\nUnterschiede: {len(errors)}")

for error in errors[:30]:
    print(error)

if not errors:
    print("Migration vollstaendig verifiziert!")