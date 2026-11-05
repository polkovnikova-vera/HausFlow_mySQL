from sqlalchemy import text

from app.dependencies import get_db
from app.main import app


def test_database_isolation(client):
    # TestClient verwendet die Testdatenbank
    assert get_db in app.dependency_overrides

    # Verbindung aus der Test-Fixture abrufen
    override = app.dependency_overrides[get_db]
    session_generator = override()

    db = next(session_generator)

    try:
        database = db.execute(
            text("SELECT DATABASE()")
        ).scalar_one()

        assert database == "hv_test"

        print("\nTestdatenbank:", database)

    finally:
        session_generator.close()