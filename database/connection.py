import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=os.getenv("HAUSFLOW_DB_USER"),
    password=os.getenv("HAUSFLOW_DB_PASSWORD"),
    host=os.getenv("HAUSFLOW_DB_HOST", "127.0.0.1"),
    port=int(os.getenv("HAUSFLOW_DB_PORT", "3308")),
    database=os.getenv("HAUSFLOW_DB_NAME"),
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def test_connection():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT DATABASE()"))
        print("Verbunden mit:", result.scalar())


if __name__ == "__main__":
    test_connection()