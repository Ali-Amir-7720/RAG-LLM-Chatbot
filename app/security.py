import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt

from app.config import get_settings


PBKDF2_ITERATIONS = 260_000
JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    encoded_salt = base64.urlsafe_b64encode(salt).decode("ascii")
    encoded_hash = base64.urlsafe_b64encode(password_hash).decode("ascii")
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${encoded_salt}${encoded_hash}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, iterations_str, encoded_salt, encoded_hash = password_hash.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        iterations = int(iterations_str)
        salt = base64.urlsafe_b64decode(encoded_salt.encode("ascii"))
        expected = base64.urlsafe_b64decode(encoded_hash.encode("ascii"))
    except Exception:
        return False

    computed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return secrets.compare_digest(computed, expected)


def create_access_token(*, user_id: UUID) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=settings.jwt_access_token_ttl_seconds)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> UUID:
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[JWT_ALGORITHM])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("invalid token type")
    sub = payload.get("sub")
    if not sub:
        raise jwt.InvalidTokenError("missing sub")
    return UUID(str(sub))


def generate_refresh_token() -> str:
    # Opaque token stored server-side in user_sessions.
    return secrets.token_urlsafe(48)
