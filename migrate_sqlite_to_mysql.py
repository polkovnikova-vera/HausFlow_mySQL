import sqlite3
from pathlib import Path

from sqlalchemy import MetaData, Table, select, func
from database.connection import engine


# Исходная база SQLite
SQLITE_PATH = Path("data/hausflow_backup.db")

# Порядок переноса таблиц
TABLES = [
    "gebaeude",
    "wohnungen",
    "meldungen",
    "kontobewegungen",
]

# Ожидаемое количество записей
EXPECTED_COUNTS = {
    "gebaeude": 28,
    "wohnungen": 137,
    "meldungen": 2,
    "kontobewegungen": 191,
}


def migrate():
    if not SQLITE_PATH.exists():
        raise FileNotFoundError(
            f"SQLite-Datenbank nicht gefunden: {SQLITE_PATH}"
        )

    sqlite_conn = sqlite3.connect(
        f"{SQLITE_PATH.resolve().as_uri()}?mode=ro",
        uri=True,
    )
    sqlite_conn.row_factory = sqlite3.Row

    metadata = MetaData()

    try:
        # Загружаем структуру таблиц MySQL
        mysql_tables = {
            name: Table(name, metadata, autoload_with=engine)
            for name in TABLES
        }

        # Сначала читаем и проверяем все данные
        data = {}

        for name in TABLES:
            rows = sqlite_conn.execute(
                f"SELECT * FROM {name}"
            ).fetchall()

            records = [dict(row) for row in rows]

            # Исключаем записи удалённого здания
            if name != "gebaeude":
                records = [
                    record
                    for record in records
                    if record.get("gebaeude_id") != 1
                ]

            if len(records) != EXPECTED_COUNTS[name]:
                raise ValueError(
                    f"{name}: Erwartet {EXPECTED_COUNTS[name]}, "
                    f"gefunden {len(records)}"
                )

            # Проверяем соответствие столбцов
            sqlite_columns = set(records[0].keys()) if records else set()
            mysql_columns = set(mysql_tables[name].columns.keys())

            if sqlite_columns != mysql_columns:
                raise ValueError(
                    f"{name}: Unterschiedliche Spalten!\n"
                    f"SQLite: {sqlite_columns}\n"
                    f"MySQL: {mysql_columns}"
                )

            data[name] = records

        # Все изменения MySQL выполняем в одной транзакции
        with engine.begin() as conn:

            # Защита от повторного переноса
            for name in TABLES:
                count = conn.execute(
                    select(func.count()).select_from(mysql_tables[name])
                ).scalar_one()

                if count != 0:
                    raise RuntimeError(
                        f"{name} ist nicht leer. Migration abgebrochen."
                    )

            # Перенос записей
            for name in TABLES:
                records = data[name]

                if records:
                    conn.execute(
                        mysql_tables[name].insert(),
                        records,
                    )

                print(f"{name}: {len(records)} Datensätze übertragen")

            # Проверка количества записей
            for name in TABLES:
                count = conn.execute(
                    select(func.count()).select_from(mysql_tables[name])
                ).scalar_one()

                if count != EXPECTED_COUNTS[name]:
                    raise RuntimeError(
                        f"{name}: Fehler bei der Überprüfung!"
                    )

        print("\nMigration erfolgreich abgeschlossen!")
        print("Insgesamt: 358 Datensätze")

    finally:
        sqlite_conn.close()


if __name__ == "__main__":
    migrate()