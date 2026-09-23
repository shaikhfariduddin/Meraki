"""
Password hashing and JWT creation/decoding.

Hashing uses the `bcrypt` library directly rather than passlib — passlib
is unmaintained and has a known incompatibility with bcrypt>=4.1 (its
internal self-test raises ValueError on newer bcrypt versions). Calling
bcrypt directly avoids that dependency entirely.

Kept as pure functions with no DB or FastAPI dependency, so they're
trivial to unit test in isolation.
"""
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import settings

# bcrypt only uses the first 72 bytes of a password — anything beyond
# that is silently ignored by the algorithm itself, so we enforce the
# same limit at the schema level (see schemas/auth.py) rather than
# truncating quietly here.


def hash_password(plain_password: str) -> str:
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(*, subject: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError:
        return None
