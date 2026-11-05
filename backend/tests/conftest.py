import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.main import app
from app.dependencies import get_db

from database.connection import DATABASE_URL
from database.models import Base
from app.passwords import hash_password
from database.models import User

# ============================================================
# Testdatenbank
# ============================================================

TEST_DATABASE_URL = DATABASE_URL.set(database="hv_test")

if TEST_DATABASE_URL.database != "hv_test":
    raise RuntimeError("Tests duerfen nur hv_test verwenden!")


test_engine = create_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True
)


# ============================================================
# Sicherheitspruefung
# ============================================================

def verify_test_database():
    with test_engine.connect() as connection:
        database = connection.execute(
            text("SELECT DATABASE()")
        ).scalar_one()

        if database != "hv_test":
            raise RuntimeError(
                "FEHLER: Falsche Testdatenbank!"
            )


# ============================================================
# Tabellen vorbereiten
# ============================================================

@pytest.fixture(scope="session", autouse=True)
def prepare_test_database():
    verify_test_database()

    Base.metadata.create_all(bind=test_engine)

    yield

    test_engine.dispose()


# ============================================================
# Datenbank-Session pro Test
# ============================================================

@pytest.fixture
def db_session():
    verify_test_database()

    connection = test_engine.connect()
    transaction = connection.begin()

    session = Session(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint"
    )

    try:
        yield session

    finally:
        session.close()
        transaction.rollback()
        connection.close()


# ============================================================
# FastAPI TestClient
# ============================================================

@pytest.fixture
def client(db_session):

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client

    finally:
        app.dependency_overrides.pop(get_db, None)

# ============================================================
# Gemeinsamer Testbenutzer
# ============================================================

@pytest.fixture
def test_user(db_session):
    user = User(
        username="pytest_anna",
        password_hash=hash_password("Test12345!"),
        role="tenant"
    )

    db_session.add(user)
    db_session.flush()

    return user