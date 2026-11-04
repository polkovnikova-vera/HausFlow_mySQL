"""verwIQ: SQLAlchemy 2.0 draft matching existing SQLite columns.

Target: MySQL 8. This file defines schema only; it does not migrate data.
Review data quality and conversion rules before creating a production schema.
"""
from decimal import Decimal
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    __table_args__ = (
    CheckConstraint(
        "role IN ('tenant', 'staff', 'admin')",
        name="ck_users_role"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )



class UserBuilding(Base):
    __tablename__ = "user_buildings"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        primary_key=True
    )

    building_id: Mapped[int] = mapped_column(
        ForeignKey("gebaeude.id"),
        primary_key=True
    )



class Gebaeude(Base):
    __tablename__ = "gebaeude"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plz: Mapped[str | None] = mapped_column(String(20))
    stadt: Mapped[str | None] = mapped_column(String(255))
    strasse: Mapped[str | None] = mapped_column(String(255))
    hausnummer: Mapped[str | None] = mapped_column(String(30))
    flaeche: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    mea: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    energieausweis_bis: Mapped[str | None] = mapped_column(String(100))
    legionellenpruefung_bis: Mapped[str | None] = mapped_column(String(100))



class Meldung(Base):
    __tablename__ = "meldungen"

    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'in_progress', 'resolved')",
            name="ck_meldungen_status"
        ),
        CheckConstraint(
            "prioritaet IN ('low', 'medium', 'high')",
            name="ck_meldungen_prioritaet"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    gebaeude_id: Mapped[int] = mapped_column(
        ForeignKey("gebaeude.id"),
        nullable=False
    )

    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    assigned_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True
    )

    titel: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    beschreibung: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    kategorie: Mapped[str | None] = mapped_column(
        String(100)
    )

    prioritaet: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="medium"
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="open"
    )

    erstellt_am: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now
    )



class Rechnung(Base):
    __tablename__ = "rechnungen"

    __table_args__ = (
        CheckConstraint(
            "betrag > 0",
            name="ck_rechnungen_betrag"
        ),
        CheckConstraint(
            "status IN ('open', 'paid')",
            name="ck_rechnungen_status"
        ),
        CheckConstraint(
            "(status = 'open' AND bezahlt_am IS NULL) OR "
            "(status = 'paid' AND bezahlt_am IS NOT NULL)",
            name="ck_rechnungen_bezahlt"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    gebaeude_id: Mapped[int] = mapped_column(
        ForeignKey("gebaeude.id"),
        nullable=False
    )

    erstellt_von: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    rechnungsnummer: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    lieferant: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    rechnungsdatum: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )

    betrag: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="open"
    )

    bezahlt_am: Mapped[date | None] = mapped_column(
        Date,
        nullable=True
    )




class MeldungRechnung(Base):
    __tablename__ = "meldung_rechnungen"

    meldung_id: Mapped[int] = mapped_column(
        ForeignKey("meldungen.id"),
        primary_key=True
    )

    rechnung_id: Mapped[int] = mapped_column(
        ForeignKey("rechnungen.id"),
        primary_key=True
    )



class AccessToken(Base):
    __tablename__ = "access_tokens"

    token_hash: Mapped[str] = mapped_column(
        String(64),
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    expires_at: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )