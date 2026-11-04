from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas import (
    MeldungCreate,
    MeldungResponse,
    MeldungUpdate,
    RechnungResponse,
)
from app.security import get_current_user, check_building_access

from database.models import (
    Gebaeude,
    Meldung,
    MeldungRechnung,
    Rechnung,
    User,
    UserBuilding,
)
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status


router = APIRouter(prefix="/reports", tags=["Meldungen"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


# ============================================================
# POST /reports - Neue Meldung erstellen
# ============================================================

@router.post(
    "",
    response_model=MeldungResponse,
    status_code=status.HTTP_201_CREATED
)
def create_report(
    data: MeldungCreate,
    db: DbSession,
    user: CurrentUser
):
    # 1. Prüfen, ob das Gebäude existiert
    building = db.get(Gebaeude, data.gebaeude_id)

    if building is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gebäude nicht gefunden"
        )

    # 2. Zugriffsrechte prüfen
    check_building_access(db, user, data.gebaeude_id)

    # 3. Meldung erstellen
    meldung = Meldung(
        gebaeude_id=data.gebaeude_id,
        author_id=user.id,
        titel=data.titel,
        beschreibung=data.beschreibung,
        kategorie=data.kategorie,
    )

    # 4. In MySQL speichern
    db.add(meldung)
    db.commit()
    db.refresh(meldung)

    return meldung


# ============================================================
# GET /reports - Meldungen anzeigen
# ============================================================

@router.get(
    "",
    response_model=list[MeldungResponse]
)
def get_reports(
    db: DbSession,
    user: CurrentUser,
    report_status: str | None = Query(
        default=None,
        pattern="^(open|in_progress|resolved)$"
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=100
    )
):
    # 1. SQL-Abfrage vorbereiten
    query = select(Meldung)

    # 2. Tenant: nur eigene Meldungen
    if user.role == "tenant":
        query = query.where(
            Meldung.author_id == user.id
        )

    # 3. Staff: nur Meldungen zugeordneter Gebäude
    elif user.role == "staff":
        query = query.join(
            UserBuilding,
            Meldung.gebaeude_id == UserBuilding.building_id
        ).where(
            UserBuilding.user_id == user.id
        )

    # 4. Admin: alle Meldungen
    elif user.role == "admin":
        pass

    # 5. Unbekannte Rollen verbieten
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Keine Berechtigung"
        )

    # 6. Optional nach Status filtern
    if report_status is not None:
        query = query.where(
            Meldung.status == report_status
        )

    # 7. Sortierung und Limit
    query = query.order_by(
        Meldung.id.desc()
    ).limit(limit)

    # 8. Daten aus MySQL lesen
    return db.scalars(query).all()

from fastapi import Path


@router.get(
    "/{report_id}",
    response_model=MeldungResponse
)
def get_report(
    report_id: int = Path(ge=1),
    *,
    db: DbSession,
    user: CurrentUser
):
    meldung = db.get(Meldung, report_id)

    if meldung is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meldung nicht gefunden"
        )

    check_building_access(db, user, meldung.gebaeude_id)

    if user.role == "tenant" and meldung.author_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Keine Berechtigung für diese Meldung"
        )

    return meldung


# ============================================================
# PATCH /reports/{id} - Offene Meldung bearbeiten
# ============================================================

@router.patch(
    "/{report_id}",
    response_model=MeldungResponse
)
def update_report(
    report_id: Annotated[int, Path(ge=1)],
    data: MeldungUpdate,
    db: DbSession,
    user: CurrentUser
):
    # 1. Meldung suchen
    meldung = db.get(Meldung, report_id)

    if meldung is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meldung nicht gefunden"
        )

    # 2. Gebäudezugriff prüfen
    check_building_access(db, user, meldung.gebaeude_id)

    # 3. Berechtigung prüfen
    # Tenant darf nur eigene Meldungen bearbeiten
    if user.role == "tenant" and meldung.author_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Keine Berechtigung"
        )

    if user.role not in ("tenant", "staff", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Keine Berechtigung"
        )

    # 4. Nur offene Meldungen bearbeiten
    if meldung.status != "open":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nur offene Meldungen können bearbeitet werden"
        )

    # 5. Nur übermittelte Felder berücksichtigen
    updates = data.model_dump(exclude_unset=True)

    # 6. NULL für Pflichtfelder verbieten
    for field in ("titel", "beschreibung"):
        if field in updates and updates[field] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{field} darf nicht NULL sein"
            )

    # 7. Änderungen übernehmen
    for field, value in updates.items():
        setattr(meldung, field, value)

    # 8. Änderungen speichern
    db.commit()
    db.refresh(meldung)

    return meldung


# ============================================================
# PATCH /reports/{id}/claim - Meldung übernehmen
# ============================================================

@router.patch(
    "/{report_id}/claim",
    response_model=MeldungResponse
)
def claim_report(
    report_id: Annotated[int, Path(ge=1)],
    db: DbSession,
    user: CurrentUser
):
    # 1. Nur staff und admin dürfen Meldungen übernehmen
    if user.role not in ("staff", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Keine Berechtigung"
        )

    # 2. Meldung suchen und für die Bearbeitung sperren
    meldung = db.scalar(
        select(Meldung)
        .where(Meldung.id == report_id)
        .with_for_update()
    )

    if meldung is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meldung nicht gefunden"
        )

    # 3. Gebäudezugriff prüfen
    check_building_access(db, user, meldung.gebaeude_id)

    # 4. Nur offene Meldungen dürfen übernommen werden
    if meldung.status != "open":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Meldung ist nicht mehr offen"
        )

    # 5. Mitarbeiter zuweisen
    meldung.assigned_user_id = user.id

    # 6. Status ändern
    meldung.status = "in_progress"

    # 7. Änderungen speichern
    db.commit()
    db.refresh(meldung)

    return meldung

# ============================================================
# PATCH /reports/{id}/resolve - Meldung abschließen
# ============================================================

@router.patch(
    "/{report_id}/resolve",
    response_model=MeldungResponse
)
def resolve_report(
    report_id: Annotated[int, Path(ge=1)],
    db: DbSession,
    user: CurrentUser
):
    # 1. Nur staff und admin
    if user.role not in ("staff", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Keine Berechtigung"
        )

    # 2. Meldung suchen und sperren
    meldung = db.scalar(
        select(Meldung)
        .where(Meldung.id == report_id)
        .with_for_update()
    )

    if meldung is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meldung nicht gefunden"
        )

    # 3. Gebäudezugriff prüfen
    check_building_access(db, user, meldung.gebaeude_id)

    # 4. Nur zuständiger Mitarbeiter oder Admin
    if (
        user.role == "staff"
        and meldung.assigned_user_id != user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Meldung ist einem anderen Mitarbeiter zugewiesen"
        )

    # 5. Nur Meldungen in Bearbeitung abschließen
    if meldung.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Meldung ist nicht in Bearbeitung"
        )

    # 6. Status ändern
    meldung.status = "resolved"

    # 7. Speichern
    db.commit()
    db.refresh(meldung)

    return meldung