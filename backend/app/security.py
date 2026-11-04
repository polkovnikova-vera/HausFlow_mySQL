import time
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.tokens import hash_token

from database.models import AccessToken, User, UserBuilding


bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme)
    ],
    db: DbSession,
) -> User:

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nicht angemeldet",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_hash = hash_token(credentials.credentials)

    token_record = db.get(AccessToken, token_hash)

    if token_record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültiger Token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if token_record.expires_at <= int(time.time()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token abgelaufen",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.get(User, token_record.user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Benutzer nicht gefunden",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_staff(
    user: Annotated[User, Depends(get_current_user)]
) -> User:

    if user.role not in ("staff", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Keine Berechtigung"
        )

    return user


def require_admin(
    user: Annotated[User, Depends(get_current_user)]
) -> User:

    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur Administratoren erlaubt"
        )

    return user


def check_building_access(
    db: Session,
    user: User,
    building_id: int
) -> None:

    if user.role == "admin":
        return

    access = db.scalar(
        select(UserBuilding).where(
            UserBuilding.user_id == user.id,
            UserBuilding.building_id == building_id
        )
    )

    if access is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kein Zugriff auf dieses Gebäude"
        )