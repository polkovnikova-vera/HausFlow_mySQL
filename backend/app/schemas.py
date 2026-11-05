from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

NonEmptyText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1
    )
]

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1)

class RegisterRequest(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_]+$"
    )

    password: str = Field(
        min_length=8,
        max_length=128
    )


class RegisterResponse(BaseModel):
    id: int
    username: str
    role: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"



class MeldungCreate(BaseModel):
    gebaeude_id: int = Field(gt=0)

    titel: NonEmptyText = Field(max_length=100)

    beschreibung: NonEmptyText

    kategorie: str | None = Field(
        default=None,
        max_length=100
    )


class MeldungResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    gebaeude_id: int
    author_id: int
    assigned_user_id: int | None
    titel: str
    beschreibung: str
    kategorie: str | None
    prioritaet: str
    status: str

class MeldungUpdate(BaseModel):
    titel: str | None = Field(
        default=None,
        min_length=1,
        max_length=100
    )

    beschreibung: str | None = Field(
        default=None,
        min_length=1
    )

    kategorie: str | None = Field(
        default=None,
        max_length=100
    )

from datetime import date
from decimal import Decimal


class RechnungCreate(BaseModel):
    gebaeude_id: int = Field(gt=0)

    rechnungsnummer: str = Field(
        min_length=1,
        max_length=50
    )

    lieferant: str = Field(
        min_length=1,
        max_length=100
    )

    rechnungsdatum: date

    betrag: Decimal = Field(
        gt=0,
        max_digits=10,
        decimal_places=2
    )

    meldung_ids: list[Annotated[int, Field(gt=0)]] = Field(
    default_factory=list
    )


class RechnungResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    gebaeude_id: int
    erstellt_von: int
    rechnungsnummer: str
    lieferant: str
    rechnungsdatum: date
    betrag: Decimal
    status: str
    bezahlt_am: date | None