from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas import RechnungCreate, RechnungResponse
from app.security import require_staff, check_building_access

from database.models import (
    Gebaeude,
    Meldung,
    MeldungRechnung,
    Rechnung,
    User,
    UserBuilding,
)

from sqlalchemy import select
from datetime import date

router = APIRouter(
    prefix="/invoices",
    tags=["Rechnungen"]
)

DbSession = Annotated[Session, Depends(get_db)]
StaffUser = Annotated[User, Depends(require_staff)]


# ============================================================
# POST /invoices - Neue Rechnung erstellen
# ============================================================

@router.post(
    "",
    response_model=RechnungResponse,
    status_code=status.HTTP_201_CREATED
)
def create_invoice(
    data: RechnungCreate,
    db: DbSession,
    user: StaffUser
):
    # 1. Prüfen, ob das Gebäude existiert
    building = db.get(Gebaeude, data.gebaeude_id)

    if building is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gebäude nicht gefunden"
        )

    # 2. Gebäudezugriff prüfen
    check_building_access(db, user, data.gebaeude_id)

    # 3. Doppelte Meldungs-IDs verbieten
    if len(data.meldung_ids) != len(set(data.meldung_ids)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Doppelte Meldungs-IDs"
        )

    # 4. Alle verknüpften Meldungen prüfen
    for meldung_id in data.meldung_ids:

        meldung = db.get(Meldung, meldung_id)

        if meldung is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Meldung {meldung_id} nicht gefunden"
            )

        if meldung.gebaeude_id != data.gebaeude_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Rechnung und Meldung gehören zu unterschiedlichen Gebäuden"
            )

    # 5. Rechnung erstellen
    rechnung = Rechnung(
        gebaeude_id=data.gebaeude_id,
        erstellt_von=user.id,
        rechnungsnummer=data.rechnungsnummer,
        lieferant=data.lieferant,
        rechnungsdatum=data.rechnungsdatum,
        betrag=data.betrag,
        status="open",
        bezahlt_am=None
    )

    # 6. Rechnung speichern und ID erhalten
    db.add(rechnung)
    db.flush()

    # 7. M:N-Verknüpfungen erstellen
    for meldung_id in data.meldung_ids:
        db.add(
            MeldungRechnung(
                meldung_id=meldung_id,
                rechnung_id=rechnung.id
            )
        )

    # 8. Alles gemeinsam speichern
    db.commit()
    db.refresh(rechnung)

    return rechnung


# ============================================================
# GET /invoices - Rechnungen anzeigen
# ============================================================

@router.get(
    "",
    response_model=list[RechnungResponse]
)
def get_invoices(
    db: DbSession,
    user: StaffUser,
    gebaeude_id: int | None = Query(
        default=None,
        gt=0
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=100
    )
):
    # 1. SQL-Abfrage vorbereiten
    query = select(Rechnung)

    # 2. Staff: nur Rechnungen zugeordneter Gebäude
    if user.role == "staff":
        query = query.join(
            UserBuilding,
            Rechnung.gebaeude_id == UserBuilding.building_id
        ).where(
            UserBuilding.user_id == user.id
        )

    # 3. Admin: alle Rechnungen

    # 4. Optional nach Gebäude filtern
    if gebaeude_id is not None:
        check_building_access(db, user, gebaeude_id)

        query = query.where(
            Rechnung.gebaeude_id == gebaeude_id
        )

    # 5. Neueste Rechnungen zuerst
    query = query.order_by(
        Rechnung.id.desc()
    ).limit(limit)

    return db.scalars(query).all()


# ============================================================
# GET /invoices/{id} - Einzelne Rechnung anzeigen
# ============================================================

@router.get(
    "/{invoice_id}",
    response_model=RechnungResponse
)
def get_invoice(
    invoice_id: Annotated[int, Path(ge=1)],
    db: DbSession,
    user: StaffUser
):
    # 1. Rechnung suchen
    rechnung = db.get(Rechnung, invoice_id)

    if rechnung is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rechnung nicht gefunden"
        )

    # 2. Gebäudezugriff prüfen
    check_building_access(db, user, rechnung.gebaeude_id)

    # 3. Rechnung zurückgeben
    return rechnung

# ============================================================
# PATCH /invoices/{id} - Rechnung als bezahlt markieren
# ============================================================

@router.patch(
    "/{invoice_id}",
    response_model=RechnungResponse
)
def pay_invoice(
    invoice_id: Annotated[int, Path(ge=1)],
    db: DbSession,
    user: StaffUser
):
    # 1. Rechnung suchen und sperren
    rechnung = db.scalar(
        select(Rechnung)
        .where(Rechnung.id == invoice_id)
        .with_for_update()
    )

    if rechnung is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rechnung nicht gefunden"
        )

    # 2. Gebäudezugriff prüfen
    check_building_access(db, user, rechnung.gebaeude_id)

    # 3. Nur offene Rechnungen bezahlen
    if rechnung.status != "open":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Rechnung ist bereits bezahlt"
        )

    # 4. Status und Zahlungsdatum setzen
    rechnung.status = "paid"
    rechnung.bezahlt_am = date.today()

    # 5. Speichern
    db.commit()
    db.refresh(rechnung)

    return rechnung