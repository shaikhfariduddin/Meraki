"""
FastAPI dependencies for authentication and role-based authorization.

`get_current_user` is the single place that trusts a JWT; every other
dependency builds on top of it. `require_role` is how a router says
"only these roles may call this endpoint" — the role comes from the
*decoded token*, which was itself derived from the trusted `users.role`
column at login time, never from anything the client sends per-request.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.repositories import user_repository
from app.utils.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise credentials_error

    user = user_repository.get_by_id(db, payload["sub"])
    if user is None or not user.is_active:
        raise credentials_error
    return user


def require_role(*allowed_roles: UserRole):
    """Usage: Depends(require_role(UserRole.ADMIN))"""

    def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return _checker
