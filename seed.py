import os
import sys
from pathlib import Path

from sqlalchemy import select

from database.connection import SessionLocal
from database.models import User, Gebaeude, UserBuilding

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent / "backend")
)

from app.passwords import hash_password


USERS = [
    ("anna", "tenant"),
    ("peter", "tenant"),
    ("lisa", "tenant"),
    ("max", "tenant"),
    ("sophie", "tenant"),
    ("michael", "staff"),
    ("thomas", "staff"),
    ("julia", "staff"),
    ("admin", "admin"),
    ("supervisor", "admin"),
]

BUILDINGS = [
    ("91522", "Ansbach", "Hauptstraße", "12"),
    ("90402", "Nürnberg", "Bahnhofstraße", "8"),
    ("97070", "Würzburg", "Gartenstraße", "5"),
    ("96047", "Bamberg", "Lange Straße", "14"),
    ("90762", "Fürth", "Königstraße", "21"),
]


def seed_data():
    password = os.getenv("HAUSFLOW_SEED_PASSWORD")

    if not password:
        raise RuntimeError(
            "HAUSFLOW_SEED_PASSWORD ist nicht gesetzt."
        )

    with SessionLocal() as db:
        for username, role in USERS:
            existing = db.scalar(
                select(User).where(User.username == username)
            )

            if existing is None:
                db.add(
                    User(
                        username=username,
                        password_hash=hash_password(password),
                        role=role,
                    )
                )
                print(f"Benutzer erstellt: {username}")

        for plz, stadt, strasse, hausnummer in BUILDINGS:
            existing = db.scalar(
                select(Gebaeude).where(
                    Gebaeude.plz == plz,
                    Gebaeude.stadt == stadt,
                    Gebaeude.strasse == strasse,
                    Gebaeude.hausnummer == hausnummer,
                )
            )

            if existing is None:
                db.add(
                    Gebaeude(
                        plz=plz,
                        stadt=stadt,
                        strasse=strasse,
                        hausnummer=hausnummer,
                    )
                )
                print(f"Gebäude erstellt: {strasse} {hausnummer}")

        db.commit()

    print("Seed erfolgreich abgeschlossen.")

def seed_user_buildings():
    assignments = {
        "anna": [0, 1],
        "peter": [0],
        "lisa": [1, 2, 3],
        "max": [2],
        "sophie": [3, 4],
        "michael": [0, 1, 2],
        "thomas": [3, 4],
        "julia": [0, 1, 3, 4],
        "admin": [0, 1, 2, 3, 4],
        "supervisor": [0, 1, 2, 3, 4],
    }

    with SessionLocal() as db:
        buildings = []

        for plz, stadt, strasse, hausnummer in BUILDINGS:
            building = db.scalar(
                select(Gebaeude).where(
                    Gebaeude.plz == plz,
                    Gebaeude.stadt == stadt,
                    Gebaeude.strasse == strasse,
                    Gebaeude.hausnummer == hausnummer,
                )
            )

            if building is None:
                raise RuntimeError(
                    f"Gebäude nicht gefunden: {strasse} {hausnummer}"
                )

            buildings.append(building)

        for username, building_indexes in assignments.items():
            user = db.scalar(
                select(User).where(User.username == username)
            )

            if user is None:
                raise RuntimeError(
                    f"Benutzer nicht gefunden: {username}"
                )

            for index in building_indexes:
                building = buildings[index]

                existing = db.get(
                    UserBuilding,
                    (user.id, building.id)
                )

                if existing is None:
                    db.add(
                        UserBuilding(
                            user_id=user.id,
                            building_id=building.id,
                        )
                    )

                    print(
                        f"Zuordnung erstellt: {username} -> "
                        f"{building.strasse} {building.hausnummer}"
                    )

        db.commit()

if __name__ == "__main__":
    seed_data()
    seed_user_buildings()