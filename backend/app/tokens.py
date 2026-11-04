import hashlib
import secrets
import time


TOKEN_LIFETIME = 60 * 60 * 24  # 24 Stunden


def create_token() -> tuple[str, str, int]:
    token = secrets.token_urlsafe(32)

    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    expires_at = int(time.time()) + TOKEN_LIFETIME

    return token, token_hash, expires_at


def hash_token(token: str) -> str:
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()