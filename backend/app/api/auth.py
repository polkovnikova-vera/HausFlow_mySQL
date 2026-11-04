from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.passwords import verify_password
from app.schemas import LoginRequest, TokenResponse
from app.tokens import create_token

from database.models import User, AccessToken
from app.security import (
    get_current_user,
    require_staff,
    require_admin,
)

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.tokens import hash_token




router = APIRouter(prefix="/auth", tags=["Authentifizierung"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: DbSession):

    user = db.scalar(
        select(User).where(User.username == data.username)
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültige Zugangsdaten"
        )

    if not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültige Zugangsdaten"
        )

    token, token_hash, expires_at = create_token()

    db.add(
        AccessToken(
            token_hash=token_hash,
            user_id=user.id,
            expires_at=expires_at
        )
    )

    db.commit()

    return TokenResponse(access_token=token)


@router.get("/me")
def get_me(
    user: Annotated[User, Depends(get_current_user)]
):
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role
    }


bearer_scheme = HTTPBearer(auto_error=False)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    user: Annotated[User, Depends(get_current_user)],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme)
    ],
    db: DbSession,
):
    db.execute(
        delete(AccessToken).where(
            AccessToken.token_hash == hash_token(
                credentials.credentials
            ),
            AccessToken.user_id == user.id
        )
    )

    db.commit()



@router.get("/staff-check")
def staff_check(
    user: Annotated[User, Depends(require_staff)]
):
    return {
        "message": "Zugriff erlaubt",
        "username": user.username,
        "role": user.role
    }


@router.get("/admin-check")
def admin_check(
    user: Annotated[User, Depends(require_admin)]
):
    return {
        "message": "Administratorzugriff erlaubt",
        "username": user.username,
        "role": user.role
    }